"""OPS-IMPL-04 bounded queue, dependency, isolation, and dedup tests."""

import asyncio
import hashlib
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

import pytest

from scan_tool.application.scheduler import (
    BoundedJobScheduler,
    InFlightRequestPool,
    QueueLimits,
    WorkerOutcome,
)
from scan_tool.domain.operations import JobRecord, JobRole, JobStatus, ProblemPriority

NOW = datetime(2026, 7, 28, 6, 0, tzinfo=UTC)


def _job(
    suffix: str,
    *,
    problem: str = "Q01",
    role: JobRole = JobRole.EVIDENCE,
    priority: ProblemPriority = ProblemPriority.NORMAL,
    idempotency_key: str | None = None,
    job_type: str | None = None,
    queued_offset: int = 0,
    max_attempts: int = 1,
) -> JobRecord:
    return JobRecord(
        job_id=f"JOB-{problem}-{suffix}",
        problem_id=f"PROB-{problem}",
        plan_id=f"PLAN-{problem}-ACTIVE",
        role=role,
        job_type=job_type or f"{role.value}_{suffix.lower().replace('-', '_')}",
        status=JobStatus.QUEUED,
        priority=priority,
        idempotency_key=idempotency_key
        or hashlib.sha256(f"{problem}:{role.value}:{suffix}".encode()).hexdigest(),
        attempt=0,
        max_attempts=max_attempts,
        queued_at=NOW + timedelta(seconds=queued_offset),
    )


def test_two_problems_overlap_and_worker_failure_is_isolated() -> None:
    active: set[str] = set()
    overlapped = asyncio.Event()
    release = asyncio.Event()

    async def execute(job: JobRecord, _: int) -> WorkerOutcome:
        active.add(job.problem_id)
        if len(active) == 2:
            overlapped.set()
        await overlapped.wait()
        if job.problem_id == "PROB-Q02":
            raise TimeoutError
        release.set()
        await release.wait()
        active.remove(job.problem_id)
        return WorkerOutcome(JobStatus.COMPLETE)

    scheduler = BoundedJobScheduler(execute)
    result = asyncio.run(scheduler.execute([_job("DEX"), _job("AUTH", problem="Q02")]))

    assert result.max_observed_active_problems == 2
    assert result.result_for("JOB-Q01-DEX").status is JobStatus.COMPLETE
    assert result.result_for("JOB-Q02-AUTH").status is JobStatus.FAILED
    assert result.result_for("JOB-Q02-AUTH").error_code == "worker_failed"


def test_independent_leaf_jobs_run_before_reconciliation_dependency() -> None:
    leaf_started = 0
    all_leaf_started = asyncio.Event()
    release_leaf = asyncio.Event()
    observed: list[str] = []
    jobs = [_job("RECEIPT"), _job("TRACE"), _job("STATE"), _job("RECON")]

    async def execute(job: JobRecord, _: int) -> WorkerOutcome:
        nonlocal leaf_started
        observed.append(job.job_id)
        if job.job_id != "JOB-Q01-RECON":
            leaf_started += 1
            if leaf_started == 3:
                all_leaf_started.set()
            await all_leaf_started.wait()
            release_leaf.set()
            await release_leaf.wait()
        else:
            assert leaf_started == 3
        return WorkerOutcome(JobStatus.COMPLETE)

    scheduler = BoundedJobScheduler(execute)
    result = asyncio.run(
        scheduler.execute(
            jobs,
            dependencies={
                "JOB-Q01-RECON": (
                    "JOB-Q01-RECEIPT",
                    "JOB-Q01-TRACE",
                    "JOB-Q01-STATE",
                )
            },
        )
    )

    assert result.dispatch_order[:3] == (
        "JOB-Q01-RECEIPT",
        "JOB-Q01-STATE",
        "JOB-Q01-TRACE",
    )
    assert result.dispatch_order[-1] == "JOB-Q01-RECON"
    assert all(item.status is JobStatus.COMPLETE for item in result.results)


