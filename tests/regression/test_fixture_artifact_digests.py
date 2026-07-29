import hashlib
import runpy
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = runpy.run_path(
    str(REPOSITORY_ROOT / "docs" / "05_QA_Validation" / "scripts" / "validate_fixture_schemas.py")
)
validate_artifact_digests = VALIDATOR["validate_artifact_digests"]


def test_content_addressed_artifact_accepts_matching_bytes(tmp_path: Path) -> None:
    package = tmp_path / "FX-TEST-001"
    artifact_root = package / "artifacts" / "sha256"
    artifact_root.mkdir(parents=True)
    payload = b"selected fixture row\n"
    digest = hashlib.sha256(payload).hexdigest()
    (artifact_root / f"{digest}.txt").write_bytes(payload)

    assert validate_artifact_digests(package) == []


def test_content_addressed_artifact_rejects_tampered_bytes(tmp_path: Path) -> None:
    package = tmp_path / "FX-TEST-001"
    artifact_root = package / "artifacts" / "sha256"
    artifact_root.mkdir(parents=True)
    original = b"selected fixture row\n"
    digest = hashlib.sha256(original).hexdigest()
    (artifact_root / f"{digest}.txt").write_bytes(b"tampered fixture row\n")

    errors = validate_artifact_digests(package)

    assert len(errors) == 1
    assert "content-addressed artifact digest mismatch" in errors[0]
