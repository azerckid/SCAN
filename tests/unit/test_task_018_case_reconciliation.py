"""TASK-018 bounded case reconciliation regression tests."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from scan_tool.domain import validate_analysis_request
from scan_tool.domain.operations import JobRole, LeafJobSpec
from scan_tool.slices.case_reconciliation import analyze_case_reconciliation_replay

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "docs/05_QA_Validation/fixtures/FX-CASE-EULER-EXIT-001"


def _request():
    return validate_analysis_request(
        json.loads((PACKAGE / "analysis-request.json").read_text(encoding="utf-8"))
    ).root


def _replay() -> dict[str, object]:
    return json.loads((PACKAGE / "raw-replay.json").read_text(encoding="utf-8"))


def _analyze(replay: dict[str, object] | None = None, request=None):
    body = json.dumps(replay or _replay(), sort_keys=True).encode()
    return analyze_case_reconciliation_replay(
        request or _request(),
        body,
        package_dir=PACKAGE,
    ).root


def test_case_reconciliation_preserves_fact_and_attribution_boundaries() -> None:
    result = _analyze()
    assert result.status == "partial"
    value = result.results[0].value
    assert value["reconciliation"]["selected_path_hop_count"] == 3
    assert value["reconciliation"]["branch_count"] == 4
    assert value["reconciliation"]["unrelated_inflow_excluded"] is True
    assert value["scope"]["full_incident_reconstruction"] is False
    assert value["attribution"]["address_ownership"] == "not_assessed"
    assert value["attribution"]["criminal_intent"] == "not_assessed"
    assert result.results[1].classification == "external_context"


def test_case_reconciliation_is_deterministic() -> None:
    first = _analyze().model_dump(mode="json", by_alias=True)
    second = _analyze().model_dump(mode="json", by_alias=True)
    assert first == second
    fact = first["results"][0]["value"]
    assert (
        hashlib.sha256(json.dumps(fact, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        == hashlib.sha256(
            json.dumps(
                second["results"][0]["value"],
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
    )


def test_case_reconciliation_rejects_seed_substitution() -> None:
    request = _request().model_copy(deep=True)
    request.inputs.seed_transaction_hash = "0x" + "1" * 64
    result = _analyze(request=request)
    assert result.status == "failed"
    assert result.errors[0].stage == "seed"


def test_case_reconciliation_rejects_source_fixture_subset() -> None:
    request = _request().model_copy(deep=True)
    request.inputs.source_fixture_refs = ["FX-FLOW-PATH-001"]
    result = _analyze(request=request)
    assert result.status == "failed"
    assert result.errors[0].stage == "source_fixture_binding"


def test_case_reconciliation_rejects_source_hash_mutation() -> None:
    replay = _replay()
    pins = deepcopy(replay["source_pins"])
    assert isinstance(pins, list)
    pins[0]["expected_sha256"] = "0" * 64
    replay["source_pins"] = pins
    result = _analyze(replay)
    assert result.status == "failed"
    assert result.errors[0].code == "decode_failed"
    assert result.errors[0].stage == "decode_replay"


def test_case_reconciliation_rejects_candidate_replay() -> None:
    replay = _replay()
    replay["status"] = "candidate"
    result = _analyze(replay)
    assert result.status == "failed"
    assert result.errors[0].code == "decode_failed"


def test_case_reconciliation_budget_returns_bounded_partial() -> None:
    request = _request().model_copy(deep=True)
    request.inputs.max_timeline_entries = 2
    result = _analyze(request=request)
    assert result.status == "partial"
    assert len(result.results[0].value["timeline"]) == 2
    assert result.results[0].value["reconciliation"]["selected_path_hop_count"] == 2


def test_case_reconciliation_rejects_unreviewed_category() -> None:
    request = _request().model_copy(deep=True)
    request.inputs.case_category = "phishing"
    replay = _replay()
    replay["case_category"] = "phishing"
    result = _analyze(replay, request=request)
    assert result.status == "failed"
    assert result.errors[0].code == "source_unavailable"


def test_case_reconciliation_rejects_unapproved_context_url() -> None:
    replay = _replay()
    replay["incident_context_url"] = "https://example.invalid/unreviewed"
    result = _analyze(replay)
    assert result.status == "failed"
    assert result.errors[0].code == "decode_failed"


def test_case_reconciliation_requires_exact_source_allowlist() -> None:
    request = _request().model_copy(deep=True)
    request.source_policy.allowed_source_ids = [
        "DS-EVM-RPC-PUBLIC",
        "DS-OSINT-WEB",
    ]
    result = _analyze(request=request)
    assert result.status == "failed"
    assert result.errors[0].code == "rule_restricted"


def test_case_reconciliation_requires_exact_source_order() -> None:
    request = _request().model_copy(deep=True)
    request.source_policy.source_order = [
        "DS-OSINT-WEB",
        "DS-EXPLORER-EVM",
        "DS-EVM-RPC-PUBLIC",
    ]
    result = _analyze(request=request)
    assert result.status == "failed"
    assert result.errors[0].stage == "source_binding"


def test_case_reconciliation_is_not_queueable_without_package_transport() -> None:
    with pytest.raises(ValidationError):
        LeafJobSpec(
            leaf_job_id="JOB-CASE-EVIDENCE",
            role=JobRole.EVIDENCE,
            purpose="Run path-bound case fixture",
            analysis_type="case_reconciliation",
            inputs_projection=_request().inputs.model_dump(mode="json"),
            depends_on=[],
            required_capabilities=["case_package_transport"],
            expected_output="Bounded case reconciliation",
        )