def test_global_problem_role_and_per_problem_limits_are_observed() -> None:
    release = asyncio.Event()
    started = asyncio.Event()
    active = 0

    async def execute(_: JobRecord, __: int) -> WorkerOutcome:
        nonlocal active
        active += 1
        if active == 2:
            started.set()
        await started.wait()
        release.set()
        await release.wait()
        active -= 1
        return WorkerOutcome(JobStatus.COMPLETE)

    jobs = [
        _job("P1", role=JobRole.PLANNER),
        _job("P2", role=JobRole.PLANNER),
        _job("E1"),
        _job("E2", problem="Q02"),
        _job("E3", problem="Q03"),
    ]
    scheduler = BoundedJobScheduler(
        execute,
        limits=QueueLimits(
            max_active_problems=2,
            max_active_jobs=2,
            max_active_jobs_per_problem=1,
            max_planner_jobs=1,
            max_verifier_jobs=1,
        ),
    )
    result = asyncio.run(scheduler.execute(jobs))

    assert result.max_observed_active_jobs == 2
    assert result.max_observed_active_problems == 2
    assert result.max_observed_jobs_per_problem == 1
    assert dict(result.max_observed_jobs_by_role)[JobRole.PLANNER] == 1


def test_priority_then_queued_at_then_job_id_controls_dispatch() -> None:
    async def execute(_: JobRecord, __: int) -> WorkerOutcome:
        return WorkerOutcome(JobStatus.COMPLETE)

    jobs = [
        _job("LATE", priority=ProblemPriority.NORMAL, queued_offset=2),
        _job("HIGH-B", priority=ProblemPriority.HIGH, queued_offset=1),
        _job("HIGH-A", priority=ProblemPriority.HIGH, queued_offset=1),
    ]
    scheduler = BoundedJobScheduler(
        execute,
        limits=QueueLimits(
            max_active_problems=1,
            max_active_jobs=1,
            max_active_jobs_per_problem=1,
            max_planner_jobs=1,
            max_verifier_jobs=1,
        ),
    )
    result = asyncio.run(scheduler.execute(jobs))

    assert result.dispatch_order == (
        "JOB-Q01-HIGH-A",
        "JOB-Q01-HIGH-B",
        "JOB-Q01-LATE",
    )


def test_same_scope_idempotency_key_executes_once() -> None:
    calls = 0

    async def execute(_: JobRecord, __: int) -> WorkerOutcome:
        nonlocal calls
        calls += 1
        return WorkerOutcome(JobStatus.COMPLETE, checkpoint_ref="checkpoint://shared")

    shared_key = "a" * 64
    jobs = [
        _job("DUP-A", idempotency_key=shared_key, job_type="evidence_shared"),
        _job("DUP-B", idempotency_key=shared_key, job_type="evidence_shared"),
    ]
    result = asyncio.run(BoundedJobScheduler(execute).execute(jobs))

    assert calls == 1
    duplicate = result.result_for("JOB-Q01-DUP-B")
    assert duplicate.status is JobStatus.COMPLETE
    assert duplicate.attempts == 0
    assert duplicate.deduplicated_from_job_id == "JOB-Q01-DUP-A"
    assert duplicate.checkpoint_ref == "checkpoint://shared"


def test_inflight_source_request_is_shared_and_capability_is_bounded() -> None:
    calls = 0
    active = 0
    first_started = asyncio.Event()
    release = asyncio.Event()

    async def operation() -> bytes:
        nonlocal active, calls
        calls += 1
        active += 1
        first_started.set()
        await release.wait()
        active -= 1
        return b"shared raw response"

    async def scenario() -> tuple[bytes, bytes, Mapping[str, int]]:
        pool = InFlightRequestPool({"archive_state": 1})
        first = asyncio.create_task(
            pool.execute(
                capability="archive_state",
                request_key="cache-key-1",
                operation=operation,
            )
        )
        await first_started.wait()
        second = asyncio.create_task(
            pool.execute(
                capability="archive_state",
                request_key="cache-key-1",
                operation=operation,
            )
        )
        await asyncio.sleep(0)
        assert active == 1
        release.set()
        values = await asyncio.gather(first, second)
        return values[0], values[1], pool.max_observed_by_capability

    first_value, second_value, maxima = asyncio.run(scenario())

    assert calls == 1
    assert first_value == second_value == b"shared raw response"
    assert maxima["archive_state"] == 1


def test_capability_pool_rejects_unapproved_capability() -> None:
    async def operation() -> bytes:
        return b"unused"

    async def scenario() -> None:
        pool = InFlightRequestPool({"archive_state": 1})
        with pytest.raises(ValueError, match="no approved concurrency limit"):
            await pool.execute(
                capability="osint",
                request_key="cache-key-2",
                operation=operation,
            )

    asyncio.run(scenario())


