"""Deterministic TASK-015 intel_context (Label/OSINT/Actor) analyzers.

Independently re-derives label/sanctions/identity/actor facts from reviewed
source replay bundles. This module does not import the fixture verifier
(``task_015_independent_verifier``); the two must reach the same facts from
separate code paths. Ownership, criminality, and coordination stay
``not_assessed``; AI/heuristic hypotheses are never promoted to confirmed fact.
"""

import re
from datetime import datetime

from pydantic import ValidationError
from pydantic.experimental.missing_sentinel import MISSING

from scan_tool import __version__
from scan_tool.domain import validate_analysis_result
from scan_tool.domain.analysis_request import (
    ActorRelationsInputs,
    CommonFunderInputs,
    IdentityCluesInputs,
    IntelContextAnalysisRequest,
    LabelClaimsInputs,
    SanctionsExposureInputs,
)
from scan_tool.domain.analysis_result import AnalysisResult
from scan_tool.domain.intel_context import (
    ActorRelationsSourceReplay,
    CommonFunderSourceReplay,
    IdentitySourceReplay,
    IntelSourceReplayDocument,
    LabelSourceReplay,
    SanctionsSourceReplay,
    parse_intel_source_replay,
)

CHECKPOINT_ID = "CP-INTEL-CONTEXT-SOURCE-REPLAY"
NOT_ASSESSED = "not_assessed"


