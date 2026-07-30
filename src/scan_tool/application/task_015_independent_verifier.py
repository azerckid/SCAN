"""Independent source-first verifier for ready TASK-015 candidate fixtures."""

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
    official_path = artifact_root / (
        "2ddb426a2d404d4984345fb6026ca02932cd4313dd0db79b36f41617f34a9a34.json"
    )
    ens_snapshot_path = artifact_root / (
        "c5da8824427364b20cc4582cb15a3704f20e4b15bb16b81dd52f7e5d6203bf4d.json"
    )
    config_path = artifact_root / (
        "84efb04363b2b6ff7d2dca3fc5a17358629203325ac5aa3c57d6ccde28d6fb32.js"
    )
    _require_file_hash(official_path)
    _require_file_hash(ens_snapshot_path)
    _require_file_hash(config_path)
    official = load_json(official_path)
    sanctions_package = package.parent / official["source_fixture_id"]
    sanctions_input = load_json(sanctions_package / "input.json")
    sanctions_evidence = _evidence_map(load_json(sanctions_package / "evidence.json"))
    designation = sanctions_evidence["EV-INTEL-SAN-DESIGNATION"]
    if (
        official.get("source_fixture_status") != "confirmed"
        or sanctions_input.get("status") != "confirmed"
        or sanctions_input.get("subject_address") != official.get("subject_address")
        or designation.get("action_date") != official.get("action_date")
        or designation.get("html_sha256") != official.get("action_html_sha256")
        or designation.get("address_match_count") != official.get("address_match_count")
        or official.get("current_status") != "not_assessed"
        or official.get("criminality_assessment") != "not_assessed"
    ):
        raise ValueError("official historical action projection differs")
    ens = _matching_complete_providers(load_json(package / "provider-replay.json"))
    decoded = ens[0]["decoded"]
    ens_snapshot = load_json(ens_snapshot_path)
    evidence = _evidence_map(load_json(package / "evidence.json"))
    official_evidence = evidence["EV-INTEL-LABEL-OFFICIAL-HISTORY"]
    config_evidence = evidence["EV-INTEL-LABEL-CONFIG"]
    ens_evidence = evidence["EV-INTEL-LABEL-ENS"]
    fixture_input = load_json(package / "input.json")
    official_input = next(
        item
        for item in fixture_input["source_locators"]
        if item["source_id"] == "DS-SANCTIONS-PUBLIC"
    )
    config_input = next(
        item for item in fixture_input["source_locators"] if item["source_id"] == "DS-OSINT-WEB"
    )
    ens_input = next(
        item for item in fixture_input["source_locators"] if item["source_id"] == "DS-ENS"
    )
    if (
        official_evidence.get("source_fixture_id") != official["source_fixture_id"]
        or official_evidence.get("subject_address") != official["subject_address"]
        or official_evidence.get("action_date") != official["action_date"]
        or official_evidence.get("action_html_sha256") != official["action_html_sha256"]
        or official_input.get("source_fixture_id") != official["source_fixture_id"]
        or official_input.get("action_date") != official["action_date"]
        or official_input.get("bounded_fact_sha256") != official_path.stem
    ):
        raise ValueError("official historical action evidence differs")
    if (
        config_evidence.get("license") != "MIT"
        or config_evidence.get("config_sha256") != config_path.stem
        or config_input.get("commit") != config_evidence.get("commit")
    ):
        raise ValueError("community config provenance differs")
    config_text = config_path.read_text(encoding="utf-8")
    mining_rate = re.search(
        r"\{\s*instance:\s*'eth-01\.tornadocash\.eth',\s*value:\s*'([^']+)'\s*\}",
        config_text,
    )
    instance = re.search(
        r"netId1:\s*\{\s*eth:\s*\{\s*instanceAddress:\s*\{\s*"
        r"0\.1:\s*'([^']+)'",
        config_text,
    )
    if mining_rate is None or instance is None:
        raise ValueError("community config ETH 0.1 instance projection is missing")
    address = instance.group(1).lower()
    if mining_rate.group(1) != "10":
        raise ValueError("community config mining rate differs")
    if (
        official.get("subject_address") != address
        or config_evidence.get("instance_name") != "eth-01.tornadocash.eth"
        or config_evidence.get("denomination") != "0.1"
        or config_evidence.get("instance_address") != address
        or config_evidence.get("mining_rate_value") != mining_rate.group(1)
        or ens_input.get("name") != ens_snapshot.get("name")
        or ens_input.get("block_number") != ens_snapshot.get("block_number")
        or ens_evidence.get("name") != ens_snapshot.get("name")
        or ens_evidence.get("resolved_address") != address
        or ens_evidence.get("artifact_uri") != f"artifact://sha256/{ens_snapshot_path.stem}"
        or ens_snapshot.get("name") != "eth-01.tornadocash.eth"
        or ens_snapshot.get("address") != address
        or ens_snapshot.get("block_number") != 25_640_270
        or decoded["address"] != address
    ):
        raise ValueError("official, config, and ENS subject binding differs")
    return {
        "subject_address": address,
        "dataset": {
            "entity": official["entity"],
            "categories": [official["category"]],
            "source_value": official["action_date"],
        },
        "ens": {
            "name": ens_snapshot["name"],
            "address": decoded["address"],
            "block_number": 25_640_270,
        },
        "community_config": {
            "name": "eth-01.tornadocash.eth",
            "role": "eth_0_1_instance",
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
    fixture_input = load_json(package / "input.json")
    if snapshot["query"]["address"] != fixture_input["subject_address"]:
        raise ValueError("current SLS snapshot subject differs")
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
