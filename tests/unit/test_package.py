from importlib.metadata import version

from scan_tool import __version__


def test_package_version_matches_metadata() -> None:
    assert __version__ == version("scan-forensics-tool")
