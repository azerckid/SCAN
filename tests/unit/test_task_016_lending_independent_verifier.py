import json
import shutil
from pathlib import Path

import pytest

from scan_tool.application.task_016_lending_independent_verifier import (
    verify_fixture,
    verify_repository,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "docs/05_QA_Validation/fixtures"
PACKAGE = FIXTURE_ROOT / "FX-SVC-LEND-001"
PINNED = "6c51b2ebfaef49ca8639053ffb2c1be446eb2ba7fbc39cf963780c26ed240f3c"


def test_independent_verifier_passes_confirmed_package() -> None:
    reports = verify_repository(FIXTURE_ROOT)
    assert reports[0]["fixture_id"] == "FX-SVC-LEND-001"
    assert reports[0]["status"] == "pass"
    assert reports[0]["calculated_sha256"] == PINNED


def test_independent_verifier_detects_canonical_drift(tmp_path: Path) -> None:
    package = tmp_path / "FX-SVC-LEND-001-tamper"
    shutil.copytree(PACKAGE, package)
    expected = json.loads((package / "expected.json").read_text(encoding="utf-8"))
    expected["defi_lending"]["attribution"]["attack_vs_normal"] = "attack"
    (package / "expected.json").write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    try:
        verify_fixture(
            package,
            json.loads((package / "raw-replay.json").read_text(encoding="utf-8")),
            json.loads((package / "provider-replay.json").read_text(encoding="utf-8")),
            json.loads((package / "artifacts/capture-meta.json").read_text(encoding="utf-8")),
            expected,
            json.loads((package / "evidence.json").read_text(encoding="utf-8")),
        )
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_independent_verifier_rejects_capture_endpoint_relabel(tmp_path: Path) -> None:
    package = tmp_path / "FX-SVC-LEND-001-capture-relabel"
    shutil.copytree(PACKAGE, package)
    capture = json.loads((package / "artifacts/capture-meta.json").read_text(encoding="utf-8"))
    capture["capabilities"][0]["endpoint"] = "https://ethereum.rpc.thirdweb.com"
    try:
        verify_fixture(
            package,
            json.loads((package / "raw-replay.json").read_text(encoding="utf-8")),
            json.loads((package / "provider-replay.json").read_text(encoding="utf-8")),
            capture,
            json.loads((package / "expected.json").read_text(encoding="utf-8")),
            json.loads((package / "evidence.json").read_text(encoding="utf-8")),
        )
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_independent_verifier_rejects_future_capture_timestamp(tmp_path: Path) -> None:
    package = tmp_path / "FX-SVC-LEND-001-future"
    shutil.copytree(PACKAGE, package)
    future = "2999-01-01T00:00:00Z"
    for name in ("raw-replay.json", "provider-replay.json", "artifacts/capture-meta.json"):
        path = package / name
        value = json.loads(path.read_text(encoding="utf-8"))
        value["captured_at"] = future
        if name == "provider-replay.json":
            for item in value["providers"]:
                item["retrieved_at"] = future
        if name.endswith("capture-meta.json"):
            for item in value["capabilities"]:
                item["captured_at"] = future
        path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="future"):
        verify_fixture(
            package,
            json.loads((package / "raw-replay.json").read_text(encoding="utf-8")),
            json.loads((package / "provider-replay.json").read_text(encoding="utf-8")),
            json.loads((package / "artifacts/capture-meta.json").read_text(encoding="utf-8")),
            json.loads((package / "expected.json").read_text(encoding="utf-8")),
            json.loads((package / "evidence.json").read_text(encoding="utf-8")),
        )
