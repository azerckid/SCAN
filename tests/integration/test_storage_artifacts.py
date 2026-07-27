"""TASK-004 SQLite, artifact, cache, checkpoint, and export integration tests."""

import asyncio
import copy
import json
import sqlite3
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scan_tool.adapters.artifacts import ArtifactIntegrityError, ArtifactStore
from scan_tool.adapters.sqlite_storage import SQLiteStorage, build_cache_key, canonical_json
from scan_tool.application.export import ResultExporter
from scan_tool.application.security import SensitiveDataError, SensitiveDataGuard
from scan_tool.application.source_orchestration import SourceOrchestrator
from scan_tool.application.storage_orchestration import CachedSourceExecutor, CheckpointRunner
from scan_tool.domain import validate_analysis_request, validate_analysis_result
from scan_tool.domain.analysis_request import SourcePolicy
from scan_tool.domain.source import JsonRpcSourceRequest, SourcePayload

EXAMPLE_ROOT = Path("docs/05_QA_Validation/examples/analysis")
NOW = datetime(2026, 7, 27, 22, 0, tzinfo=UTC)


class CountingAdapter:
    source_id = "DS-EVM-RPC-PUBLIC"
    provider_id = "provider-a"

    def __init__(self) -> None:
        self.call_count = 0

    async def execute(self, request: object) -> SourcePayload:
        self.call_count += 1
        return SourcePayload(
            raw_bytes=b'{"jsonrpc":"2.0","id":1,"result":"0x1"}',
            status_code=200,
            media_type="application/json",
            endpoint_host="rpc.example",
            endpoint_path="/",
            retrieved_at=NOW,
        )


def load_document(name: str, kind: str) -> dict[str, object]:
    return json.loads((EXAMPLE_ROOT / f"{name}-{kind}.json").read_text())


def make_run(
    root: Path,
    name: str = "dex",
    *,
    guard: SensitiveDataGuard | None = None,
) -> tuple[SQLiteStorage, ArtifactStore, object, object]:
    storage = SQLiteStorage(root / "scan.sqlite3", guard=guard)
    artifacts = ArtifactStore(root, guard=guard, clock=lambda: NOW)
    request = validate_analysis_request(load_document(name, "request"))
    result = validate_analysis_result(load_document(name, "result"))
    request_body = (canonical_json(request.to_contract_dict()) + "\n").encode()
    request_artifact = artifacts.write(
        request_body,
        media_type="application/json",
        artifact_kind="request",
    )
    storage.create_run(
        request,
        request_artifact,
        tool_version="test-0.1",
        now=NOW,
    )
    return storage, artifacts, request, result


def test_content_addressed_artifacts_are_atomic_and_verified(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path, clock=lambda: NOW)

    first = store.write(b"same", media_type="text/plain", artifact_kind="raw_response")
    duplicate = store.write(b"same", media_type="text/plain", artifact_kind="raw_response")
    different = store.write(b"same!", media_type="text/plain", artifact_kind="raw_response")

    assert first.sha256 == duplicate.sha256
    assert first.relative_path == duplicate.relative_path
    assert first.sha256 != different.sha256
    assert len([path for path in (tmp_path / "artifacts").rglob("*") if path.is_file()]) == 2
    assert not list((tmp_path / "artifacts").rglob(".artifact-*"))

    (tmp_path / first.relative_path).write_bytes(b"tampered")
    with pytest.raises(ArtifactIntegrityError):
        store.read(first)


