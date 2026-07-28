"""Validate TASK-009 document links, IDs, and fixture-to-example values."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
LINK_PATTERN = re.compile(r"\[[^\]]*]\(([^)]+)\)")
TASK_PATTERN = re.compile(r"^### \[[ x]] (TASK-\d{3}):", re.MULTILINE)
QA_PATTERN = re.compile(r"^### (QA-[A-Z]+-\d{3})", re.MULTILINE)


def _load(relative: str) -> dict[str, object]:
    return json.loads((ROOT / relative).read_text())


def _result_values(name: str) -> dict[str, dict[str, object]]:
    document = _load(f"docs/05_QA_Validation/examples/analysis/{name}-result.json")
    return {item["result_type"]: item["value"] for item in document["results"]}  # type: ignore[index]


def _assert_fields_equal(
    expected: dict[str, object],
    actual: dict[str, object],
    fields: tuple[str, ...],
) -> None:
    missing_expected = tuple(field for field in fields if field not in expected)
    missing_actual = tuple(field for field in fields if field not in actual)
    assert not missing_expected, f"expected fixture fields are missing: {missing_expected}"
    assert not missing_actual, f"analysis result fields are missing: {missing_actual}"
    for field in fields:
        assert actual[field] == expected[field], (
            f"{field} differs: {actual[field]!r} != {expected[field]!r}"
        )


def check_links() -> int:
    checked = 0
    for path in sorted(DOCS.rglob("*.md")):
        for raw_link in LINK_PATTERN.findall(path.read_text()):
            link = raw_link.split("#", 1)[0]
            if not link or link.startswith(("http://", "https://", "mailto:")):
                continue
            target = (path.parent / link).resolve()
            assert target.exists(), f"broken relative link: {path.relative_to(ROOT)} -> {raw_link}"
            checked += 1
    return checked


def check_ids() -> tuple[int, int]:
    backlog = (DOCS / "04_Logic_Progress/00_BACKLOG.md").read_text()
    scenarios = (DOCS / "05_QA_Validation/01_TEST_SCENARIOS.md").read_text()
    task_ids = TASK_PATTERN.findall(backlog)
    qa_ids = QA_PATTERN.findall(scenarios)
    assert len(task_ids) == len(set(task_ids)) == 10, "TASK IDs must be unique TASK-001~010"
    assert len(qa_ids) == len(set(qa_ids)) == 24, "QA IDs must be 24 unique definitions"
    return len(task_ids), len(qa_ids)


def check_fixture_values() -> None:
    dex_expected = _load("docs/05_QA_Validation/fixtures/FX-SVC-DEX-001/expected.json")
    dex = _result_values("dex")
    asset_fields = ("token_address", "symbol", "decimals", "amount_raw")
    _assert_fields_equal(  # type: ignore[arg-type,index]
        dex_expected["asset_in"],
        dex["asset_in"],
        asset_fields,
    )
    _assert_fields_equal(  # type: ignore[arg-type,index]
        dex_expected["pool_output"],
        dex["pool_output"],
        asset_fields,
    )
    _assert_fields_equal(  # type: ignore[arg-type,index]
        dex_expected["user_net_output"],
        dex["user_net_output"],
        (*asset_fields, "asset_type", "from", "to"),
    )

    auth_expected = _load("docs/05_QA_Validation/fixtures/FX-EVM-AUTH-001/expected.json")
    auth = _result_values("auth")
    _assert_fields_equal(  # type: ignore[arg-type,index]
        auth_expected["approval"],
        auth["approval"],
        ("type", "owner", "spender", "amount_raw"),
    )
    allowance = auth_expected["allowance"]  # type: ignore[assignment]
    assert auth["allowance_lifecycle"] == {
        "before_approval_raw": allowance["before_approval"]["amount_raw"],  # type: ignore[index]
        "after_approval_raw": allowance["after_approval"]["amount_raw"],  # type: ignore[index]
        "before_consumption_raw": allowance["before_consumption"]["amount_raw"],  # type: ignore[index]
        "after_consumption_raw": allowance["after_consumption"]["amount_raw"],  # type: ignore[index]
        "consumed_delta_raw": allowance["consumed_delta_raw"],  # type: ignore[index]
    }
    _assert_fields_equal(
        auth_expected["consumption"],  # type: ignore[arg-type,index]
        auth["authorization_consumption"],
        ("method", "from", "to", "amount_raw"),
    )
    assert auth["theft_or_phishing_attribution"]["theft_or_phishing_claim"] is False

    freeze_expected = _load("docs/05_QA_Validation/fixtures/FX-EVM-FREEZE-001/expected.json")
    freeze = _result_values("freeze")
    transitions = freeze_expected["address_freeze"]["transitions"]  # type: ignore[index]
    for result_type, transition in zip(
        ("blacklist_transition", "unblacklist_transition"),
        transitions,
        strict=True,
    ):
        assert freeze[result_type] == {
            "target_address": freeze_expected["address_freeze"]["target_address"],  # type: ignore[index]
            "before": transition["state_before"],
            "after": transition["state_after"],
            "before_block": transition["block_number"] - 1,
            "after_block": transition["block_number"],
        }
    scope = freeze["official_context_scope"]
    assert scope["circle_address_specific"] is False
    assert scope["ofac_address_specific"] is True
    assert scope["current_sanctions_status"] == "not_assessed"
    assert scope["criminal_intent"] == "not_assessed"
    _assert_fields_equal(
        freeze_expected["token_pause"],  # type: ignore[arg-type,index]
        scope["global_pause"],  # type: ignore[arg-type]
        ("applicable",),
    )


def main() -> None:
    links = check_links()
    tasks, qa = check_ids()
    check_fixture_values()
    print(
        f"PASS repository traceability: {links} links, "
        f"{tasks} TASK IDs, {qa} QA IDs, 3 fixture/example mappings"
    )


if __name__ == "__main__":
    main()
