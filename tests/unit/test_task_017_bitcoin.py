import hashlib
import json
import runpy
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from scan_tool.application.task_017_negative_oracles import (
    BitcoinOracleCase,
    evaluate_bitcoin_oracle,
)
from scan_tool.domain import ContractViolation, validate_analysis_request
from scan_tool.domain.analysis_request import BitcoinUtxoAnalysisRequest
from scan_tool.domain.bitcoin_utxo import BitcoinUtxoReplay
from scan_tool.slices.bitcoin_utxo import analyze_bitcoin_utxo_replay

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "docs/05_QA_Validation/fixtures/FX-BTC-UTXO-001"
independently_verify_bitcoin = runpy.run_path(str(ROOT / "scripts/verify_task_017_bitcoin.py"))[
    "verify"
]


def _document() -> dict[str, object]:
    return json.loads((PACKAGE / "analysis-request.json").read_text())


def _request() -> BitcoinUtxoAnalysisRequest:
    request = validate_analysis_request(_document()).root
    assert isinstance(request, BitcoinUtxoAnalysisRequest)
    return request


def test_bitcoin_exact_satoshi_summary() -> None:
    result = analyze_bitcoin_utxo_replay(
        _request(), (PACKAGE / "raw-replay.json").read_bytes(), package_dir=PACKAGE
    )
    assert result.root.status == "complete"
    value = result.root.results[0].value
    assert value["input_sum_sat"] == 604308
    assert value["output_sum_sat"] == 435183
    assert value["fee_sat"] == 169125


def test_bitcoin_spend_path_has_provider_backed_evidence() -> None:
    result = analyze_bitcoin_utxo_replay(
        _request(), (PACKAGE / "raw-replay.json").read_bytes(), package_dir=PACKAGE
    )
    evidence = {item.evidence_id: item for item in result.root.evidence}
    refs = set(result.root.results[0].evidence_refs)

    assert {"EV-BTC-HOP-0-0", "EV-BTC-HOP-0-1", "EV-BTC-HOP-0-2"} <= refs
    assert evidence["EV-BTC-HOP-0-0"].decoded["spending_transaction_id"] == (
        "a75779b6562c6bd549f25dc3001b5edd3d24e53235e29fe3047bccaeb25d7a6f"
    )
    assert evidence["EV-BTC-HOP-0-0"].raw_artifact.sha256 == (
        "59d353ad36038abee2c976a5c6083b48bfd428aeb1fdd914e245791af97a757e"
    )


def test_bitcoin_replay_rejects_fee_mismatch() -> None:
    replay = json.loads((PACKAGE / "raw-replay.json").read_text())
    replay["transaction"]["fee_sat"] = 1
    with pytest.raises(ValidationError):
        BitcoinUtxoReplay.model_validate(replay)


def test_bitcoin_replay_rejects_duplicate_provider_identity() -> None:
    replay = json.loads((PACKAGE / "raw-replay.json").read_text())
    replay["transaction"]["providers"][1]["provider_id"] = replay["transaction"]["providers"][0][
        "provider_id"
    ]
    with pytest.raises(ValidationError):
        BitcoinUtxoReplay.model_validate(replay)


def test_bitcoin_hop_rejects_provider_role_relabel() -> None:
    replay = json.loads((PACKAGE / "raw-replay.json").read_text())
    hop_providers = replay["spend_path"][0]["providers"]
    primary = next(item for item in hop_providers if item["role"] == "primary")
    verify = next(item for item in hop_providers if item["role"] == "verify")
    primary["role"], verify["role"] = "verify", "primary"

    with pytest.raises(ValidationError, match="primary provider must be"):
        BitcoinUtxoReplay.model_validate(replay)


def test_independent_verifier_rejects_provider_role_relabel(tmp_path: Path) -> None:
    copied = tmp_path / PACKAGE.name
    shutil.copytree(PACKAGE, copied)
    replay = json.loads((copied / "raw-replay.json").read_text())
    hop_providers = replay["spend_path"][0]["providers"]
    primary = next(item for item in hop_providers if item["role"] == "primary")
    verify = next(item for item in hop_providers if item["role"] == "verify")
    primary["role"], verify["role"] = "verify", "primary"
    (copied / "raw-replay.json").write_text(json.dumps(replay))

    with pytest.raises(ValueError, match="primary provider must be"):
        independently_verify_bitcoin(copied)


def test_bitcoin_replay_rejects_identical_primary_verify_hashes() -> None:
    replay = json.loads((PACKAGE / "raw-replay.json").read_text())
    replay["spend_path"][0]["providers"][0]["artifact_sha256"] = replay["spend_path"][0][
        "providers"
    ][1]["artifact_sha256"]

    with pytest.raises(
        ValidationError,
        match="hop primary and verify artifact SHA-256 must differ",
    ):
        BitcoinUtxoReplay.model_validate(replay)