def test_immutable_cache_replays_without_second_source_call(tmp_path: Path) -> None:
    storage, artifacts, request_model, _ = make_run(tmp_path)
    adapter = CountingAdapter()
    executor = CachedSourceExecutor(
        SourceOrchestrator([adapter], clock=lambda: NOW),
        storage,
        artifacts,
        clock=lambda: NOW,
    )
    request = JsonRpcSourceRequest(
        capability="chain_id",
        method="eth_chainId",
        params=[],
        block_tag=123,
    )
    live_policy = SourcePolicy.model_validate(
        {
            "rule_status": "allowed",
            "allowed_source_ids": [adapter.source_id],
            "source_order": [adapter.source_id],
            "allow_fallback": False,
            "offline_mode": False,
        }
    )
    offline_policy = live_policy.model_copy(update={"offline_mode": True})

    first = asyncio.run(
        executor.execute(
            analysis_id=request_model.root.analysis_id,
            chain_id=1,
            request=request,
            policy=live_policy,
        )
    )
    second = asyncio.run(
        executor.execute(
            analysis_id=request_model.root.analysis_id,
            chain_id=1,
            request=request,
            policy=offline_policy,
        )
    )

    assert first.response is not None and first.response.cache_status == "miss"
    assert second.response is not None and second.response.cache_status == "hit"
    assert first.response.payload.raw_bytes == second.response.payload.raw_bytes
    assert second.attempts == ()
    assert adapter.call_count == 1
    assert storage.count("cache_entries") == 1
    assert storage.count("source_attempts") == 1
    stored_attempt = storage.list_source_attempts(request_model.root.analysis_id)[0]
    assert stored_attempt["raw_sha256"] == first.response.payload.raw_sha256
    assert stored_attempt["artifact_sha256"] == first.response.payload.raw_sha256
    cache_key = build_cache_key(1, request)
    cached = storage.get_cache(
        cache_key,
        allowed_source_ids=live_policy.allowed_source_ids,
        now=NOW,
    )
    assert cached is not None
    conflicting_artifact = artifacts.write(
        b'{"different":true}',
        media_type="application/json",
        artifact_kind="raw_response",
    )
    storage.record_artifact(conflicting_artifact)
    with pytest.raises(ValueError, match="cache key conflicts"):
        storage.put_cache(replace(cached, artifact_sha256=conflicting_artifact.sha256))
    storage.close()


def test_latest_request_is_not_promoted_to_immutable_cache(tmp_path: Path) -> None:
    storage, artifacts, request_model, _ = make_run(tmp_path)
    adapter = CountingAdapter()
    executor = CachedSourceExecutor(
        SourceOrchestrator([adapter], clock=lambda: NOW),
        storage,
        artifacts,
        clock=lambda: NOW,
    )
    policy = SourcePolicy.model_validate(
        {
            "rule_status": "allowed",
            "allowed_source_ids": [adapter.source_id],
            "source_order": [adapter.source_id],
            "allow_fallback": False,
            "offline_mode": False,
        }
    )
    request = JsonRpcSourceRequest(
        capability="chain_id",
        method="eth_chainId",
        params=[],
        block_tag="latest",
    )

    executions = []
    for _ in range(2):
        executions.append(
            asyncio.run(
                executor.execute(
                    analysis_id=request_model.root.analysis_id,
                    chain_id=1,
                    request=request,
                    policy=policy,
                )
            )
        )

    assert adapter.call_count == 2
    assert [item.attempts[0].attempt_number for item in executions] == [1, 2]
    assert storage.count("cache_entries") == 0
    storage.close()


def test_checkpoint_runner_skips_completed_stage_on_resume(tmp_path: Path) -> None:
    storage, _, request_model, _ = make_run(tmp_path)
    runner = CheckpointRunner(storage)
    call_count = 0

    async def operation() -> tuple[dict[str, object], tuple[str, ...]]:
        nonlocal call_count
        call_count += 1
        return {"next_block": 124}, ("EV-ONE",)

    first = asyncio.run(
        runner.run_once(
            analysis_id=request_model.root.analysis_id,
            stage="collect_receipt",
            operation=operation,
        )
    )
    second = asyncio.run(
        runner.run_once(
            analysis_id=request_model.root.analysis_id,
            stage="collect_receipt",
            operation=operation,
        )
    )

    assert first.resumed is False
    assert second.resumed is True
    assert first.checkpoint == second.checkpoint
    assert first.checkpoint.revision == 1
    assert call_count == 1
    assert storage.count("checkpoints") == 1
    storage.close()


