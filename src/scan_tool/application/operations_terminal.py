"""Plain-text OperationsSnapshot renderer for the local CLI."""

import json
from typing import TextIO

from scan_tool.application.operations_snapshot import OperationsSnapshot


def render_operations_snapshot(
    snapshot: OperationsSnapshot,
    stream: TextIO,
    *,
    output_format: str,
) -> None:
    if output_format == "json":
        stream.write(
            json.dumps(
                snapshot.to_contract_dict(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )
        stream.flush()
        return
    if output_format != "terminal":
        raise ValueError("output_format must be terminal or json")

    _render_header(snapshot, stream)
    _render_problems(snapshot, stream)
    _render_workers(snapshot, stream)
    _render_verifications(snapshot, stream)
    _render_submissions(snapshot, stream)
    _render_sources(snapshot, stream)
    _render_activity(snapshot, stream)
    stream.flush()


def _render_header(snapshot: OperationsSnapshot, stream: TextIO) -> None:
    mode = snapshot.ai_mode
    stream.write(
        f"OPERATIONS {snapshot.competition.competition_id} · "
        f"{snapshot.view_state.value.upper()} · snapshot {snapshot.snapshot_id}\n"
    )
    stream.write(
        "TIME       "
        f"elapsed {snapshot.competition.elapsed_seconds}s · "
        f"remaining {snapshot.competition.remaining_seconds}s · "
        f"stale_at {snapshot.stale_at.isoformat()}\n"
    )
    if mode is None:
        stream.write("AI MODE    unavailable\n")
    else:
        provider = mode.provider_id or "unresolved"
        model = mode.model_id or "unresolved"
        stream.write(
            f"AI MODE    {mode.rule_state.value} · {provider}/{model} · "
            f"{mode.data_boundary} · {mode.tool_mode}\n"
        )
    summary = snapshot.summary
    stream.write(
        "SUMMARY    "
        f"{summary.total} total · {summary.active} active · "
        f"{summary.verifying} verifying · {summary.ready} ready · "
        f"{summary.submitted} submitted · queue_age {summary.queue_age_seconds}s\n"
    )


def _render_problems(snapshot: OperationsSnapshot, stream: TextIO) -> None:
    stream.write("\nPROBLEMS\n")
    if not snapshot.problems:
        stream.write("EMPTY      Register a CTFd problem and confirm the Rules mode.\n")
    for problem in snapshot.problems:
        stream.write(
            f"{problem.problem_id:<14} {problem.status.value.upper():<18} "
            f"{problem.priority.value:<8} {problem.progress:<12} "
            f"owner={problem.owner} · next={problem.next_action}\n"
        )


def _render_workers(snapshot: OperationsSnapshot, stream: TextIO) -> None:
    stream.write("\nWORKERS\n")
    if not snapshot.workers:
        stream.write("EMPTY      No planner or evidence jobs are registered.\n")
    for worker in snapshot.workers:
        reason = "" if worker.queue_reason is None else f" · {worker.queue_reason}"
        stream.write(
            f"{worker.job_id:<22} {worker.role.value:<9} {worker.health.value:<8} "
            f"{worker.stage} · attempt {worker.attempt}/{worker.max_attempts}{reason}\n"
        )


def _render_verifications(snapshot: OperationsSnapshot, stream: TextIO) -> None:
    stream.write("\nVERIFICATION\n")
    if not snapshot.verifications:
        stream.write("EMPTY      No independently verified candidate exists.\n")
    for verification in snapshot.verifications:
        stream.write(
            f"{verification.verification_id:<20} {verification.status.value.upper():<10} "
            f"{verification.passed_checks}/{verification.required_checks} checks · "
            f"conflicts {len(verification.conflicts)} · "
            f"missing {len(verification.missing_evidence)}\n"
        )


def _render_submissions(snapshot: OperationsSnapshot, stream: TextIO) -> None:
    stream.write("\nSUBMISSION QUEUE\n")
    if not snapshot.submissions:
        stream.write("EMPTY      No evidence-backed candidate is available.\n")
    for submission in snapshot.submissions:
        stream.write(
            f"{submission.candidate_id:<20} {submission.human_state.value.upper():<15} "
            f"{submission.answer_format} · confidence {submission.confidence} · "
            f"evidence {submission.evidence_count}\n"
        )
        stream.write(f"ANSWER     {submission.answer_value}\n")


def _render_sources(snapshot: OperationsSnapshot, stream: TextIO) -> None:
    stream.write("\nSOURCES\n")
    if not snapshot.sources:
        stream.write("EMPTY      No live source health was supplied to this offline snapshot.\n")
    for source in snapshot.sources:
        stream.write(
            f"{source.capability:<18} {source.provider_id:<20} {source.health:<8} "
            f"{source.in_flight}/{source.concurrency_limit} in-flight · "
            f"cache {source.cache_status}\n"
        )


def _render_activity(snapshot: OperationsSnapshot, stream: TextIO) -> None:
    stream.write("\nACTIVITY\n")
    if not snapshot.activity:
        stream.write("EMPTY      No append-only activity event exists.\n")
    for event in snapshot.activity:
        problem = event.problem_id or "GLOBAL"
        stream.write(
            f"{event.created_at.isoformat()} {problem:<14} "
            f"{event.event_type} · {event.actor_type}:{event.actor_id}\n"
        )