def test_bitcoin_replay_rejects_duplicate_spent_outpoint() -> None:
    replay = json.loads((PACKAGE / "raw-replay.json").read_text())
    replay["transaction"]["inputs"].append(replay["transaction"]["inputs"][0])
    with pytest.raises(ValidationError):
        BitcoinUtxoReplay.model_validate(replay)


def test_bitcoin_request_rejects_evm_chain() -> None:
    document = _document()
    document["chain_id"] = 1
    with pytest.raises(ContractViolation):
        validate_analysis_request(document)


def test_bitcoin_transaction_binding_is_exact() -> None:
    document = _document()
    document["inputs"]["transaction_id"] = "0" * 64
    request = validate_analysis_request(document).root
    assert isinstance(request, BitcoinUtxoAnalysisRequest)
    result = analyze_bitcoin_utxo_replay(
        request, (PACKAGE / "raw-replay.json").read_bytes(), package_dir=PACKAGE
    )
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_bitcoin_start_vout_must_exist() -> None:
    document = _document()
    document["inputs"]["start_vout"] = 99
    request = validate_analysis_request(document).root
    assert isinstance(request, BitcoinUtxoAnalysisRequest)
    result = analyze_bitcoin_utxo_replay(
        request, (PACKAGE / "raw-replay.json").read_bytes(), package_dir=PACKAGE
    )
    assert result.root.status == "failed"
    assert result.root.errors[0].stage == "start_outpoint"


def test_bitcoin_spend_path_depths_must_be_contiguous() -> None:
    replay = json.loads((PACKAGE / "raw-replay.json").read_text())
    extra = replay["spend_path"][0].copy()
    extra["depth"] = 3
    replay["spend_path"].append(extra)

    with pytest.raises(ValidationError, match="depths must be contiguous"):
        BitcoinUtxoReplay.model_validate(replay)


def test_bitcoin_unrelated_next_hop_is_rejected_by_independent_verifier(
    tmp_path: Path,
) -> None:
    copied = tmp_path / PACKAGE.name
    shutil.copytree(PACKAGE, copied)
    replay = json.loads((copied / "raw-replay.json").read_text())
    unrelated = json.loads(json.dumps(replay["spend_path"][0]))
    unrelated["depth"] = 2
    replay["spend_path"].append(unrelated)
    (copied / "raw-replay.json").write_text(json.dumps(replay))

    with pytest.raises(ValueError, match="spend path chain differs"):
        independently_verify_bitcoin(copied)


def test_bitcoin_missing_spend_path_is_partial() -> None:
    replay = json.loads((PACKAGE / "raw-replay.json").read_text())
    replay["spend_path"] = []
    result = analyze_bitcoin_utxo_replay(
        _request(),
        json.dumps(replay).encode(),
        package_dir=PACKAGE,
    )
    assert result.root.status == "partial"
    assert result.root.results[0].value["frontier_outpoints"] == []
    assert result.root.errors[0].code == "evidence_incomplete"


def test_bitcoin_source_set_binding_is_exact() -> None:
    document = _document()
    document["source_policy"]["allowed_source_ids"].append("DS-BTC-OTHER")
    document["source_policy"]["source_order"].append("DS-BTC-OTHER")
    request = validate_analysis_request(document).root
    assert isinstance(request, BitcoinUtxoAnalysisRequest)
    result = analyze_bitcoin_utxo_replay(
        request, (PACKAGE / "raw-replay.json").read_bytes(), package_dir=PACKAGE
    )
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "rule_restricted"


def test_bitcoin_replay_drift_from_artifact_is_rejected() -> None:
    replay = json.loads((PACKAGE / "raw-replay.json").read_text())
    replay["transaction"]["block_time"] += 1
    result = analyze_bitcoin_utxo_replay(
        _request(),
        json.dumps(replay).encode(),
        package_dir=PACKAGE,
    )
    assert result.root.status == "failed"
    assert result.root.errors[0].stage == "artifact_reconciliation"


def test_bitcoin_artifact_mutation_is_rejected(
    tmp_path: Path,
) -> None:
    copied = tmp_path / PACKAGE.name
    shutil.copytree(PACKAGE, copied)
    artifact = copied / "artifacts/mempool-hop1-raw.json"
    artifact.write_bytes(artifact.read_bytes() + b" ")

    result = analyze_bitcoin_utxo_replay(
        _request(),
        (copied / "raw-replay.json").read_bytes(),
        package_dir=copied,
    )
    assert result.root.status == "failed"
    assert result.root.errors[0].stage == "artifact_reconciliation"
    with pytest.raises(ValueError, match="artifact hash mismatch"):
        independently_verify_bitcoin(copied)