def test_capability_pool_bounds_different_requests() -> None:
    calls = 0
    active = 0
    first_started = asyncio.Event()
    release_first = asyncio.Event()

    async def operation() -> int:
        nonlocal active, calls
        calls += 1
        active += 1
        if calls == 1:
            first_started.set()
            await release_first.wait()
        observed = active
        active -= 1
        return observed

    async def scenario() -> tuple[list[int], Mapping[str, int]]:
        pool = InFlightRequestPool({"archive_state": 1})
        first = asyncio.create_task(
            pool.execute(
                capability="archive_state",
                request_key="cache-key-a",
                operation=operation,
            )
        )
        await first_started.wait()
        second = asyncio.create_task(
            pool.execute(
                capability="archive_state",
                request_key="cache-key-b",
                operation=operation,
            )
        )
        await asyncio.sleep(0)
        assert calls == 1
        release_first.set()
        values = await asyncio.gather(first, second)
        return values, pool.max_observed_by_capability

    values, maxima = asyncio.run(scenario())

    assert calls == 2
    assert values == [1, 1]
    assert maxima["archive_state"] == 1


def test_idempotency_collision_across_problem_scope_is_rejected() -> None:
    async def execute(_: JobRecord, __: int) -> WorkerOutcome:
        return WorkerOutcome(JobStatus.COMPLETE)

    shared_key = "b" * 64
    scheduler = BoundedJobScheduler(execute)

    with pytest.raises(ValueError, match="different job scopes"):
        asyncio.run(
            scheduler.execute(
                [
                    _job("SAME", idempotency_key=shared_key),
                    _job("SAME", problem="Q02", idempotency_key=shared_key),
                ]
            )
        )


def test_deduplicated_jobs_require_equivalent_dependencies() -> None:
    async def execute(_: JobRecord, __: int) -> WorkerOutcome:
        return WorkerOutcome(JobStatus.COMPLETE)

    dependency = _job("BASE")
    shared_key = "c" * 64
    first = _job("DUP-A", idempotency_key=shared_key, job_type="evidence_shared")
    second = _job("DUP-B", idempotency_key=shared_key, job_type="evidence_shared")

    with pytest.raises(ValueError, match="equivalent dependencies"):
        asyncio.run(
            BoundedJobScheduler(execute).execute(
                [dependency, first, second],
                dependencies={second.job_id: (dependency.job_id,)},
            )
        )


@pytest.mark.parametrize("kind", ["unknown", "cross_problem", "cycle"])
def test_invalid_dependency_graph_is_rejected(kind: str) -> None:
    async def execute(_: JobRecord, __: int) -> WorkerOutcome:
        return WorkerOutcome(JobStatus.COMPLETE)

    first = _job("FIRST")
    second = _job("SECOND")
    other = _job("OTHER", problem="Q02")
    jobs = [first, second, other]
    if kind == "unknown":
        dependencies = {second.job_id: ("JOB-Q01-MISSING",)}
        match = "unknown job"
    elif kind == "cross_problem":
        dependencies = {second.job_id: (other.job_id,)}
        match = "cross-problem"
    else:
        dependencies = {
            first.job_id: (second.job_id,),
            second.job_id: (first.job_id,),
        }
        match = "cycle"

    with pytest.raises(ValueError, match=match):
        asyncio.run(BoundedJobScheduler(execute).execute(jobs, dependencies=dependencies))


def test_failed_dependency_keeps_reconciliation_waiting() -> None:
    async def execute(job: JobRecord, _: int) -> WorkerOutcome:
        if job.job_id == "JOB-Q01-STATE":
            return WorkerOutcome(JobStatus.FAILED, error_code="archive_unavailable")
        return WorkerOutcome(JobStatus.COMPLETE)

    result = asyncio.run(
        BoundedJobScheduler(execute).execute(
            [_job("STATE"), _job("RECON")],
            dependencies={"JOB-Q01-RECON": ("JOB-Q01-STATE",)},
        )
    )

    assert result.result_for("JOB-Q01-STATE").status is JobStatus.FAILED
    blocked = result.result_for("JOB-Q01-RECON")
    assert blocked.status is JobStatus.WAITING
    assert blocked.error_code == "dependency_incomplete"
    assert blocked.attempts == 0


