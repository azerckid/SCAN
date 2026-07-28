"""Validate the static TASK-012 EVM Core UI Preview contract."""

from html.parser import HTMLParser
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PREVIEW_PATH = REPOSITORY_ROOT / "docs/02_UI_Screens/previews/04_task_012_evm_core_cli_preview.html"

EXPECTED_QUERIES = {
    "object_summary",
    "historical_balance",
    "first_token_transfer",
    "native_inflow",
}
EXPECTED_STATES = {"complete", "partial", "failed"}
REQUIRED_MARKERS = {
    "USER REVIEW PENDING",
    "Runtime not implemented",
    "No network, file, DB, or external API calls",
    "data: null",
    "8115326069137440",
    "148897435437879000853",
    "26470158088",
    "25000000000",
    "14449515027026387018",
    "range_complete",
    "trace_complete",
    "token_address",
    "fee_paid_wei",
}
FORBIDDEN_MARKERS = {
    "fetch(",
    "XMLHttpRequest",
    "WebSocket(",
    "EventSource(",
    "http://",
    "https://",
}


class PreviewParser(HTMLParser):
    """Collect IDs and query/state data attributes without external dependencies."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.queries: list[str] = []
        self.states: list[str] = []
        self.scripts = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"])
        if values.get("data-query"):
            self.queries.append(values["data-query"])
        if values.get("data-state"):
            self.states.append(values["data-state"])
        if tag == "script":
            self.scripts += 1


def main() -> None:
    source = PREVIEW_PATH.read_text(encoding="utf-8")
    parser = PreviewParser()
    parser.feed(source)

    if len(parser.ids) != len(set(parser.ids)):
        raise ValueError("TASK-012 Preview contains duplicate HTML IDs")
    if set(parser.queries) != EXPECTED_QUERIES or len(parser.queries) != 4:
        raise ValueError("TASK-012 Preview query tabs drifted from the contract")
    if set(parser.states) != EXPECTED_STATES or len(parser.states) != 3:
        raise ValueError("TASK-012 Preview state tabs drifted from the contract")
    if parser.scripts != 1:
        raise ValueError("TASK-012 Preview requires exactly one inline script")

    missing = sorted(marker for marker in REQUIRED_MARKERS if marker not in source)
    if missing:
        raise ValueError(f"TASK-012 Preview lacks required markers: {missing}")
    forbidden = sorted(marker for marker in FORBIDDEN_MARKERS if marker in source)
    if forbidden:
        raise ValueError(f"TASK-012 Preview contains external-call markers: {forbidden}")

    print(
        "PASS TASK-012 UI Preview: 4 queries, 3 states, 12 contract combinations, no external calls"
    )


if __name__ == "__main__":
    main()
