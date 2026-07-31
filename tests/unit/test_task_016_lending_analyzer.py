import hashlib
import json
import shutil
from collections.abc import Callable
from pathlib import Path

from scan_tool.domain import validate_analysis_request
from scan_tool.domain.analysis_request import DefiLendingAnalysisRequest
from scan_tool.slices.defi_lending import analyze_defi_lending_replay

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "docs/05_QA_Validation/fixtures/FX-SVC-LEND-001"
PINNED_SHA256 = "6c51b2ebfaef49ca8639053ffb2c1be446eb2ba7fbc39cf963780c26ed240f3c"


def _request() -> DefiLendingAnalysisRequest:
    request = validate_analysis_request(
        json.loads((PACKAGE / "analysis-request.json").read_text(encoding="utf-8"))
    ).root
    assert isinstance(request, DefiLendingAnalysisRequest)
    return request


def _hash(value: dict[str, object]) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(canonical).hexdigest()


def _rewrite_receipts(
    package: Path,
    mutate: Callable[[dict[str, object]], None],
) -> None:
    provider = json.loads((package / "provider-replay.json").read_text(encoding="utf-8"))
    raw = json.loads((package / "raw-replay.json").read_text(encoding="utf-8"))
    capture = json.loads((package / "artifacts/capture-meta.json").read_text(encoding="utf-8"))
    for index, provider_item in enumerate(provider["providers"]):
        old_digest = provider_item["raw_sha256"]["receipt"]
        artifact_path = package / "artifacts/sha256" / f"{old_digest}.json"
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        mutate(artifact)
        serialized = (
            json.dumps(artifact, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            if index == 0
            else json.dumps(artifact, sort_keys=True, indent=2, ensure_ascii=True)
        )
        raw_bytes = (serialized + "\n").encode()
        digest = hashlib.sha256(raw_bytes).hexdigest()
        (package / "artifacts/sha256" / f"{digest}.json").write_bytes(raw_bytes)
        provider_item["raw_sha256"]["receipt"] = digest
        raw["raw_observations"][index]["artifacts"]["receipt"] = f"artifact://sha256/{digest}"
        provider_id = provider_item["provider_id"]
        capability = next(
            item
            for item in capture["capabilities"]
            if item["provider_id"] == provider_id and item["capability"] == "receipt"
        )
        capability["response_sha256"] = digest
    (package / "provider-replay.json").write_text(
        json.dumps(provider, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    (package / "raw-replay.json").write_text(
        json.dumps(raw, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    (package / "artifacts/capture-meta.json").write_text(
        json.dumps(capture, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )


def _analyze(package: Path):
    return analyze_defi_lending_replay(
        _request(),
        (package / "raw-replay.json").read_bytes(),
        package_dir=package,
    )


def test_complete_defi_lending_matches_the_pinned_fact_hash() -> None:
    result = analyze_defi_lending_replay(
        _request(),
        (PACKAGE / "raw-replay.json").read_bytes(),
        package_dir=PACKAGE,
    )
    assert result.root.status == "complete"
    assert _hash(result.root.results[0].value) == PINNED_SHA256
    assert result.root.results[0].value["attribution"]["attack_vs_normal"] == "not_assessed"


def test_same_endpoint_masquerading_as_two_providers_is_rejected(tmp_path: Path) -> None:
    package = tmp_path / "FX-SVC-LEND-001-tamper"
    shutil.copytree(PACKAGE, package)
    provider = json.loads((package / "provider-replay.json").read_text(encoding="utf-8"))
    provider["providers"][1]["endpoint"] = provider["providers"][0]["endpoint"]
    (package / "provider-replay.json").write_text(
        json.dumps(provider, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    result = analyze_defi_lending_replay(
        _request(),
        (package / "raw-replay.json").read_bytes(),
        package_dir=package,
    )
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_approved_provider_endpoints_cannot_be_relabeled(tmp_path: Path) -> None:
    package = tmp_path / "FX-SVC-LEND-001-provider-relabel"
    shutil.copytree(PACKAGE, package)
    provider = json.loads((package / "provider-replay.json").read_text(encoding="utf-8"))
    provider["providers"][0]["endpoint"], provider["providers"][1]["endpoint"] = (
        provider["providers"][1]["endpoint"],
        provider["providers"][0]["endpoint"],
    )
    (package / "provider-replay.json").write_text(
        json.dumps(provider, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    result = _analyze(package)
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_capture_metadata_method_tamper_is_rejected(tmp_path: Path) -> None:
    package = tmp_path / "FX-SVC-LEND-001-capture-meta"
    shutil.copytree(PACKAGE, package)
    capture = json.loads((package / "artifacts/capture-meta.json").read_text(encoding="utf-8"))
    capture["capabilities"][0]["method"] = "eth_getTransactionReceipt"
    (package / "artifacts/capture-meta.json").write_text(
        json.dumps(capture, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    result = _analyze(package)
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_identical_primary_verify_artifact_bytes_are_rejected(tmp_path: Path) -> None:
    package = tmp_path / "FX-SVC-LEND-001-identical"
    shutil.copytree(PACKAGE, package)
    provider = json.loads((package / "provider-replay.json").read_text(encoding="utf-8"))
    provider["providers"][1]["raw_sha256"] = dict(provider["providers"][0]["raw_sha256"])
    (package / "provider-replay.json").write_text(
        json.dumps(provider, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    raw = json.loads((package / "raw-replay.json").read_text(encoding="utf-8"))
    primary_arts = raw["raw_observations"][0]["artifacts"]
    raw["raw_observations"][1]["artifacts"] = dict(primary_arts)
    (package / "raw-replay.json").write_text(
        json.dumps(raw, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    result = analyze_defi_lending_replay(
        _request(),
        (package / "raw-replay.json").read_bytes(),
        package_dir=package,
    )
    assert result.root.status == "failed"
    assert result.root.errors[0].code == "reconciliation_failed"


def test_window_violation_fails(tmp_path: Path) -> None:
    package = tmp_path / "FX-SVC-LEND-001-window"
    shutil.copytree(PACKAGE, package)
    raw = json.loads((package / "raw-replay.json").read_text(encoding="utf-8"))
    raw["observation_window"] = {"start_block": 1, "end_block": 2}
    (package / "raw-replay.json").write_text(
        json.dumps(raw, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    request_doc = json.loads((PACKAGE / "analysis-request.json").read_text(encoding="utf-8"))
    request_doc["inputs"]["observation_window"] = {"start_block": 1, "end_block": 2}
    request = validate_analysis_request(request_doc).root
    assert isinstance(request, DefiLendingAnalysisRequest)
    result = analyze_defi_lending_replay(
        request,
        (package / "raw-replay.json").read_bytes(),
        package_dir=package,
    )
    assert result.root.status == "failed"


def test_tampered_liquidation_block_hash_is_rejected(tmp_path: Path) -> None:
    package = tmp_path / "FX-SVC-LEND-001-liquidation-block"
    shutil.copytree(PACKAGE, package)

    def mutate(artifact: dict[str, object]) -> None:
        logs = artifact["result"]["logs"]  # type: ignore[index]
        liquidation = next(log for log in logs if log["topics"][0].lower().startswith("0xe413"))
        liquidation["blockHash"] = "0x" + "00" * 32

    _rewrite_receipts(package, mutate)
    assert _analyze(package).root.status == "failed"


def test_removed_transfer_log_is_rejected(tmp_path: Path) -> None:
    package = tmp_path / "FX-SVC-LEND-001-removed-transfer"
    shutil.copytree(PACKAGE, package)

    def mutate(artifact: dict[str, object]) -> None:
        logs = artifact["result"]["logs"]  # type: ignore[index]
        transfer = next(log for log in logs if log["logIndex"] == "0xa")
        transfer["removed"] = True

    _rewrite_receipts(package, mutate)
    assert _analyze(package).root.status == "failed"


def test_transfer_block_number_tamper_is_rejected(tmp_path: Path) -> None:
    package = tmp_path / "FX-SVC-LEND-001-transfer-block"
    shutil.copytree(PACKAGE, package)

    def mutate(artifact: dict[str, object]) -> None:
        logs = artifact["result"]["logs"]  # type: ignore[index]
        transfer = next(log for log in logs if log["logIndex"] == "0xf")
        transfer["blockNumber"] = "0x140fbf0"

    _rewrite_receipts(package, mutate)
    assert _analyze(package).root.status == "failed"


def test_liquidation_five_topic_shape_is_rejected(tmp_path: Path) -> None:
    package = tmp_path / "FX-SVC-LEND-001-five-topics"
    shutil.copytree(PACKAGE, package)

    def mutate(artifact: dict[str, object]) -> None:
        logs = artifact["result"]["logs"]  # type: ignore[index]
        liquidation = next(log for log in logs if log["logIndex"] == "0x10")
        liquidation["topics"].append("0x" + "00" * 32)

    _rewrite_receipts(package, mutate)
    assert _analyze(package).root.status == "failed"


def test_liquidation_160_byte_data_shape_is_rejected(tmp_path: Path) -> None:
    package = tmp_path / "FX-SVC-LEND-001-wide-data"
    shutil.copytree(PACKAGE, package)

    def mutate(artifact: dict[str, object]) -> None:
        logs = artifact["result"]["logs"]  # type: ignore[index]
        liquidation = next(log for log in logs if log["logIndex"] == "0x10")
        liquidation["data"] += "00" * 32

    _rewrite_receipts(package, mutate)
    assert _analyze(package).root.status == "failed"


def test_erc20_transfer_abi_shape_is_rejected(tmp_path: Path) -> None:
    package = tmp_path / "FX-SVC-LEND-001-transfer-shape"
    shutil.copytree(PACKAGE, package)

    def mutate(artifact: dict[str, object]) -> None:
        logs = artifact["result"]["logs"]  # type: ignore[index]
        transfer = next(log for log in logs if log["logIndex"] == "0x13")
        transfer["data"] += "00" * 32

    _rewrite_receipts(package, mutate)
    assert _analyze(package).root.status == "failed"


def test_earlier_larger_transfer_is_not_a_subsequent_outflow(tmp_path: Path) -> None:
    package = tmp_path / "FX-SVC-LEND-001-earlier-outflow"
    shutil.copytree(PACKAGE, package)

    def mutate(artifact: dict[str, object]) -> None:
        logs = artifact["result"]["logs"]  # type: ignore[index]
        earlier = dict(next(log for log in logs if log["logIndex"] == "0x13"))
        earlier["logIndex"] = "0x9"
        earlier["data"] = "0x" + (2**256 - 1).to_bytes(32, "big").hex()
        logs.append(earlier)

    _rewrite_receipts(package, mutate)
    result = _analyze(package)
    assert result.root.status == "complete"
    assert result.root.results[0].value["subsequent_outflow"]["log_index"] == 19


def test_future_capture_timestamp_is_rejected(tmp_path: Path) -> None:
    package = tmp_path / "FX-SVC-LEND-001-future"
    shutil.copytree(PACKAGE, package)
    raw = json.loads((package / "raw-replay.json").read_text(encoding="utf-8"))
    future = "2999-01-01T00:00:00Z"
    raw["captured_at"] = future
    (package / "raw-replay.json").write_text(
        json.dumps(raw, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    provider = json.loads((package / "provider-replay.json").read_text(encoding="utf-8"))
    for item in provider["providers"]:
        item["retrieved_at"] = future
    provider["captured_at"] = future
    (package / "provider-replay.json").write_text(
        json.dumps(provider, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    capture = json.loads((package / "artifacts/capture-meta.json").read_text(encoding="utf-8"))
    capture["captured_at"] = future
    for item in capture["capabilities"]:
        item["captured_at"] = future
    (package / "artifacts/capture-meta.json").write_text(
        json.dumps(capture, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    result = _analyze(package)
    assert result.root.status == "failed"
