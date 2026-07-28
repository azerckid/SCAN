"""Bounded in-process job scheduler for OPS-IMPL-04."""

import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import cast

from scan_tool.domain.operations import JobRecord, JobRole, JobStatus, ProblemPriority

type JobExecutor = Callable[[JobRecord, int], Awaitable["WorkerOutcome"]]
type Clock = Callable[[], datetime]
type SourceOperation[T] = Callable[[], Awaitable[T]]

_PRIORITY_ORDER = {
    ProblemPriority.CRITICAL: 0,
    ProblemPriority.HIGH: 1,
    ProblemPriority.NORMAL: 2,
    ProblemPriority.DEFERRED: 3,
}
_TERMINAL_WORKER_STATUSES = {
    JobStatus.COMPLETE,
    JobStatus.PARTIAL,
    JobStatus.FAILED,
    JobStatus.CANCELLED,
}


@dataclass(frozen=True, slots=True)
class QueueLimits:
    max_active_problems: int = 4
    max_active_jobs: int = 6
    max_active_jobs_per_problem: int = 3
    max_planner_jobs: int = 1
    max_verifier_jobs: int = 2

    def __post_init__(self) -> None:
        values = (
            self.max_active_problems,
            self.max_active_jobs,
            self.max_active_jobs_per_problem,
            self.max_planner_jobs,
            self.max_verifier_jobs,
        )
        if any(value < 1 for value in values):
            raise ValueError("queue limits must be positive")

    def role_limit(self, role: JobRole) -> int:
        if role is JobRole.PLANNER:
            return self.max_planner_jobs
        if role is JobRole.VERIFIER:
            return self.max_verifier_jobs
        return self.max_active_jobs


class InFlightRequestPool:
    """Deduplicate identical in-flight reads and bound each source capability."""

    def __init__(self, capability_limits: Mapping[str, int]) -> None:
        if not capability_limits or any(limit < 1 for limit in capability_limits.values()):
            raise ValueError("capability limits must contain positive values")
        self._semaphores = {
            capability: asyncio.Semaphore(limit) for capability, limit in capability_limits.items()
        }
        self._inflight: dict[tuple[str, str], asyncio.Task[object]] = {}
        self._lock = asyncio.Lock()
        self._active_by_capability = dict.fromkeys(capability_limits, 0)
        self._max_observed_by_capability = dict.fromkeys(capability_limits, 0)

    @property
    def max_observed_by_capability(self) -> Mapping[str, int]:
        return dict(self._max_observed_by_capability)

    async def execute[T](
        self,
        *,
        capability: str,
        request_key: str,
        operation: SourceOperation[T],
    ) -> T:
        semaphore = self._semaphores.get(capability)
        if semaphore is None:
            raise ValueError("source capability has no approved concurrency limit")
        if not request_key:
            raise ValueError("request_key must not be empty")
        key = (capability, request_key)
        async with self._lock:
            task = self._inflight.get(key)
            if task is None:
                task = asyncio.create_task(self._run_source(capability, semaphore, operation))
                self._inflight[key] = task
                task.add_done_callback(
                    lambda completed, request_key=key: asyncio.create_task(
                        self._forget(request_key, completed)
                    )
                )
        return cast(T, await asyncio.shield(task))

    async def _run_source[T](
        self,
        capability: str,
        semaphore: asyncio.Semaphore,
        operation: SourceOperation[T],
    ) -> T:
        async with semaphore:
            self._active_by_capability[capability] += 1
            self._max_observed_by_capability[capability] = max(
                self._max_observed_by_capability[capability],
                self._active_by_capability[capability],
            )
            try:
                return await operation()
            finally:
                self._active_by_capability[capability] -= 1

    async def _forget(
        self,
        key: tuple[str, str],
        task: asyncio.Task[object],
    ) -> None:
        if not task.cancelled():
            task.exception()
        async with self._lock:
            if self._inflight.get(key) is task:
                del self._inflight[key]


@dataclass(frozen=True, slots=True)
class WorkerOutcome:
    status: JobStatus
    error_code: str | None = None
    checkpoint_ref: str | None = None
    retryable: bool = False

    def __post_init__(self) -> None:
        if self.status not in _TERMINAL_WORKER_STATUSES:
            raise ValueError("worker outcome must be terminal")
        if self.retryable and self.status is not JobStatus.FAILED:
            raise ValueError("only a failed worker outcome can be retryable")


