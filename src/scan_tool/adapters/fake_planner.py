"""Deterministic synthetic-only planner used by offline QA."""

import hashlib
import json

from scan_tool.domain.operations import (
    AdapterKind,
    DataBoundary,
    JobRole,
    LeafJobSpec,
    PlanHypothesis,
    PlanStatus,
)
from scan_tool.domain.planning import (
    PlannerAdapterResponse,
    PlannerContext,
    PlannerUsage,
)


class DeterministicFakePlanner:
    """Create repeatable method and leaf hypotheses without external I/O."""

    adapter_kind = AdapterKind.FAKE_QA
    provider_id = "fake.qa"
    model_id = "deterministic-planner-0.1"

    async def plan(self, context: PlannerContext) -> PlannerAdapterResponse:
        if context.data_boundary is not DataBoundary.SYNTHETIC_ONLY:
            raise ValueError("fake QA planner accepts synthetic_only data")

        leaf_job_specs: list[LeafJobSpec] = []
        for index, capability in enumerate(context.available_capabilities):
            dependency = [] if not leaf_job_specs else [leaf_job_specs[-1].leaf_job_id]
            leaf_job_specs.append(
                LeafJobSpec(
                    leaf_job_id=_leaf_job_id(context.plan_id, index, capability),
                    role=JobRole.EVIDENCE,
                    purpose=f"Collect deterministic evidence with {capability}.",
                    analysis_type=context.analysis_type,
                    inputs_projection=context.problem_view,
                    depends_on=dependency,
                    required_capabilities=[capability],
                    expected_output=f"Evidence-backed {capability} result.",
                )
            )
        raw_payload = {
            "problem_type_hypothesis": _problem_type(context),
            "method_hypothesis": (
                "Run the approved Python evidence capabilities and verify their outputs."
            ),
            "assumptions": ["Synthetic QA input only."],
            "missing_inputs": [],
            "leaf_job_specs": [item.model_dump(mode="json") for item in leaf_job_specs],
        }
        raw_output = json.dumps(
            raw_payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        sha256 = hashlib.sha256(raw_output).hexdigest()
        plan = PlanHypothesis(
            plan_id=context.plan_id,
            problem_id=context.problem_id,
            mode_id=context.mode_id,
            planner_job_id=context.planner_job_id,
            status=PlanStatus.PROPOSED,
            problem_type_hypothesis=raw_payload["problem_type_hypothesis"],
            method_hypothesis=raw_payload["method_hypothesis"],
            assumptions=raw_payload["assumptions"],
            missing_inputs=raw_payload["missing_inputs"],
            leaf_job_specs=leaf_job_specs,
            raw_output_artifact=f"artifact://sha256/{sha256}",
            created_at=context.created_at,
        )
        return PlannerAdapterResponse(
            plan=plan,
            raw_output=raw_output,
            usage=PlannerUsage(
                input_tokens=max(1, len(json.dumps(context.problem_view)) // 4),
                output_tokens=max(1, len(raw_output) // 4),
                cost_microunits=0,
            ),
        )


def _problem_type(context: PlannerContext) -> str:
    hinted = context.problem_view.get("problem_type_hint")
    return hinted if isinstance(hinted, str) and hinted else "synthetic_chain_analysis"


def _leaf_job_id(plan_id: str, index: int, capability: str) -> str:
    digest = hashlib.sha256(f"{plan_id}:{index}:{capability}".encode()).hexdigest()
    return f"JOB-FAKE-{digest[:12].upper()}"
