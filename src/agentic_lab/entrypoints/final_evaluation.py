"""Validate and persist immutable evidence for the final framework evaluation."""

import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, cast

FINAL_EVALUATION_REPETITIONS: Final = 3
FINAL_EVALUATION_MODEL_ALIAS: Final = "security-analysis"

FINAL_EVALUATION_BENCHMARK_JSON_PATHS: Final[tuple[Path, ...]] = (
    Path("langgraph/latest.json"),
    Path("crewai/latest.json"),
    Path("crewai-flow/latest.json"),
    Path("llamaindex-workflow/latest.json"),
    Path("agno-workflow/latest.json"),
)
FINAL_EVALUATION_COMPARISON_JSON_PATH: Final = Path("comparison/five-way-latest.json")

_RUN_ID_PATTERN: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_GIT_COMMIT_PATTERN: Final = re.compile(r"[0-9a-f]{40}")


@dataclass(frozen=True, slots=True)
class FinalEvaluationManifest:
    """Describe the immutable provenance envelope for one final evaluation run."""

    schema_version: str
    generated_at_utc: str
    git_commit: str
    model_alias: str
    repetitions_per_scenario: int
    validated_json_artifacts: tuple[str, ...]


def default_final_evaluation_run_id() -> str:
    """Return a filesystem-safe UTC identifier for a new final evaluation run."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def validate_final_evaluation_run_id(run_id: str) -> str:
    """Reject ambiguous or traversal-capable final evaluation identifiers."""
    if ".." in run_id or _RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise ValueError(
            "run_id must be 1-64 characters using only letters, digits, '.', '_' or '-' "
            "and must not contain '..'"
        )
    return run_id


def validate_git_commit(git_commit: str) -> str:
    """Require a full immutable Git commit SHA for evaluation provenance."""
    if _GIT_COMMIT_PATTERN.fullmatch(git_commit) is None:
        raise ValueError("git_commit must be a full 40-character lowercase hexadecimal SHA")
    return git_commit


def _object_mapping(value: object, *, context: str) -> dict[str, object]:
    """Return a JSON object with string keys without leaking unknown types."""
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected JSON object for {context}")

    raw_mapping = cast(dict[object, object], value)
    mapping: dict[str, object] = {}
    for key, item in raw_mapping.items():
        if not isinstance(key, str):
            raise RuntimeError(f"Expected string JSON keys for {context}")
        mapping[key] = item
    return mapping


def _load_json_object(path: Path) -> dict[str, object]:
    """Load one benchmark JSON object through a strict runtime boundary."""
    if not path.is_file():
        raise RuntimeError(f"Required final evaluation artifact not found: {path}")

    payload: object = json.loads(path.read_text())
    return _object_mapping(payload, context=str(path))


def _require_string(mapping: dict[str, object], key: str, *, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"Expected non-empty string {key!r} in {context}")
    return value


def _require_int(mapping: dict[str, object], key: str, *, context: str) -> int:
    value = mapping.get(key)
    if type(value) is not int:
        raise RuntimeError(f"Expected integer {key!r} in {context}")
    return cast(int, value)


def validate_final_benchmark_workspace(
    benchmark_root: Path,
    *,
    expected_model_alias: str = FINAL_EVALUATION_MODEL_ALIAS,
) -> tuple[str, ...]:
    """Fail closed unless isolated benchmark artifacts describe the final contract."""
    if not expected_model_alias:
        raise ValueError("expected_model_alias must not be blank")

    validated_paths: list[str] = []
    for relative_path in FINAL_EVALUATION_BENCHMARK_JSON_PATHS:
        artifact_path = benchmark_root / relative_path
        payload = _load_json_object(artifact_path)
        context = relative_path.as_posix()

        model = _require_string(payload, "model", context=context)
        if model != expected_model_alias:
            raise RuntimeError(
                f"Final evaluation artifact {context} used model {model!r}; "
                f"expected governed alias {expected_model_alias!r}"
            )

        repetitions = _require_int(payload, "repetitions_per_scenario", context=context)
        if repetitions != FINAL_EVALUATION_REPETITIONS:
            raise RuntimeError(
                f"Final evaluation artifact {context} used {repetitions} repetitions; "
                f"expected {FINAL_EVALUATION_REPETITIONS}"
            )

        overall = _object_mapping(payload.get("overall_summary"), context=f"{context}.overall_summary")
        overall_model = _require_string(overall, "model", context=f"{context}.overall_summary")
        if overall_model != expected_model_alias:
            raise RuntimeError(f"Final evaluation overall model differs in {context}")

        validated_paths.append(relative_path.as_posix())

    comparison_path = benchmark_root / FINAL_EVALUATION_COMPARISON_JSON_PATH
    comparison = _load_json_object(comparison_path)
    methodology = _object_mapping(
        comparison.get("methodology"),
        context="comparison/five-way-latest.json.methodology",
    )
    comparison_model = _require_string(methodology, "model", context="comparison methodology")
    comparison_repetitions = _require_int(
        methodology,
        "repetitions_per_scenario",
        context="comparison methodology",
    )
    if comparison_model != expected_model_alias:
        raise RuntimeError("Final comparison does not use the governed model alias")
    if comparison_repetitions != FINAL_EVALUATION_REPETITIONS:
        raise RuntimeError("Final comparison does not use the required repetition count")

    validated_paths.append(FINAL_EVALUATION_COMPARISON_JSON_PATH.as_posix())
    return tuple(validated_paths)


def persist_final_evaluation_bundle(
    *,
    benchmark_root: Path,
    destination_root: Path,
    run_id: str,
    git_commit: str,
    model_alias: str = FINAL_EVALUATION_MODEL_ALIAS,
) -> Path:
    """Persist validated benchmark evidence without overwriting an earlier run."""
    safe_run_id = validate_final_evaluation_run_id(run_id)
    immutable_commit = validate_git_commit(git_commit)
    validated_paths = validate_final_benchmark_workspace(
        benchmark_root,
        expected_model_alias=model_alias,
    )

    destination = destination_root / safe_run_id
    if destination.exists():
        raise FileExistsError(f"Final evaluation destination already exists: {destination}")

    destination.mkdir(parents=True)
    shutil.copytree(benchmark_root, destination / "benchmarks")

    manifest = FinalEvaluationManifest(
        schema_version="1",
        generated_at_utc=datetime.now(UTC).isoformat(),
        git_commit=immutable_commit,
        model_alias=model_alias,
        repetitions_per_scenario=FINAL_EVALUATION_REPETITIONS,
        validated_json_artifacts=validated_paths,
    )
    (destination / "manifest.json").write_text(json.dumps(asdict(manifest), indent=2) + "\n")
    return destination
