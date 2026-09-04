"""Provider-free tests for focused LlamaIndex gateway attempt diagnostics."""

from pathlib import Path
from runpy import run_path
from types import SimpleNamespace
from typing import Any

_SCRIPT_PATH = (
    Path(__file__).parents[2] / "scripts" / "diagnose_llamaindex_gateway_product_mismatch.py"
)
_SCRIPT = run_path(str(_SCRIPT_PATH))
build_attempt_diagnostics: Any = _SCRIPT["build_attempt_diagnostics"]
load_baseline_scenario: Any = _SCRIPT["load_baseline_scenario"]
load_product_mismatch_scenario: Any = _SCRIPT["load_product_mismatch_scenario"]
summarize_execution: Any = _SCRIPT["summarize_execution"]


def test_diagnostic_targets_canonical_product_mismatch_and_baseline_scenarios() -> None:
    target = load_product_mismatch_scenario()
    baseline = load_baseline_scenario()

    assert target.scenario_id == "product-mismatch"
    assert len(target.expected_assets) == 1
    assert target.expected_assets[0].asset_id == "api-prod-03"
    assert target.expected_assets[0].status == "not_applicable"
    assert baseline.scenario_id == "baseline-mixed"


def test_attempt_diagnostics_expose_only_status_level_trace() -> None:
    output = SimpleNamespace(
        attempt_trace=(
            SimpleNamespace(
                attempt=1,
                input_feedback=None,
                validation_passed=False,
                validation_reason="LLM applicability differs from deterministic oracle.",
                validation_feedback="sensitive evaluator feedback should not be copied",
                draft=SimpleNamespace(
                    recommendation="do not emit recommendation",
                    confidence=0.2,
                    assets=(
                        SimpleNamespace(
                            asset_id="api-prod-03",
                            status="affected",
                            rationale="do not emit rationale",
                        ),
                    ),
                ),
            ),
            SimpleNamespace(
                attempt=2,
                input_feedback="feedback was supplied",
                validation_passed=True,
                validation_reason="LLM applicability matches deterministic oracle.",
                validation_feedback="",
                draft=SimpleNamespace(
                    recommendation="do not emit recommendation",
                    confidence=0.9,
                    assets=(
                        SimpleNamespace(
                            asset_id="api-prod-03",
                            status="not_applicable",
                            rationale="do not emit rationale",
                        ),
                    ),
                ),
            ),
        )
    )

    diagnostics = build_attempt_diagnostics(output)

    assert len(diagnostics) == 2
    assert diagnostics[0].attempt == 1
    assert diagnostics[0].input_feedback_present is False
    assert diagnostics[0].validation_passed is False
    assert diagnostics[0].assets[0].asset_id == "api-prod-03"
    assert diagnostics[0].assets[0].status == "affected"
    assert diagnostics[1].attempt == 2
    assert diagnostics[1].input_feedback_present is True
    assert diagnostics[1].validation_passed is True
    assert diagnostics[1].assets[0].status == "not_applicable"

    serialized = repr(diagnostics)
    assert "sensitive evaluator feedback should not be copied" not in serialized
    assert "do not emit rationale" not in serialized
    assert "do not emit recommendation" not in serialized


def test_sample_summary_distinguishes_first_attempt_acceptance_from_final_source() -> None:
    execution = SimpleNamespace(
        output=SimpleNamespace(
            analysis_source="oracle_fallback",
            validation_passed=False,
            analysis_attempts=2,
            attempt_trace=(
                SimpleNamespace(validation_passed=False),
                SimpleNamespace(validation_passed=False),
            ),
        ),
        usage=SimpleNamespace(
            model_calls=2,
            input_tokens=1000,
            output_tokens=250,
            total_tokens=1250,
        ),
    )

    summary = summarize_execution("after_baseline", 2, execution)

    assert summary.mode == "after_baseline"
    assert summary.sample == 2
    assert summary.first_attempt_validation_passed is False
    assert summary.analysis_source == "oracle_fallback"
    assert summary.validation_passed is False
    assert summary.analysis_attempts == 2
    assert summary.model_calls == 2
    assert summary.total_tokens == 1250


def test_diagnostic_script_compares_isolated_and_baseline_preceded_modes_without_artifacts() -> None:
    source = _SCRIPT_PATH.read_text()

    assert 'mode="isolated"' in source
    assert 'mode="after_baseline"' in source
    assert "write_smoke_artifacts" not in source
    assert "artifacts/gateway-smoke" not in source
    assert "AGENTIC_LAB_MODEL" not in source
