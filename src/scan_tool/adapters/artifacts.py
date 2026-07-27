"""Atomic SHA-256 content-addressed artifact storage."""

import hashlib
import os
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from scan_tool.application.security import SensitiveDataGuard
from scan_tool.domain.storage import ArtifactRecord

type Clock = Callable[[], datetime]


class ArtifactIntegrityError(ValueError):
    """Raised when an existing content-addressed file does not match its name."""


class ArtifactStore:
    def __init__(
        self,
        root: Path,
        *,
        guard: SensitiveDataGuard | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.root = root
        self._guard = guard or SensitiveDataGuard()
        self._clock = clock or (lambda: datetime.now(UTC))

    def write(
        self,
        body: bytes,
        *,
        media_type: str,
        artifact_kind: str,
        redaction_status: str = "not_required",
        license_status: str = "unknown",
        source_id: str | None = None,
        retrieved_at: datetime | None = None,
    ) -> ArtifactRecord:
        self._guard.check_bytes(body)
        sha256 = hashlib.sha256(body).hexdigest()
        relative_path = Path("artifacts") / sha256[:2] / sha256
        destination = self.root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists():
            self._verify_file(destination, sha256, len(body))
        else:
            self._atomic_write(destination, body)

        return ArtifactRecord(
            sha256=sha256,
            byte_length=len(body),
            media_type=media_type,
            relative_path=relative_path.as_posix(),
            artifact_kind=artifact_kind,
            redaction_status=redaction_status,
            license_status=license_status,
            created_at=self._clock(),
            source_id=source_id,
            retrieved_at=retrieved_at,
        )

    def read(self, record: ArtifactRecord) -> bytes:
        path = self.root / record.relative_path
        self._verify_file(path, record.sha256, record.byte_length)
        return path.read_bytes()

    def _atomic_write(self, destination: Path, body: bytes) -> None:
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=destination.parent,
                prefix=".artifact-",
                delete=False,
            ) as temporary:
                temporary.write(body)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            try:
                os.link(temporary_path, destination)
            except FileExistsError:
                self._verify_file(destination, hashlib.sha256(body).hexdigest(), len(body))
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    @staticmethod
    def _verify_file(path: Path, expected_sha256: str, expected_length: int) -> None:
        try:
            body = path.read_bytes()
        except FileNotFoundError as exc:
            raise ArtifactIntegrityError("artifact file is missing") from exc
        if len(body) != expected_length or hashlib.sha256(body).hexdigest() != expected_sha256:
            raise ArtifactIntegrityError("artifact content does not match its metadata")
