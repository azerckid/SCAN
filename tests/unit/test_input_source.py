"""Bounded provided-artifact normalization tests."""

import json
from datetime import UTC, datetime

import pytest

from scan_tool.adapters.input_source import ProvidedArtifactImporter
from scan_tool.domain.input_source import (
    ArtifactFormat,
    ChainScope,
    InputFailureKind,
    InputNormalizationError,
    require_chain_scope,
)


def test_json_array_is_bounded_and_deterministic() -> None:
    raw = json.dumps(
        [
            {"chain_scope": "evm", "transaction_hash": "0x01"},
            {"chain_scope": "evm", "transaction_hash": "0x02"},
        ],
        separators=(",", ":"),
    ).encode()
    importer = ProvidedArtifactImporter()
    observed_at = datetime(2026, 7, 29, tzinfo=UTC)

    first = importer.import_bytes(
        raw,
        artifact_format=ArtifactFormat.JSON,
        chain_scope=ChainScope.EVM,
        record_type="transaction",
        observed_at=observed_at,
    )
    second = importer.import_bytes(
        raw,
        artifact_format=ArtifactFormat.JSON,
        chain_scope=ChainScope.EVM,
        record_type="transaction",
        observed_at=observed_at,
    )

    assert first == second
    assert [record.record_locator for record in first.records] == ["json:$[0]", "json:$[1]"]
    assert len(first.raw_sha256) == 64


def test_json_rpc_artifact_unwraps_to_its_result() -> None:
    bundle = ProvidedArtifactImporter().import_bytes(
        b'{"jsonrpc":"2.0","id":1,"result":{"number":"0x10"}}',
        artifact_format=ArtifactFormat.JSON,
        chain_scope=ChainScope.EVM,
        record_type="block",
    )

    assert bundle.records[0].data == {"number": "0x10"}


def test_normalized_bundle_repr_does_not_reflect_record_data() -> None:
    bundle = ProvidedArtifactImporter().import_bytes(
        b'{"note":"SECRET_CANARY"}',
        artifact_format=ArtifactFormat.JSON,
        chain_scope=ChainScope.EVM,
    )

    assert "SECRET_CANARY" not in repr(bundle)


def test_jsonl_preserves_line_locators() -> None:
    bundle = ProvidedArtifactImporter().import_bytes(
        b'{"value":"1"}\n\n{"value":"2"}\n',
        artifact_format=ArtifactFormat.JSONL,
        chain_scope=ChainScope.BITCOIN,
        record_type="utxo",
    )

    assert [record.record_locator for record in bundle.records] == [
        "jsonl:line=1",
        "jsonl:line=3",
    ]


def test_csv_preserves_rows_as_string_values() -> None:
    bundle = ProvidedArtifactImporter().import_bytes(
        b"txid,value_sat\nabc,42\n",
        artifact_format=ArtifactFormat.CSV,
        chain_scope=ChainScope.BITCOIN,
        record_type="transaction",
    )

    assert bundle.records[0].record_locator == "csv:row=2"
    assert bundle.records[0].data == {"txid": "abc", "value_sat": "42"}


@pytest.mark.parametrize(
    ("raw", "artifact_format", "safe_message"),
    [
        (b"", ArtifactFormat.JSON, "provided artifact must not be empty"),
        (b"{", ArtifactFormat.JSON, "provided artifact could not be parsed"),
        (
            b'{"SECRET_CANARY":1}\n{',
            ArtifactFormat.JSONL,
            "provided artifact could not be parsed",
        ),
        (b"\xff", ArtifactFormat.CSV, "provided artifact is not valid UTF-8"),
        (b"null", ArtifactFormat.JSON, "provided artifact contains a null record"),
        (
            b'{"value":NaN}',
            ArtifactFormat.JSON,
            "provided artifact could not be parsed",
        ),
        (
            b"a,a\n1,2\n",
            ArtifactFormat.CSV,
            "provided artifact could not be parsed",
        ),
        (
            b"a\n1,2\n",
            ArtifactFormat.CSV,
            "provided artifact could not be parsed",
        ),
    ],
)
def test_invalid_artifacts_fail_without_reflecting_raw_input(
    raw: bytes,
    artifact_format: ArtifactFormat,
    safe_message: str,
) -> None:
    with pytest.raises(InputNormalizationError) as captured:
        ProvidedArtifactImporter().import_bytes(
            raw,
            artifact_format=artifact_format,
            chain_scope=ChainScope.EVM,
        )

    assert captured.value.kind is InputFailureKind.INVALID_ARTIFACT
    assert str(captured.value) == safe_message
    assert "SECRET_CANARY" not in str(captured.value)


def test_artifact_byte_and_record_limits_are_enforced() -> None:
    with pytest.raises(InputNormalizationError) as too_large:
        ProvidedArtifactImporter(max_bytes=2).import_bytes(
            b"{} ",
            artifact_format=ArtifactFormat.JSON,
            chain_scope=ChainScope.EVM,
        )
    assert too_large.value.kind is InputFailureKind.ARTIFACT_TOO_LARGE

    with pytest.raises(InputNormalizationError) as too_many:
        ProvidedArtifactImporter(max_records=1).import_bytes(
            b"[{},{}]",
            artifact_format=ArtifactFormat.JSON,
            chain_scope=ChainScope.EVM,
        )
    assert too_many.value.kind is InputFailureKind.TOO_MANY_RECORDS


def test_declared_chain_scope_must_match() -> None:
    with pytest.raises(InputNormalizationError) as captured:
        ProvidedArtifactImporter().import_bytes(
            b'{"chain_scope":"bitcoin","txid":"abc"}',
            artifact_format=ArtifactFormat.JSON,
            chain_scope=ChainScope.EVM,
        )

    assert captured.value.kind is InputFailureKind.CHAIN_SCOPE_MISMATCH


def test_analyzer_scope_guard_rejects_bitcoin_as_evm() -> None:
    bundle = ProvidedArtifactImporter().import_bytes(
        b'{"txid":"abc"}',
        artifact_format=ArtifactFormat.JSON,
        chain_scope=ChainScope.BITCOIN,
    )

    with pytest.raises(InputNormalizationError) as captured:
        require_chain_scope(bundle, ChainScope.EVM)

    assert captured.value.kind is InputFailureKind.CHAIN_SCOPE_MISMATCH


def test_artifact_observed_at_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="UTC offset"):
        ProvidedArtifactImporter().import_bytes(
            b'{"ok":true}',
            artifact_format=ArtifactFormat.JSON,
            chain_scope=ChainScope.EVM,
            observed_at=datetime(2026, 7, 29),
        )
