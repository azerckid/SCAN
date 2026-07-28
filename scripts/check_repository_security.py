"""Reject obvious secrets and user-local paths from runtime and evidence files."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = (
    ROOT / "src",
    ROOT / "docs/05_QA_Validation/fixtures",
    ROOT / "docs/05_QA_Validation/examples",
)
PATTERNS = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(rb"Authorization\s*:\s*Bearer\s+\S+", re.IGNORECASE),
    re.compile(rb"/Users/[^/<\s]+/"),
    re.compile(rb"/home/[^/<\s]+/"),
    re.compile(rb"[A-Za-z]:\\Users\\[^\\<\s]+\\"),
)
ALLOWED_PATTERN_DEFINITION = ROOT / "src/scan_tool/application/security.py"


def main() -> None:
    checked = 0
    for root in SCAN_ROOTS:
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            if path == ALLOWED_PATTERN_DEFINITION or "__pycache__" in path.parts:
                continue
            body = path.read_bytes()
            for pattern in PATTERNS:
                assert not pattern.search(body), (
                    f"sensitive material pattern found in {path.relative_to(ROOT)}"
                )
            checked += 1
    print(f"PASS repository security scan: {checked} runtime/evidence files")


if __name__ == "__main__":
    main()