@pytest.mark.parametrize("name", ("dex", "auth", "freeze"))
def test_confirmed_examples_persist_export_and_restore(
    tmp_path: Path,
    name: str,
) -> None:
    run_root = tmp_path / name
    storage, artifacts, _, result = make_run(run_root, name)

    storage.save_result(result, now=NOW)
    checkpoint = storage.save_checkpoint(
        result.root.analysis_id,
        "result_validated",
        {"status": result.root.status},
        (item.evidence_id for item in result.root.evidence),
        now=NOW,
    )
    bundle = ResultExporter(
        artifacts,
        storage,
        clock=lambda: NOW,
    ).export(result)
    repeated_bundle = ResultExporter(
        artifacts,
        storage,
        clock=lambda: NOW,
    ).export(result)

    json_body = artifacts.read(bundle.json_export.artifact)
    assert json.loads(json_body) == result.to_contract_dict()
    assert repeated_bundle.json_export.artifact.sha256 == bundle.json_export.artifact.sha256
    assert repeated_bundle.markdown_export.artifact.sha256 == bundle.markdown_export.artifact.sha256
    embedded_json = bundle.markdown_text.split("```json\n", 1)[1].split("\n```", 1)[0]
    assert json.loads(embedded_json) == result.to_contract_dict()
    for item in result.root.results:
        assert item.result_id in bundle.markdown_text
        assert (
            json.dumps(
                item.value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            in bundle.markdown_text
        )
    for evidence in result.root.evidence:
        assert evidence.evidence_id in bundle.markdown_text
    for source in result.root.sources:
        assert source.source_record_id in bundle.markdown_text

    assert storage.count("analysis_runs") == 1
    assert storage.count("results") == len(result.root.results)
    assert storage.count("evidence_records") == len(result.root.evidence)
    assert storage.count("source_records") == len(result.root.sources)
    assert storage.count("checkpoints") == 1
    assert storage.count("exports") == 2
    assert storage.integrity_check() == "ok"

    backup_path = tmp_path / f"{name}-backup.sqlite3"
    storage.backup_to(backup_path)
    with pytest.raises(FileExistsError):
        storage.backup_to(backup_path)
    storage.close()
    with SQLiteStorage(backup_path) as restored:
        assert restored.integrity_check() == "ok"
        assert restored.count("results") == len(result.root.results)
        assert restored.count("exports") == 2
        assert (
            restored.latest_checkpoint(
                result.root.analysis_id,
                "result_validated",
            )
            == checkpoint
        )


def test_secret_and_local_path_are_rejected_before_persistence(tmp_path: Path) -> None:
    canary = "SCAN_SECRET_CANARY"
    local_path = "/Users/example/private/input.json"
    guard = SensitiveDataGuard((canary, local_path))
    storage, artifacts, request, result = make_run(tmp_path, guard=guard)

    with pytest.raises(SensitiveDataError):
        artifacts.write(
            canary.encode(),
            media_type="text/plain",
            artifact_kind="raw_response",
        )
    with pytest.raises(SensitiveDataError):
        storage.save_checkpoint(
            request.root.analysis_id,
            "unsafe",
            {"path": local_path},
            (),
        )

    unsafe_document = copy.deepcopy(result.to_contract_dict())
    unsafe_document["warnings"] = [
        {
            "warning_id": "WARN-LOCAL-PATH",
            "code": "local_path",
            "message": local_path,
        }
    ]
    unsafe_result = validate_analysis_result(unsafe_document)
    storage.save_result(result, now=NOW)
    with pytest.raises(SensitiveDataError):
        ResultExporter(artifacts, storage, clock=lambda: NOW).export(unsafe_result)

    assert canary not in storage.path.read_bytes().decode(errors="ignore")
    assert local_path not in storage.path.read_bytes().decode(errors="ignore")
    storage.close()


def test_markdown_escapes_untrusted_evidence_text(tmp_path: Path) -> None:
    storage, artifacts, _, _ = make_run(tmp_path)
    document = load_document("dex", "result")
    document["evidence"][0]["method"] = "<script>alert(1)</script>|method"  # type: ignore[index]
    result = validate_analysis_result(document)
    storage.save_result(result, now=NOW)

    markdown = (
        ResultExporter(
            artifacts,
            storage,
            clock=lambda: NOW,
        )
        .export(result)
        .markdown_text
    )
    embedded_json = markdown.split("```json\n", 1)[1].split("\n```", 1)[0]

    assert "<script>" not in markdown
    assert "&lt;script&gt;" in markdown
    assert "\\|method" in markdown
    assert json.loads(embedded_json) == result.to_contract_dict()
    storage.close()


def test_cross_analysis_result_evidence_link_is_rejected_by_sqlite(tmp_path: Path) -> None:
    storage, _, _, result = make_run(tmp_path)
    storage.save_result(result, now=NOW)

    with pytest.raises(sqlite3.IntegrityError):
        storage.link_result_evidence(
            analysis_id="AN-OTHER-RUN",
            result_id=result.root.results[0].result_id,
            evidence_id=result.root.evidence[0].evidence_id,
            role="scoring",
            created_at=NOW,
        )
    storage.close()