def test_partial_dependency_keeps_reconciliation_waiting() -> None:
    async def execute(job: JobRecord, _: int) -> WorkerOutcome:
        if job.job_id == "JOB-Q01-TRACE":
            return WorkerOutcome(
                JobStatus.PARTIAL,
                error_code="trace_incomplete",
                checkpoint_ref="checkpoint://trace-partial",
            )
        return WorkerOutcome(JobStatus.COMPLETE)

    result = asyncio.run(
        BoundedJobScheduler(execute).execute(
            [_job("TRACE"), _job("RECON")],
            dependencies={"JOB-Q01-RECON": ("JOB-Q01-TRACE",)},
        )
    )

    partial = result.result_for("JOB-Q01-TRACE")
    assert partial.status is JobStatus.PARTIAL
    assert partial.checkpoint_ref == "checkpoint://trace-partial"
    blocked = result.result_for("JOB-Q01-RECON")
    assert blocked.status is JobStatus.WAITING
    assert blocked.error_code == "dependency_incomplete"
    assert blocked.attempts == 0


def test_retryable_failure_is_bounded_by_job_max_attempts() -> None:
    attempts: list[int] = []

    async def execute(_: JobRecord, attempt: int) -> WorkerOutcome:
        attempts.append(attempt)
        if attempt == 1:
            return WorkerOutcome(
                JobStatus.FAILED,
                error_code="temporary_failure",
                retryable=True,
            )
        return WorkerOutcome(JobStatus.COMPLETE)

    job = _job("RETRY", max_attempts=2)
    result = asyncio.run(BoundedJobScheduler(execute).execute([job]))

    assert attempts == [1, 2]
    assert result.result_for(job.job_id).status is JobStatus.COMPLETE
    assert result.result_for(job.job_id).attempts == 2


def test_retryable_failure_stays_failed_after_max_attempts() -> None:
    attempts: list[int] = []

    async def execute(_: JobRecord, attempt: int) -> WorkerOutcome:
        attempts.append(attempt)
        return WorkerOutcome(
            JobStatus.FAILED,
            error_code="temporary_failure",
            checkpoint_ref=f"checkpoint://attempt-{attempt}",
            retryable=True,
        )

    job = _job("EXHAUST", max_attempts=2)
    result = asyncio.run(BoundedJobScheduler(execute).execute([job]))

    assert attempts == [1, 2]
    exhausted = result.result_for(job.job_id)
    assert exhausted.status is JobStatus.FAILED
    assert exhausted.attempts == 2
    assert exhausted.error_code == "temporary_failure"
    assert exhausted.checkpoint_ref == "checkpoint://attempt-2"


def test_paused_and_cancelled_jobs_are_not_dispatched() -> None:
    calls = 0

    async def execute(_: JobRecord, __: int) -> WorkerOutcome:
        nonlocal calls
        calls += 1
        return WorkerOutcome(JobStatus.COMPLETE)

    paused = _job("PAUSED")
    cancelled = _job("CANCELLED", problem="Q02")
    result = asyncio.run(
        BoundedJobScheduler(execute).execute(
            [paused, cancelled],
            paused_problem_ids=frozenset({paused.problem_id}),
            cancelled_job_ids=frozenset({cancelled.job_id}),
        )
    )

    assert calls == 0
    assert result.result_for(paused.job_id).status is JobStatus.WAITING
    assert result.result_for(cancelled.job_id).status is JobStatus.CANCELLED


def test_non_queued_job_and_concurrent_scheduler_reuse_are_rejected() -> None:
    release = asyncio.Event()

    async def execute(_: JobRecord, __: int) -> WorkerOutcome:
        await release.wait()
        return WorkerOutcome(JobStatus.COMPLETE)

    async def scenario() -> None:
        scheduler = BoundedJobScheduler(execute)
        first = asyncio.create_task(scheduler.execute([_job("FIRST")]))
        await asyncio.sleep(0)
        with pytest.raises(RuntimeError, match="cannot execute two queues"):
            await scheduler.execute([_job("SECOND")])
        release.set()
        await first

    asyncio.run(scenario())

    invalid = _job("DONE").model_copy(update={"status": JobStatus.COMPLETE, "finished_at": NOW})
    with pytest.raises(ValueError, match="only queued"):
        asyncio.run(BoundedJobScheduler(execute).execute([invalid]))
