"""Independent source-first verifier for ready TASK-015 candidate fixtures."""

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

FIXTURE_IDS = (
    "FX-OSINT-LABEL-CONFLICT-001",
    "FX-OSINT-SANCTIONS-HISTORY-001",
    "FX-OSINT-ENS-CONFLICT-001",
    "FX-ACTOR-RELATION-HUB-001",
)

REQUIREMENTS = {
    "FX-OSINT-LABEL-CONFLICT-001": (
        "REQ-INTEL-LABEL-ASSERTIONS",
        "REQ-INTEL-LABEL-CONFLICT",
    ),
    "FX-OSINT-SANCTIONS-HISTORY-001": (
        "REQ-INTEL-SAN-TIMELINE",
        "REQ-INTEL-SAN-CURRENT-SEPARATION",
    ),
    "FX-OSINT-ENS-CONFLICT-001": (
        "REQ-INTEL-ENS-FORWARD",
        "REQ-INTEL-ENS-REVERSE",
    ),
    "FX-ACTOR-RELATION-HUB-001": (
        "REQ-INTEL-ACTOR-HUB-RELATIONS",
        "REQ-INTEL-ACTOR-HUB-EXCLUSION",
    ),
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def verify_repository(fixtures_root: Path) -> tuple[dict[str, Any], ...]:
    return tuple(verify_fixture(fixtures_root, fixture_id) for fixture_id in FIXTURE_IDS)


def verify_fixture(fixtures_root: Path, fixture_id: str) -> dict[str, Any]:
    if fixture_id not in FIXTURE_IDS:
        raise ValueError("unsupported TASK-015 verifier fixture")
    package = fixtures_root / fixture_id
    expected = load_json(package / "expected.json")
    evidence = load_json(package / "evidence.json")
    if expected.get("fixture_id") != fixture_id or evidence.get("fixture_id") != fixture_id:
        raise ValueError("fixture IDs differ")
    _verify_requirements(fixture_id, expected, evidence)
    if fixture_id == "FX-OSINT-LABEL-CONFLICT-001":
        facts = _label(package)
    elif fixture_id == "FX-OSINT-SANCTIONS-HISTORY-001":
        facts = _sanctions(package, evidence)
    elif fixture_id == "FX-OSINT-ENS-CONFLICT-001":
        facts = _ens(package)
    else:
        facts = _hub(fixtures_root, evidence)
    if facts != _expected_projection(fixture_id, expected, evidence):
        raise ValueError(f"{fixture_id} independently calculated facts differ")
    canonical = json.dumps(facts, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return {
        "fixture_id": fixture_id,
        "status": "pass",
        "calculated_sha256": hashlib.sha256(canonical).hexdigest(),
        "requirement_count": len(REQUIREMENTS[fixture_id]),
    }


def _label(package: Path) -> dict[str, Any]:
    artifact_root = package / "artifacts/sha256"
    csv_path = artifact_root / (
        "15bbfb684a2c6048e2062753ae38a3543d3a09e9ff2de7e4ab08188015481475.csv"
    )
    _require_file_hash(csv_path)
    ens_snapshot_path = artifact_root / (
        "762291a131b34ed2af52f2baf681b4ed23b3452a6cdb43755c4bb525b9e56f5b.json"
    )
    config_path = artifact_root / (
        "84efb04363b2b6ff7d2dca3fc5a17358629203325ac5aa3c57d6ccde28d6fb32.js"
    )
    _require_file_hash(ens_snapshot_path)
    _require_file_hash(config_path)
    rows = list(csv.reader(csv_path.read_text(encoding="utf-8").splitlines()))
    if len(rows) != 1 or len(rows[0]) != 6:
        raise ValueError("label selected-row artifact shape differs")
    chain, address, entity, _, categories, source_value = rows[0]
    if chain != "Ethereum":
        raise ValueError("label chain differs")
    ens = _matching_complete_providers(load_json(package / "provider-replay.json"))
    decoded = ens[0]["decoded"]
    evidence = _evidence_map(load_json(package / "evidence.json"))
    config_evidence = evidence["EV-INTEL-LABEL-CONFIG"]
    fixture_input = load_json(package / "input.json")
    config_input = next(
        item for item in fixture_input["source_locators"] if item["source_id"] == "DS-OSINT-WEB"
    )
    if (
        config_evidence.get("license") != "MIT"
        or config_evidence.get("config_sha256") != config_path.stem
        or config_input.get("commit") != config_evidence.get("commit")
    ):
        raise ValueError("community config provenance differs")
    config_text = config_path.read_text(encoding="utf-8")
    team4 = re.search(
        r"team4:\s*\{\s*address:\s*'([^']+)',\s*beneficiary:\s*'([^']+)',"
        r"\s*cliff:\s*(\d+),\s*duration:\s*(\d+),",
        config_text,
    )
    if team4 is None:
        raise ValueError("community config team4 entry is missing")
    config_name, _, cliff, duration = team4.groups()
    if (cliff, duration) != ("12", "36"):
        raise ValueError("community config team4 vesting terms differ")
    if decoded["address"] != address.lower():
        raise ValueError("label dataset and ENS addresses differ")
    return {
        "subject_address": address.lower(),
        "dataset": {
            "entity": entity,
            "categories": categories.split(";"),
            "source_value": source_value,
        },
        "ens": {
            "name": "team4.vesting.contract.tornadocash.eth",
            "address": decoded["address"],
            "block_number": 25_640_270,
        },
        "community_config": {
            "name": config_name,
            "role": "team4_vesting_contract",
        },
        "conflict": {
            "auto_merge": False,
            "ownership_assessment": "not_assessed",
            "criminality_assessment": "not_assessed",
        },
    }


def _sanctions(package: Path, evidence: dict[str, Any]) -> dict[str, Any]:
    context = _evidence_map(evidence)
    designation = context["EV-INTEL-SAN-DESIGNATION"]
    removal = context["EV-INTEL-SAN-REMOVAL"]
    snapshot = load_json(package / "sls-snapshot.json")
    if designation.get("address_match_count") != 1 or removal.get("address_match_count") != 1:
        raise ValueError("official action address match count differs")
    if snapshot["query"]["case_insensitive_match_count"] != 0:
        raise ValueError("current SLS bounded address match differs")
    interpretation = snapshot["interpretation"]
    if any(
        interpretation[key] is not False
        for key in (
            "historical_designation_changed",
            "historical_removal_changed",
            "current_criminality_assessed",
        )
    ):
        raise ValueError("current SLS context rewrites historical facts")
    return {
        "timeline": [
            {"date": designation["action_date"], "action": "designation"},
            {"date": removal["action_date"], "action": "removal"},
        ],
        "current_status": "not_assessed",
        "current_sls_address_match_count": 0,
        "criminality_assessment": "not_assessed",
    }


def _ens(package: Path) -> dict[str, Any]:
    complete = _matching_complete_providers(load_json(package / "provider-replay.json"))
    decoded = complete[0]["decoded"]
    return {
        "block_number": 25_640_270,
        "forward": {
            "name": "nick.eth",
            "address": decoded["forward_address"],
            "resolver": decoded["forward_resolver"],
        },
        "reverse": {
            "address": decoded["forward_address"],
            "name": decoded["reverse_name"],
            "resolver": decoded["reverse_resolver"],
        },
        "forward_reverse_match": decoded["reverse_name"] == "nick.eth",
        "ownership_assessment": "not_assessed",
    }


def _hub(fixtures_root: Path, evidence: dict[str, Any]) -> dict[str, Any]:
    entries = _evidence_map(evidence)
    dex = load_json(fixtures_root / "FX-SVC-DEX-001/expected.json")
    auth = load_json(fixtures_root / "FX-EVM-AUTH-001/expected.json")
    _verify_linked_file_hashes(fixtures_root, entries["EV-INTEL-ACTOR-HUB-DEX"])
    _verify_linked_file_hashes(fixtures_root, entries["EV-INTEL-ACTOR-HUB-AUTH"])
    hub = dex["asset_in"]
    if hub["token_address"] != "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48":
        raise ValueError("DEX public hub differs")
    if auth["consumption"]["from"] != auth["approval"]["owner"]:
        raise ValueError("AUTH subject binding differs")
    return {
        "hub": {
            "address": hub["token_address"],
            "role": "public_erc20_token_contract",
            "symbol": hub["symbol"],
        },
        "relations": [
            {
                "subject_address": dex["user_net_output"]["to"],
                "source_fixture_id": "FX-SVC-DEX-001",
                "relation": "token_transfer_interaction",
            },
            {
                "subject_address": auth["approval"]["owner"],
                "source_fixture_id": "FX-EVM-AUTH-001",
                "relation": "approval_and_consumption_interaction",
            },
        ],
        "hub_excluded_from_actor_link": True,
        "ownership_assessment": "not_assessed",
        "coordination_assessment": "not_assessed",
    }


def _matching_complete_providers(replay: dict[str, Any]) -> list[dict[str, Any]]:
    complete = [item for item in replay["providers"] if item.get("status") == "complete"]
    if len(complete) < 2 or replay.get("decoded_match") is not True:
        raise ValueError("two matching complete provider replays are required")
    canonical = {json.dumps(item["decoded"], sort_keys=True) for item in complete}
    if len(canonical) != 1:
        raise ValueError("provider decoded values differ")
    return complete


def _verify_linked_file_hashes(fixtures_root: Path, entry: dict[str, Any]) -> None:
    source_id = entry["source_fixture_id"]
    for name, uri_key in (
        ("raw-replay.json", "raw_artifact_uri"),
        ("expected.json", "expected_artifact_uri"),
    ):
        path = fixtures_root / source_id / name
        expected_hash = entry[uri_key].removeprefix("artifact://sha256/")
        if _sha256(path.read_bytes()) != expected_hash:
            raise ValueError(f"{source_id} {name} hash differs")


def _require_file_hash(path: Path) -> None:
    if _sha256(path.read_bytes()) != path.name.split(".", 1)[0]:
        raise ValueError("content-addressed artifact hash differs")


def _evidence_map(evidence: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = {}
    for field in ("event_evidence", "call_evidence", "state_evidence", "context_evidence"):
        for item in evidence[field]:
            evidence_id = item["evidence_id"]
            if evidence_id in entries:
                raise ValueError("evidence IDs must be unique")
            entries[evidence_id] = item
    return entries


def _verify_requirements(
    fixture_id: str,
    expected: dict[str, Any],
    evidence: dict[str, Any],
) -> None:
    evidence_ids = set(_evidence_map(evidence))
    requirements = expected["scoring"]["requirements"]
    if {item["requirement_id"] for item in requirements} != set(REQUIREMENTS[fixture_id]):
        raise ValueError("requirement IDs differ")
    for requirement in requirements:
        refs = requirement.get("evidence_refs")
        if not refs or not set(refs).issubset(evidence_ids):
            raise ValueError("requirement evidence reference differs")


def _expected_projection(
    fixture_id: str,
    expected: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    if fixture_id == "FX-OSINT-LABEL-CONFLICT-001":
        dataset, config, ens = expected["assertions"]
        return {
            "subject_address": expected["subject_address"],
            "dataset": {
                "entity": dataset["entity"],
                "categories": dataset["categories"],
                "source_value": dataset["source_value"],
            },
            "ens": {
                "name": ens["name"],
                "address": ens["resolved_address"],
                "block_number": ens["block_number"],
            },
            "community_config": {
                "name": config["name"],
                "role": config["role"],
            },
            "conflict": {
                "auto_merge": expected["conflict"]["auto_merge"],
                "ownership_assessment": expected["conflict"]["ownership_assessment"],
                "criminality_assessment": expected["conflict"]["criminality_assessment"],
            },
        }
    if fixture_id == "FX-OSINT-SANCTIONS-HISTORY-001":
        return {
            "timeline": [
                {"date": item["date"], "action": item["action"]} for item in expected["timeline"]
            ],
            "current_status": expected["current_status"],
            "current_sls_address_match_count": 0,
            "criminality_assessment": "not_assessed",
        }
    if fixture_id == "FX-OSINT-ENS-CONFLICT-001":
        return {
            "block_number": expected["block_number"],
            "forward": expected["forward"],
            "reverse": expected["reverse"],
            "forward_reverse_match": expected["forward_reverse_match"],
            "ownership_assessment": expected["ownership_assessment"],
        }
    return {
        "hub": expected["hub"],
        "relations": expected["relations"],
        "hub_excluded_from_actor_link": expected["hub_excluded_from_actor_link"],
        "ownership_assessment": expected["ownership_assessment"],
        "coordination_assessment": expected["coordination_assessment"],
    }


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