def test_bitcoin_missing_publicnode_hop_artifact_is_rejected(
    tmp_path: Path,
) -> None:
    copied = tmp_path / PACKAGE.name
    shutil.copytree(PACKAGE, copied)
    (copied / "artifacts/publicnode-hop1-raw.json").unlink()

    result = analyze_bitcoin_utxo_replay(
        _request(),
        (copied / "raw-replay.json").read_bytes(),
        package_dir=copied,
    )

    assert result.root.status == "failed"
    assert result.root.errors[0].stage == "artifact_reconciliation"
    with pytest.raises(ValueError, match="provider artifact missing"):
        independently_verify_bitcoin(copied)


def test_bitcoin_publicnode_hop_fact_mismatch_is_rejected(
    tmp_path: Path,
) -> None:
    copied = tmp_path / PACKAGE.name
    shutil.copytree(PACKAGE, copied)
    artifact = copied / "artifacts/publicnode-hop1-raw.json"
    publicnode = json.loads(artifact.read_text())
    publicnode["result"]["vout"][0]["value"] = 0.00142099
    artifact_body = json.dumps(publicnode, separators=(",", ":")).encode()
    artifact.write_bytes(artifact_body)

    replay_path = copied / "raw-replay.json"
    replay = json.loads(replay_path.read_text())
    replay["spend_path"][0]["providers"][0]["artifact_sha256"] = hashlib.sha256(
        artifact_body
    ).hexdigest()
    replay_path.write_text(json.dumps(replay))

    result = analyze_bitcoin_utxo_replay(
        _request(),
        replay_path.read_bytes(),
        package_dir=copied,
    )

    assert result.root.status == "failed"
    assert result.root.errors[0].stage == "artifact_reconciliation"
    with pytest.raises(ValueError, match="PublicNode spend projection differs"):
        independently_verify_bitcoin(copied)


def test_independent_verifier_rejects_replay_and_expected_joint_drift(
    tmp_path: Path,
) -> None:
    copied = tmp_path / PACKAGE.name
    shutil.copytree(PACKAGE, copied)
    replay = json.loads((copied / "raw-replay.json").read_text())
    expected = json.loads((copied / "expected.json").read_text())
    replay["transaction"]["block_height"] += 1
    expected["expected_results"][0]["value"]["block_height"] += 1
    (copied / "raw-replay.json").write_text(json.dumps(replay))
    (copied / "expected.json").write_text(json.dumps(expected))

    with pytest.raises(ValueError, match="root replay differs"):
        independently_verify_bitcoin(copied)


def test_independent_verifier_rejects_artifact_mutation(
    tmp_path: Path,
) -> None:
    copied = tmp_path / PACKAGE.name
    shutil.copytree(PACKAGE, copied)
    artifact = copied / "artifacts/blockstream-supporting.json"
    artifact.write_bytes(artifact.read_bytes() + b" ")

    with pytest.raises(ValueError, match="artifact hash mismatch"):
        independently_verify_bitcoin(copied)


def test_change_is_only_a_heuristic_candidate() -> None:
    document = _document()
    document["analysis_id"] = "AN-BTC-HEURISTIC-001"
    document["query_kind"] = "assess_heuristics"
    document["inputs"]["assess_change"] = True
    document["inputs"]["assess_coinjoin"] = True
    request = validate_analysis_request(document).root
    assert isinstance(request, BitcoinUtxoAnalysisRequest)
    result = analyze_bitcoin_utxo_replay(
        request, (PACKAGE / "raw-replay.json").read_bytes(), package_dir=PACKAGE
    )
    heuristic = result.root.results[1]
    assert heuristic.classification == "heuristic"
    assert heuristic.value["change_candidates"][0]["classification"] == "heuristic_candidate"
    assert heuristic.value["coinjoin_assessment"]["ownership"] == "not_assessed"


@pytest.mark.parametrize(
    ("category", "status"),
    [
        ("fee_mismatch", "failed"),
        ("missing_prevout", "partial"),
        ("duplicate_outpoint", "failed"),
        ("change_overclaim", "failed"),
        ("coinjoin_overclaim", "failed"),
        ("equal_output_candidate", "partial"),
        ("complete_control", "complete"),
    ],
)
def test_bitcoin_negative_oracles(category: str, status: str) -> None:
    case = BitcoinOracleCase(
        oracle_id=f"OR-BTC-{category.upper().replace('_', '-')}",
        category=category,
        facts={"synthetic": True},
    )
    assert evaluate_bitcoin_oracle(case).status == status


def test_bitcoin_replay_is_deterministic() -> None:
    body = (PACKAGE / "raw-replay.json").read_bytes()
    first = analyze_bitcoin_utxo_replay(_request(), body, package_dir=PACKAGE)
    second = analyze_bitcoin_utxo_replay(_request(), body, package_dir=PACKAGE)
    assert first.to_contract_dict() == second.to_contract_dict()
