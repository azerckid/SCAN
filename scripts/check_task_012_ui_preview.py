"""Validate the static TASK-012 EVM Core UI Preview contract."""

import json
from html.parser import HTMLParser
from itertools import product
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PREVIEW_PATH = REPOSITORY_ROOT / "docs/02_UI_Screens/previews/04_task_012_evm_core_cli_preview.html"
PROPOSAL_PATH = (
    REPOSITORY_ROOT
    / "docs/05_QA_Validation/examples/task-012/TASK-012-ANALYSIS-CONTRACT-PROPOSAL.json"
)

EXPECTED_QUERIES = {
    "object_summary",
    "historical_balance",
    "first_token_transfer",
    "native_inflow",
}
EXPECTED_STATES = {"complete", "partial", "failed"}
REQUIRED_MARKERS = {
    "USER REVIEW PASSED",
    "Runtime not implemented",
    "No network, file, DB, or external API calls",
    "COMPLETE RESULT",
    "data: null",
    "range_complete",
    "trace_complete",
    "token_address",
    "fee_paid_wei",
}
FORBIDDEN_MARKERS = {
    "CONFIRMED RESULT",
    "fetch(",
    "XMLHttpRequest",
    "WebSocket(",
    "EventSource(",
    "http://",
    "https://",
}


def _contract_markers(cases: list[dict[str, object]]) -> set[str]:
    """Return raw values and structured errors that the Preview must preserve."""

    complete_by_query = {
        case["request"]["query_kind"]: case for case in cases if case["scenario"] == "complete"
    }
    return {
        complete_by_query["object_summary"]["result"]["data"]["fee_paid_wei"],
        *(
            balance["amount_raw"]
            for balance in complete_by_query["historical_balance"]["result"]["data"]["balances"]
        ),
        complete_by_query["first_token_transfer"]["result"]["data"]["transfer"]["amount_raw"],
        str(complete_by_query["first_token_transfer"]["result"]["data"]["transfer"]["log_index"]),
        complete_by_query["native_inflow"]["result"]["data"]["internal_inflow_wei"],
        *(
            marker
            for case in cases
            for error in case["result"]["errors"]
            for marker in (error["code"], error["stage"])
        ),
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
    proposal = json.loads(PROPOSAL_PATH.read_text(encoding="utf-8"))
    cases = proposal["cases"]
    parser = PreviewParser()
    parser.feed(source)

    if len(cases) != 12:
        raise ValueError("TASK-012 proposal must contain exactly 12 UI contract cases")
    case_ids = [case["case_id"] for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("TASK-012 proposal contains duplicate case IDs")
    contract_matrix = {(case["request"]["query_kind"], case["scenario"]) for case in cases}
    expected_matrix = set(product(EXPECTED_QUERIES, EXPECTED_STATES))
    if contract_matrix != expected_matrix:
        raise ValueError("TASK-012 proposal query/state matrix drifted")

    if len(parser.ids) != len(set(parser.ids)):
        raise ValueError("TASK-012 Preview contains duplicate HTML IDs")
    if set(parser.queries) != EXPECTED_QUERIES or len(parser.queries) != 4:
        raise ValueError("TASK-012 Preview query tabs drifted from the contract")
    if set(parser.states) != EXPECTED_STATES or len(parser.states) != 3:
        raise ValueError("TASK-012 Preview state tabs drifted from the contract")
    if parser.scripts != 1:
        raise ValueError("TASK-012 Preview requires exactly one inline script")

    missing = sorted(
        marker
        for marker in REQUIRED_MARKERS | _contract_markers(cases) | set(case_ids)
        if marker not in source
    )
    if missing:
        raise ValueError(f"TASK-012 Preview drifted from contract markers: {missing}")
    repeated_case_ids = sorted(case_id for case_id in case_ids if source.count(case_id) != 1)
    if repeated_case_ids:
        raise ValueError(
            f"TASK-012 Preview must map every contract case exactly once: {repeated_case_ids}"
        )
    forbidden = sorted(marker for marker in FORBIDDEN_MARKERS if marker in source)
    if forbidden:
        raise ValueError(f"TASK-012 Preview contains external-call markers: {forbidden}")

    print(
        "PASS TASK-012 UI Preview: 4 queries, 3 states, 12 contract-linked cases, no external calls"
    )


if __name__ == "__main__":
    main()
