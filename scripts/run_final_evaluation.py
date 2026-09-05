#!/usr/bin/env python3
"""Run the current five-way evaluation without mutating historical artifacts."""

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from tempfile import TemporaryDirectory

from agentic_lab.adapters.gateway import gateway_api_key, gateway_base_url, gateway_model_alias
from agentic_lab.entrypoints.final_evaluation import (
    FINAL_EVALUATION_REPETITIONS,
    default_final_evaluation_run_id,
    persist_final_evaluation_bundle,
)

_BENCHMARK_SCRIPTS = (
    "benchmark_langgraph_scenarios.py",
    "benchmark_crewai_scenarios.py",
    "benchmark_crewai_flow_scenarios.py",
    "benchmark_llamaindex_workflow_scenarios.py",
    "benchmark_agno_workflow_scenarios.py",
)
_COMPARISON_SCRIPT = "compare_five_way_benchmarks.py"


def parse_args() -> argparse.Namespace:
    """Parse final-evaluation execution options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional immutable artifact directory name; defaults to a UTC timestamp.",
    )
    return parser.parse_args()


def _run_trusted_command(
    command: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run one closed-world command assembled only from project-owned inputs."""
    result = subprocess.run(  # noqa: S603 - command executables/arguments are project-owned
        tuple(command),
        cwd=cwd,
        env=None if env is None else dict(env),
        check=False,
        capture_output=capture_output,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {command[0]}")
    return result


def _git_executable() -> str:
    """Resolve Git to an absolute executable path before invoking it."""
    executable = shutil.which("git")
    if executable is None:
        raise RuntimeError("git executable not found")
    return executable


def _git_output(repo_root: Path, *arguments: str) -> str:
    """Return stripped output from one trusted Git read command."""
    result = _run_trusted_command(
        (_git_executable(), *arguments),
        cwd=repo_root,
        capture_output=True,
    )
    return result.stdout.strip()


def _require_clean_worktree(repo_root: Path) -> str:
    """Return the evaluated commit only when repository provenance is unambiguous."""
    status = _git_output(repo_root, "status", "--porcelain")
    if status:
        raise RuntimeError("Final evaluation requires a clean committed Git worktree")

    commit = _git_output(repo_root, "rev-parse", "HEAD")
    if len(commit) != 40:
        raise RuntimeError("Unable to resolve a full Git commit for final evaluation")
    return commit


def _benchmark_environment(repo_root: Path) -> dict[str, str]:
    """Build child-process environment without logging credentials or legacy model selection."""
    gateway_base_url()
    gateway_api_key()

    environment = dict(os.environ)
    environment.pop("AGENTIC_LAB_MODEL", None)
    environment["AGNO_TELEMETRY"] = "false"

    source_root = str(repo_root / "src")
    current_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        source_root
        if not current_pythonpath
        else os.pathsep.join((source_root, current_pythonpath))
    )
    return environment


def run_final_evaluation(repo_root: Path, *, run_id: str) -> Path:
    """Execute all variants in isolation and persist one immutable evidence bundle."""
    git_commit = _require_clean_worktree(repo_root)
    environment = _benchmark_environment(repo_root)
    model_alias = gateway_model_alias()
    script_root = repo_root / "scripts"

    with TemporaryDirectory(prefix="agentic-security-final-eval-") as temporary_directory:
        workspace = Path(temporary_directory)

        for script_name in _BENCHMARK_SCRIPTS:
            print(f"running: {script_name}", flush=True)
            _run_trusted_command(
                (
                    sys.executable,
                    str(script_root / script_name),
                    "--runs",
                    str(FINAL_EVALUATION_REPETITIONS),
                ),
                cwd=workspace,
                env=environment,
            )

        print(f"running: {_COMPARISON_SCRIPT}", flush=True)
        _run_trusted_command(
            (sys.executable, str(script_root / _COMPARISON_SCRIPT)),
            cwd=workspace,
            env=environment,
        )

        destination = persist_final_evaluation_bundle(
            benchmark_root=workspace / "artifacts" / "benchmarks",
            destination_root=repo_root / "artifacts" / "final-evaluation",
            run_id=run_id,
            git_commit=git_commit,
            model_alias=model_alias,
        )

    return destination


def main() -> int:
    """Run final evaluation from the repository root and report only safe metadata."""
    args = parse_args()
    run_id = args.run_id if isinstance(args.run_id, str) else default_final_evaluation_run_id()
    repo_root = Path(__file__).resolve().parents[1]

    destination = run_final_evaluation(repo_root, run_id=run_id)
    print(f"final_evaluation_artifact: {destination.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