@dataclass(frozen=True, slots=True)
class ScheduledJobResult:
    job_id: str
    problem_id: str
    status: JobStatus
    attempts: int
    started_at: datetime | None
    finished_at: datetime | None
    error_code: str | None = None
    checkpoint_ref: str | None = None
    deduplicated_from_job_id: str | None = None


@dataclass(frozen=True, slots=True)
class SchedulerExecution:
    results: tuple[ScheduledJobResult, ...]
    dispatch_order: tuple[str, ...]
    max_observed_active_jobs: int
    max_observed_active_problems: int
    max_observed_jobs_per_problem: int
    max_observed_jobs_by_role: tuple[tuple[JobRole, int], ...]

    def result_for(self, job_id: str) -> ScheduledJobResult:
        for result in self.results:
            if result.job_id == job_id:
                return result
        raise KeyError(job_id)


@dataclass(slots=True)
class _ActiveCounters:
    total: int = 0
    by_problem: dict[str, int] = field(default_factory=dict)
    by_role: dict[JobRole, int] = field(default_factory=dict)


class BoundedJobScheduler:
    """Execute a validated job DAG with deterministic bounded dispatch."""

    def __init__(
        self,
        executor: JobExecutor,
        *,
        limits: QueueLimits | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._executor = executor
        self._limits = limits or QueueLimits()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._is_running = False

    async def execute(
        self,
        jobs: Sequence[JobRecord],
        *,
        dependencies: Mapping[str, Sequence[str]] | None = None,
        paused_problem_ids: frozenset[str] = frozenset(),
        cancelled_job_ids: frozenset[str] = frozenset(),
    ) -> SchedulerExecution:
        if self._is_running:
            raise RuntimeError("one scheduler instance cannot execute two queues concurrently")
        self._is_running = True
        try:
            return await self._execute(
                jobs,
                dependencies=dependencies or {},
                paused_problem_ids=paused_problem_ids,
                cancelled_job_ids=cancelled_job_ids,
            )
        finally:
            self._is_running = False

    async def _execute(
        self,
        jobs: Sequence[JobRecord],
        *,
        dependencies: Mapping[str, Sequence[str]],
        paused_problem_ids: frozenset[str],
        cancelled_job_ids: frozenset[str],
    ) -> SchedulerExecution:
        jobs_by_id = self._validate_jobs(jobs)
        dependency_map = self._validate_dependencies(jobs_by_id, dependencies)
        canonical_by_job = self._deduplication_map(jobs)
        canonical_jobs = {
            job_id: job for job_id, job in jobs_by_id.items() if canonical_by_job[job_id] == job_id
        }
        canonical_dependencies = {
            job_id: tuple(canonical_by_job[item] for item in dependency_map[job_id])
            for job_id in canonical_jobs
        }
        for job in jobs:
            canonical_id = canonical_by_job[job.job_id]
            if canonical_id == job.job_id:
                continue
            duplicate_dependencies = tuple(
                canonical_by_job[item] for item in dependency_map[job.job_id]
            )
            if set(duplicate_dependencies) != set(canonical_dependencies[canonical_id]):
                raise ValueError("deduplicated jobs must have equivalent dependencies")
        self._require_acyclic(canonical_dependencies)

        pending = set(canonical_jobs)
        results: dict[str, ScheduledJobResult] = {}
        attempts: dict[str, int] = {job_id: 0 for job_id in canonical_jobs}
        started_times: dict[str, datetime] = {}
        active: dict[asyncio.Task[WorkerOutcome], JobRecord] = {}
        counters = _ActiveCounters()
        dispatch_order: list[str] = []
        maxima = {"jobs": 0, "problems": 0, "per_problem": 0}
        role_maxima: dict[JobRole, int] = {}

        for job_id in tuple(pending):
            job = canonical_jobs[job_id]
            if job_id in cancelled_job_ids:
                results[job_id] = self._not_run(job, JobStatus.CANCELLED, "cancelled")
                pending.remove(job_id)
            elif job.problem_id in paused_problem_ids:
                results[job_id] = self._not_run(job, JobStatus.WAITING, "problem_paused")
                pending.remove(job_id)

        while pending or active:
            self._resolve_blocked_dependencies(
                pending,
                results,
                canonical_jobs,
                canonical_dependencies,
            )
            for job in self._ready_jobs(
                pending,
                results,
                canonical_jobs,
                canonical_dependencies,
            ):
                if not self._has_capacity(job, counters):
                    continue
                pending.remove(job.job_id)
                attempts[job.job_id] += 1
                started_times.setdefault(job.job_id, self._clock())
                dispatch_order.append(job.job_id)
                self._increment(job, counters)
                task = asyncio.create_task(self._run_worker(job, attempts[job.job_id]))
                active[task] = job
                maxima["jobs"] = max(maxima["jobs"], counters.total)
                maxima["problems"] = max(
                    maxima["problems"],
                    sum(1 for count in counters.by_problem.values() if count),
                )
                maxima["per_problem"] = max(
                    maxima["per_problem"],
                    counters.by_problem[job.problem_id],
                )
                role_maxima[job.role] = max(
                    role_maxima.get(job.role, 0),
                    counters.by_role[job.role],
                )

            if not active:
                for job_id in tuple(pending):
                    results[job_id] = self._not_run(
                        canonical_jobs[job_id],
                        JobStatus.WAITING,
                        "dependency_incomplete",
                    )
                    pending.remove(job_id)
                break

            completed, _ = await asyncio.wait(active, return_when=asyncio.FIRST_COMPLETED)
            for task in sorted(completed, key=lambda item: active[item].job_id):
                job = active.pop(task)
                self._decrement(job, counters)
                outcome = task.result()
                if (
                    outcome.status is JobStatus.FAILED
                    and outcome.retryable
                    and attempts[job.job_id] < job.max_attempts
                ):
                    pending.add(job.job_id)
                    continue
                results[job.job_id] = ScheduledJobResult(
                    job_id=job.job_id,
                    problem_id=job.problem_id,
                    status=outcome.status,
                    attempts=attempts[job.job_id],
                    started_at=started_times[job.job_id],
                    finished_at=self._clock(),
                    error_code=outcome.error_code,
                    checkpoint_ref=outcome.checkpoint_ref or _optional_text(job.checkpoint_ref),
                )

        for job in jobs:
            canonical_id = canonical_by_job[job.job_id]
            if canonical_id == job.job_id:
                continue
            canonical = results[canonical_id]
            results[job.job_id] = ScheduledJobResult(
                job_id=job.job_id,
                problem_id=job.problem_id,
                status=canonical.status,
                attempts=0,
                started_at=None,
                finished_at=canonical.finished_at,
                error_code=canonical.error_code,
                checkpoint_ref=canonical.checkpoint_ref,
                deduplicated_from_job_id=canonical_id,
            )

        return SchedulerExecution(
            results=tuple(results[job.job_id] for job in jobs),
            dispatch_order=tuple(dispatch_order),
            max_observed_active_jobs=maxima["jobs"],
            max_observed_active_problems=maxima["problems"],
            max_observed_jobs_per_problem=maxima["per_problem"],
            max_observed_jobs_by_role=tuple(sorted(role_maxima.items(), key=lambda item: item[0])),
        )

    async def _run_worker(self, job: JobRecord, attempt: int) -> WorkerOutcome:
        try:
            return await self._executor(job, attempt)
        except asyncio.CancelledError:
            return WorkerOutcome(status=JobStatus.CANCELLED, error_code="cancelled")
        except Exception:
            return WorkerOutcome(status=JobStatus.FAILED, error_code="worker_failed")

    def _validate_jobs(self, jobs: Sequence[JobRecord]) -> dict[str, JobRecord]:
        jobs_by_id = {job.job_id: job for job in jobs}
        if len(jobs_by_id) != len(jobs):
            raise ValueError("job_id values must be unique")
        if any(job.status is not JobStatus.QUEUED for job in jobs):
            raise ValueError("scheduler accepts only queued jobs")
        return jobs_by_id

    def _validate_dependencies(
        self,
        jobs_by_id: Mapping[str, JobRecord],
        dependencies: Mapping[str, Sequence[str]],
    ) -> dict[str, tuple[str, ...]]:
        unknown_jobs = set(dependencies) - jobs_by_id.keys()
        if unknown_jobs:
            raise ValueError("dependency map contains an unknown job")
        normalized: dict[str, tuple[str, ...]] = {}
        for job_id, job in jobs_by_id.items():
            items = tuple(dependencies.get(job_id, ()))
            if len(items) != len(set(items)):
                raise ValueError("job dependency values must be unique")
            for dependency_id in items:
                dependency = jobs_by_id.get(dependency_id)
                if dependency is None:
                    raise ValueError("job dependency references an unknown job")
                if dependency.problem_id != job.problem_id:
                    raise ValueError("cross-problem job dependency is forbidden")
                if dependency_id == job_id:
                    raise ValueError("job cannot depend on itself")
            normalized[job_id] = items
        self._require_acyclic(normalized)
        return normalized

    def _require_acyclic(self, dependencies: Mapping[str, Sequence[str]]) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(job_id: str) -> None:
            if job_id in visiting:
                raise ValueError("job dependency cycle")
            if job_id in visited:
                return
            visiting.add(job_id)
            for dependency_id in dependencies[job_id]:
                visit(dependency_id)
            visiting.remove(job_id)
            visited.add(job_id)

        for job_id in dependencies:
            visit(job_id)

    def _deduplication_map(self, jobs: Sequence[JobRecord]) -> dict[str, str]:
        canonical_by_key: dict[str, JobRecord] = {}
        result: dict[str, str] = {}
        for job in sorted(jobs, key=self._sort_key):
            canonical = canonical_by_key.get(job.idempotency_key)
            if canonical is None:
                canonical_by_key[job.idempotency_key] = job
                canonical = job
            elif (
                canonical.problem_id != job.problem_id
                or canonical.job_type != job.job_type
                or canonical.role is not job.role
            ):
                raise ValueError("idempotency key collides across different job scopes")
            result[job.job_id] = canonical.job_id
        return result

    def _ready_jobs(
        self,
        pending: set[str],
        results: Mapping[str, ScheduledJobResult],
        jobs: Mapping[str, JobRecord],
        dependencies: Mapping[str, Sequence[str]],
    ) -> list[JobRecord]:
        ready = [
            jobs[job_id]
            for job_id in pending
            if all(
                dependency_id in results and results[dependency_id].status is JobStatus.COMPLETE
                for dependency_id in dependencies[job_id]
            )
        ]
        return sorted(ready, key=self._sort_key)

    def _resolve_blocked_dependencies(
        self,
        pending: set[str],
        results: dict[str, ScheduledJobResult],
        jobs: Mapping[str, JobRecord],
        dependencies: Mapping[str, Sequence[str]],
    ) -> None:
        blocking_statuses = {
            JobStatus.WAITING,
            JobStatus.PARTIAL,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        }
        for job_id in tuple(pending):
            if any(
                dependency_id in results and results[dependency_id].status in blocking_statuses
                for dependency_id in dependencies[job_id]
            ):
                results[job_id] = self._not_run(
                    jobs[job_id],
                    JobStatus.WAITING,
                    "dependency_incomplete",
                )
                pending.remove(job_id)

    def _has_capacity(self, job: JobRecord, counters: _ActiveCounters) -> bool:
        active_problems = sum(1 for count in counters.by_problem.values() if count)
        is_active_problem = counters.by_problem.get(job.problem_id, 0) > 0
        return (
            counters.total < self._limits.max_active_jobs
            and counters.by_problem.get(job.problem_id, 0)
            < self._limits.max_active_jobs_per_problem
            and counters.by_role.get(job.role, 0) < self._limits.role_limit(job.role)
            and (is_active_problem or active_problems < self._limits.max_active_problems)
        )

    def _increment(self, job: JobRecord, counters: _ActiveCounters) -> None:
        counters.total += 1
        counters.by_problem[job.problem_id] = counters.by_problem.get(job.problem_id, 0) + 1
        counters.by_role[job.role] = counters.by_role.get(job.role, 0) + 1

    def _decrement(self, job: JobRecord, counters: _ActiveCounters) -> None:
        counters.total -= 1
        counters.by_problem[job.problem_id] -= 1
        counters.by_role[job.role] -= 1

    def _sort_key(self, job: JobRecord) -> tuple[int, datetime, str]:
        return (_PRIORITY_ORDER[job.priority], job.queued_at, job.job_id)

    def _not_run(
        self,
        job: JobRecord,
        status: JobStatus,
        error_code: str,
    ) -> ScheduledJobResult:
        return ScheduledJobResult(
            job_id=job.job_id,
            problem_id=job.problem_id,
            status=status,
            attempts=0,
            started_at=None,
            finished_at=None,
            error_code=error_code,
            checkpoint_ref=_optional_text(job.checkpoint_ref),
        )


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) else None