class _DecodeFailure(Exception):
    def __init__(self, code: str, message: str, stage: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.stage = stage


def analyze_intel_context_replay(
    request: IntelContextAnalysisRequest,
    raw_replay: bytes,
    *,
    resumed: bool = False,
    checkpoint_id: str | None = CHECKPOINT_ID,
) -> AnalysisResult:
    """Run one approved intel_context query over a reviewed source replay bundle."""
    try:
        replay = parse_intel_source_replay(raw_replay)
    except (ValueError, ValidationError):
        return _failed(
            request,
            "decode_failed",
            "The reviewed source replay does not match the raw evidence contract.",
            "decode_replay",
            resumed,
            checkpoint_id,
        )
    binding_error = _binding_error(request, replay)
    if binding_error is not None:
        return _failed(request, *binding_error, resumed, checkpoint_id)
    try:
        inputs = request.inputs
        if isinstance(inputs, LabelClaimsInputs):
            return _label(request, replay, resumed, checkpoint_id)
        if isinstance(inputs, SanctionsExposureInputs):
            return _sanctions(request, replay, resumed, checkpoint_id)
        if isinstance(inputs, IdentityCluesInputs):
            return _identity(request, replay, resumed, checkpoint_id)
        if isinstance(inputs, CommonFunderInputs):
            return _common_funder(request, replay, resumed, checkpoint_id)
        return _actor_relations(request, replay, resumed, checkpoint_id)
    except _DecodeFailure as error:
        return _failed(request, error.code, error.message, error.stage, resumed, checkpoint_id)
    except (KeyError, TypeError, ValueError) as error:
        return _failed(
            request,
            "decode_failed",
            f"The reviewed source could not be decoded: {error}",
            "decode_intel_context",
            resumed,
            checkpoint_id,
        )


def _binding_error(
    request: IntelContextAnalysisRequest,
    replay: IntelSourceReplayDocument,
) -> tuple[str, str, str] | None:
    if not request.source_policy.offline_mode:
        return (
            "rule_restricted",
            "TASK-015 currently executes reviewed replay only.",
            "source_policy",
        )
    if request.fixture_id is not MISSING and request.fixture_id != replay.fixture_id:
        return (
            "reconciliation_failed",
            "Request and replay fixture IDs differ.",
            "source_reconciliation",
        )
    if request.query_kind.value != replay.query_kind:
        return (
            "reconciliation_failed",
            "Request query_kind and replay shape differ.",
            "source_reconciliation",
        )
    # Provenance is taken from the reviewed replay's own source records; every
    # one must sit inside the request allowlist, so a tampered allowlist cannot
    # manufacture a source of truth.
    allowed = set(request.source_policy.allowed_source_ids)
    if not {record.source_id for record in replay.sources} <= allowed:
        return (
            "rule_restricted",
            "Replay source record uses a source outside the allowed policy.",
            "source_policy",
        )
    return None


def _require_subject(request: IntelContextAnalysisRequest, subject: str) -> None:
    subjects = getattr(request.inputs, "subject_addresses", ())
    if subject not in subjects:
        raise _DecodeFailure(
            "reconciliation_failed",
            "Replay subject is not bound to the requested subject_addresses.",
            "source_reconciliation",
        )


# --- collect_label_claims -------------------------------------------------


def _label(
    request: IntelContextAnalysisRequest,
    replay: LabelSourceReplay,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    inputs = request.inputs
    assert isinstance(inputs, LabelClaimsInputs)
    _require_subject(request, replay.subject_address)
    if replay.ens.address != replay.subject_address:
        raise _DecodeFailure(
            "reconciliation_failed",
            "Label dataset subject and ENS-resolved address differ.",
            "source_reconciliation",
        )
    if replay.ens.block_number != inputs.observation_block:
        raise _DecodeFailure(
            "reconciliation_failed",
            "Replay ENS observation block differs from the requested observation_block.",
            "source_reconciliation",
        )
    _require_artifact_binding(inputs.source_artifact_refs, replay)
    if len(replay.sources) > inputs.max_sources:
        raise _DecodeFailure(
            "reconciliation_failed",
            "Reviewed replay uses more sources than the requested max_sources budget.",
            "source_reconciliation",
        )
    # A category label and a first-party role are different assertion classes and
    # are never silently auto-merged into one identity.
    auto_merge = not (replay.dataset.categories and replay.community_config.role)
    value = {
        "subject_address": replay.subject_address,
        "dataset": {
            "entity": replay.dataset.entity,
            "categories": list(replay.dataset.categories),
            "source_value": replay.dataset.source_value,
        },
        "ens": {
            "name": replay.ens.name,
            "address": replay.ens.address,
            "block_number": replay.ens.block_number,
        },
        "community_config": {
            "name": replay.community_config.name,
            "role": replay.community_config.role,
        },
        "conflict": {
            "auto_merge": auto_merge,
            "ownership_assessment": NOT_ASSESSED,
            "criminality_assessment": NOT_ASSESSED,
        },
    }
    evidence = [
        _evidence(
            replay,
            "EV-INTEL-LABEL-ASSERTIONS",
            "context",
            0,
        ),
        _evidence(
            replay,
            "EV-INTEL-LABEL-CONFLICT",
            "context",
            1,
        ),
    ]
    result = _result_item(
        "RES-INTEL-LABEL",
        "collect_label_claims",
        value,
        ["REQ-INTEL-LABEL-ASSERTIONS", "REQ-INTEL-LABEL-CONFLICT"],
        [item["evidence_id"] for item in evidence],
    )
    return _result(request, replay, "complete", [result], evidence, [], resumed, checkpoint_id)


# --- check_sanctions_exposure ---------------------------------------------


def _sanctions(
    request: IntelContextAnalysisRequest,
    replay: SanctionsSourceReplay,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    inputs = request.inputs
    assert isinstance(inputs, SanctionsExposureInputs)
    _require_subject(request, replay.subject_address)
    if replay.current_snapshot.subject_address != replay.subject_address:
        raise _DecodeFailure(
            "reconciliation_failed",
            "The current sanctions snapshot is not bound to the requested subject.",
            "source_reconciliation",
        )
    _require_source_ref(inputs.current_list_snapshot_ref, replay, "current_list_snapshot_ref")
    for action in replay.official_actions:
        if action.address_match_count != 1:
            raise _DecodeFailure(
                "reconciliation_failed",
                "An official action does not explicitly match the subject exactly once.",
                "source_reconciliation",
            )
    # One-to-one correspondence between requested action refs and replay actions:
    # replacing a removal with a duplicate designation must not still read complete.
    requested = sorted(_parse_action_ref(ref) for ref in inputs.official_action_refs)
    present = sorted((action.date, action.action) for action in replay.official_actions)
    if requested != present:
        raise _DecodeFailure(
            "reconciliation_failed",
            "Replay official actions are not a one-to-one match with the requested actions.",
            "source_reconciliation",
        )
    timeline = [
        {"date": action.date, "action": action.action}
        for action in sorted(replay.official_actions, key=lambda item: item.date)
    ]
    value = {
        "timeline": timeline,
        "current_status": NOT_ASSESSED,
        "current_sls_address_match_count": replay.current_snapshot.case_insensitive_match_count,
        "criminality_assessment": NOT_ASSESSED,
    }
    evidence = [
        _evidence(
            replay,
            "EV-INTEL-SAN-TIMELINE",
            "context",
            0,
        ),
        _evidence(
            replay,
            "EV-INTEL-SAN-CURRENT",
            "context",
            1,
        ),
    ]
    result = _result_item(
        "RES-INTEL-SANCTIONS",
        "check_sanctions_exposure",
        value,
        ["REQ-INTEL-SAN-TIMELINE", "REQ-INTEL-SAN-CURRENT-SEPARATION"],
        [item["evidence_id"] for item in evidence],
    )
    return _result(request, replay, "complete", [result], evidence, [], resumed, checkpoint_id)


# --- resolve_identity_clues -----------------------------------------------


def _identity(
    request: IntelContextAnalysisRequest,
    replay: IdentitySourceReplay,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    inputs = request.inputs
    assert isinstance(inputs, IdentityCluesInputs)
    if replay.forward.name not in inputs.names:
        raise _DecodeFailure(
            "reconciliation_failed",
            "Replay ENS name is not bound to the requested names.",
            "source_reconciliation",
        )
    if replay.forward.address not in inputs.subject_addresses:
        raise _DecodeFailure(
            "reconciliation_failed",
            "Replay ENS-resolved address is not bound to the requested subject_addresses.",
            "source_reconciliation",
        )
    if replay.block_number != inputs.observation_block:
        raise _DecodeFailure(
            "reconciliation_failed",
            "Replay observation block differs from the requested observation_block.",
            "source_reconciliation",
        )
    if replay.reverse.address != replay.forward.address:
        raise _DecodeFailure(
            "reconciliation_failed",
            "ENS forward and reverse resolved addresses differ.",
            "source_reconciliation",
        )
    _require_source_ref(inputs.provider_replay_ref, replay, "provider_replay_ref")
    value = {
        "block_number": replay.block_number,
        "forward": {
            "name": replay.forward.name,
            "address": replay.forward.address,
            "resolver": replay.forward.resolver,
        },
        "reverse": {
            "address": replay.reverse.address,
            "name": replay.reverse.name,
            "resolver": replay.reverse.resolver,
        },
        "forward_reverse_match": replay.reverse.name == replay.forward.name,
        "ownership_assessment": NOT_ASSESSED,
    }
    evidence = [
        _evidence(
            replay,
            "EV-INTEL-ENS-FORWARD",
            "state",
            0,
        ),
        _evidence(
            replay,
            "EV-INTEL-ENS-REVERSE",
            "state",
            1,
        ),
    ]
    result = _result_item(
        "RES-INTEL-ENS",
        "resolve_identity_clues",
        value,
        ["REQ-INTEL-ENS-FORWARD", "REQ-INTEL-ENS-REVERSE"],
        [item["evidence_id"] for item in evidence],
    )
    return _result(request, replay, "complete", [result], evidence, [], resumed, checkpoint_id)


# --- find_common_funder ---------------------------------------------------


def _common_funder(
    request: IntelContextAnalysisRequest,
    replay: CommonFunderSourceReplay,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    inputs = request.inputs
    assert isinstance(inputs, CommonFunderInputs)
    relation_subjects = {item.subject_address for item in replay.relations}
    # The requested subject set must match the replay exactly: dropping a subject
    # (or requesting one not present) must not read as a completed set.
    if relation_subjects != set(inputs.subject_addresses):
        raise _DecodeFailure(
            "reconciliation_failed",
            "Replay relation subjects do not match the requested subject_addresses exactly.",
            "source_reconciliation",
        )
    if replay.source_fixture_ref != inputs.source_fixture_ref:
        raise _DecodeFailure(
            "reconciliation_failed",
            "Replay source_fixture_ref differs from the requested source_fixture_ref.",
            "source_reconciliation",
        )
    if (replay.block_range.from_block, replay.block_range.to_block) != (
        inputs.block_range.from_block,
        inputs.block_range.to_block,
    ):
        raise _DecodeFailure(
            "reconciliation_failed",
            "Replay block_range differs from the requested block_range.",
            "source_reconciliation",
        )
    # Confirmed on-chain direct seed outputs (confirmed_fact).
    relations_value = {
        "seed_address": replay.seed_address,
        "relations": [
            {
                "subject_address": item.subject_address,
                "relation": item.relation,
                "amount_raw": item.amount_raw,
            }
            for item in replay.relations
        ],
    }
    # The common-funder assessment is a candidate hypothesis, not a confirmed
    # fact, and stays partial-only until a real completeness evidence structure
    # (bounded prehistory + service exclusion) exists. Claimed boolean flags are
    # never treated as completeness proof.
    assessment_value = {
        "common_funder_assessment": "candidate",
        "ownership_assessment": NOT_ASSESSED,
        "coordination_assessment": NOT_ASSESSED,
        "initial_inflow_complete": False,
        "service_exclusion_complete": False,
        "coverage_gaps": ["bounded_prehistory_unavailable", "service_exclusion_unavailable"],
    }
    evidence = [
        _evidence(replay, "EV-INTEL-COMMON-FUNDER-RELATIONS", "context", 0),
        _evidence(
            replay, "EV-INTEL-COMMON-FUNDER-ASSESSMENT", "context", min(1, len(replay.sources) - 1)
        ),
    ]
    results = [
        _result_item(
            "RES-INTEL-COMMON-FUNDER-RELATIONS",
            "find_common_funder_relations",
            relations_value,
            ["REQ-INTEL-FUNDER-RELATIONS"],
            ["EV-INTEL-COMMON-FUNDER-RELATIONS"],
            classification="confirmed_fact",
        ),
        _result_item(
            "RES-INTEL-COMMON-FUNDER-ASSESSMENT",
            "find_common_funder_assessment",
            assessment_value,
            ["REQ-INTEL-FUNDER-COMPLETENESS"],
            ["EV-INTEL-COMMON-FUNDER-ASSESSMENT"],
            classification="heuristic",
        ),
    ]
    errors = [
        _error(
            "evidence_incomplete",
            "Common-funder initial inflow / service exclusion completeness is unproven; "
            "confirmed direct seed outputs are preserved as a candidate hypothesis only.",
            "intel_coverage",
            [item["evidence_id"] for item in evidence],
            retryable=True,
        )
    ]
    return _result(request, replay, "partial", results, evidence, errors, resumed, checkpoint_id)


# --- score_actor_relations ------------------------------------------------


def _actor_relations(
    request: IntelContextAnalysisRequest,
    replay: ActorRelationsSourceReplay,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    inputs = request.inputs
    assert isinstance(inputs, ActorRelationsInputs)
    if replay.hub.address != inputs.hub_address:
        raise _DecodeFailure(
            "reconciliation_failed",
            "Replay hub differs from the requested hub_address.",
            "source_reconciliation",
        )
    if {item.subject_address for item in replay.relations} != set(inputs.subject_addresses):
        raise _DecodeFailure(
            "reconciliation_failed",
            "Replay relation subjects do not match the requested subject_addresses exactly.",
            "source_reconciliation",
        )
    if {item.source_fixture_id for item in replay.relations} != set(inputs.source_fixture_refs):
        raise _DecodeFailure(
            "reconciliation_failed",
            "Replay relation source fixtures do not match the requested source_fixture_refs exactly.",
            "source_reconciliation",
        )
    # One-to-one: each requested component weight is covered by exactly one relation
    # type, so duplicating a component (leaving another uncovered) must fail.
    if sorted(item.relation for item in replay.relations) != sorted(inputs.component_weights):
        raise _DecodeFailure(
            "reconciliation_failed",
            "Replay relation types are not a one-to-one match with the requested component_weights.",
            "source_reconciliation",
        )
    value = {
        "hub": {
            "address": replay.hub.address,
            "role": replay.hub.role,
            "symbol": replay.hub.symbol,
        },
        "relations": [
            {
                "subject_address": item.subject_address,
                "source_fixture_id": item.source_fixture_id,
                "relation": item.relation,
            }
            for item in replay.relations
        ],
        "hub_excluded_from_actor_link": True,
        "ownership_assessment": NOT_ASSESSED,
        "coordination_assessment": NOT_ASSESSED,
    }
    evidence = [
        _evidence(
            replay,
            "EV-INTEL-ACTOR-RELATIONS",
            "context",
            0,
        ),
        _evidence(
            replay,
            "EV-INTEL-ACTOR-EXCLUSION",
            "context",
            1,
        ),
    ]
    result = _result_item(
        "RES-INTEL-ACTOR-HUB",
        "score_actor_relations",
        value,
        ["REQ-INTEL-ACTOR-HUB-RELATIONS", "REQ-INTEL-ACTOR-HUB-EXCLUSION"],
        [item["evidence_id"] for item in evidence],
    )
    return _result(request, replay, "complete", [result], evidence, [], resumed, checkpoint_id)


# --- envelope helpers -----------------------------------------------------


def _parse_action_ref(ref: str) -> tuple[str, str]:
    match = re.search(r"(\d{4}-\d{2}-\d{2}).*?(designation|removal)", ref)
    if match is None:
        raise _DecodeFailure(
            "invalid_input",
            "official_action_ref must carry a date and designation/removal action.",
            "intel_input",
        )
    return match.group(1), match.group(2)


def _require_artifact_binding(
    requested_refs: list[str],
    replay: IntelSourceReplayDocument,
) -> None:
    # Exact set: a removed replay source (subset) must not read as complete, and a
    # requested artifact absent from the replay must fail.
    if {record.artifact_ref for record in replay.sources} != set(requested_refs):
        raise _DecodeFailure(
            "reconciliation_failed",
            "Replay source artifacts do not match the requested source_artifact_refs exactly.",
            "source_reconciliation",
        )


def _require_source_ref(requested_ref: str, replay: IntelSourceReplayDocument, what: str) -> None:
    if requested_ref not in {record.artifact_ref for record in replay.sources}:
        raise _DecodeFailure(
            "reconciliation_failed",
            f"Requested {what} does not match any reviewed replay source artifact.",
            "source_reconciliation",
        )


def _evidence(
    replay: IntelSourceReplayDocument,
    evidence_id: str,
    evidence_type: str,
    source_index: int,
) -> dict[str, object]:
    index = min(source_index, len(replay.sources) - 1)
    record = replay.sources[index]
    return {
        "evidence_id": evidence_id,
        "evidence_type": evidence_type,
        "source_id": record.source_id,
        "source_record_ref": record.source_record_id,
        "method": "reviewed_source_replay",
        "retrieved_at": replay.captured_at,
        "locator": {"chain_id": 1},
        "decoded": {"fixture_id": replay.fixture_id, "query_kind": replay.query_kind},
        "raw_artifact": {
            "artifact_uri": record.artifact_ref,
            "sha256": record.content_sha256,
            "media_type": "application/json",
        },
    }


def _source_records(
    replay: IntelSourceReplayDocument,
    referenced_ids: set[str],
) -> list[dict[str, object]]:
    return [
        {
            "source_record_id": record.source_record_id,
            "source_id": record.source_id,
            "provider_id": "reviewed-source-replay",
            "role": "scoring",
            "required": True,
            "capability": "intel_context_replay",
            "endpoint_host": "reviewed.replay.invalid",
            "retrieved_at": replay.captured_at,
        }
        for record in replay.sources
        if record.source_record_id in referenced_ids
    ]


def _result_item(
    result_id: str,
    result_type: str,
    value: dict[str, object],
    fixture_requirement_ids: list[str],
    evidence_refs: list[str],
    *,
    classification: str = "confirmed_fact",
) -> dict[str, object]:
    return {
        "result_id": result_id,
        "result_type": result_type,
        "classification": classification,
        "value": value,
        "tool_requirement_ids": ["REQ-P0-EVM-001"],
        "fixture_requirement_ids": fixture_requirement_ids,
        "evidence_refs": evidence_refs,
    }


def _error(
    code: str,
    message: str,
    stage: str,
    evidence_ids: list[str],
    *,
    retryable: bool = False,
) -> dict[str, object]:
    value: dict[str, object] = {
        "error_id": f"ERR-INTEL-{code.upper().replace('_', '-')}",
        "code": code,
        "message": message,
        "stage": stage,
        "retryable": retryable,
        "attempt_count": 0,
    }
    if evidence_ids:
        value["related_evidence_ids"] = evidence_ids
    return value


def _result(
    request: IntelContextAnalysisRequest,
    replay: IntelSourceReplayDocument,
    status: str,
    results: list[dict[str, object]],
    evidence: list[dict[str, object]],
    errors: list[dict[str, object]],
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    referenced = {str(item["source_record_ref"]) for item in evidence}
    finished_at = max(request.requested_at, replay.captured_at)
    return validate_analysis_result(
        {
            "$schema": "../../schemas/analysis-result.schema.json",
            "schema_version": "0.2",
            "analysis_id": request.analysis_id,
            "analysis_type": request.analysis_type,
            "chain_id": request.chain_id,
            "status": status,
            "results": results,
            "evidence": evidence,
            "sources": _source_records(replay, referenced),
            "warnings": [],
            "errors": errors,
            "run": _run(
                request.requested_at, finished_at, resumed=resumed, checkpoint_id=checkpoint_id
            ),
            "exports": _pending_exports(request.analysis_id),
        }
    )


def _failed(
    request: IntelContextAnalysisRequest,
    code: str,
    message: str,
    stage: str,
    resumed: bool,
    checkpoint_id: str | None,
) -> AnalysisResult:
    return validate_analysis_result(
        {
            "$schema": "../../schemas/analysis-result.schema.json",
            "schema_version": "0.2",
            "analysis_id": request.analysis_id,
            "analysis_type": request.analysis_type,
            "chain_id": request.chain_id,
            "status": "failed",
            "results": [],
            "evidence": [],
            "sources": [],
            "warnings": [],
            "errors": [_error(code, message, stage, [])],
            "run": _run(
                request.requested_at,
                request.requested_at,
                resumed=resumed,
                checkpoint_id=checkpoint_id,
            ),
            "exports": _pending_exports(request.analysis_id),
        }
    )


def _run(
    started_at: datetime,
    finished_at: datetime,
    *,
    resumed: bool,
    checkpoint_id: str | None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "tool_version": __version__,
        "execution_mode": "offline_replay",
        "started_at": started_at,
        "finished_at": max(started_at, finished_at),
        "cache_hits": 1,
        "cache_misses": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "resumed": resumed,
    }
    if checkpoint_id is not None:
        value["checkpoint_id"] = checkpoint_id
    return value


def _pending_exports(analysis_id: str) -> dict[str, object]:
    return {
        "json": {"artifact_uri": f"artifact://pending/{analysis_id}/result.json"},
        "markdown": {"artifact_uri": f"artifact://pending/{analysis_id}/evidence.md"},
    }
