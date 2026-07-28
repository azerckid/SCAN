"""Internal planner boundary models for OPS-IMPL-03."""

from dataclasses import dataclass

from pydantic import Field

from scan_tool.domain._types import (
    ContractModel,
    JsonObject,
    NonEmptyUniqueList,
    NonNegativeInt,
    SnakeName,
)
from scan_tool.domain.analysis_request import AnalysisType
from scan_tool.domain.operations import (
    DataBoundary,
    JobId,
    ModeId,
    PlanHypothesis,
    PlanId,
    ProblemId,
    SafeJsonObject,
    UtcDatetime,
)


class PlannerContext(ContractModel):
    """Validated, boundary-labeled projection passed to a planner adapter."""

    plan_id: PlanId
    mode_id: ModeId
    problem_id: ProblemId
    planner_job_id: JobId
    analysis_type: AnalysisType
    data_boundary: DataBoundary
    problem_view: SafeJsonObject
    available_capabilities: NonEmptyUniqueList[SnakeName]
    prior_safe_context: SafeJsonObject
    created_at: UtcDatetime


@dataclass(frozen=True, slots=True)
class PlannerUsage:
    input_tokens: int
    output_tokens: int
    cost_microunits: int

    def __post_init__(self) -> None:
        if min(self.input_tokens, self.output_tokens, self.cost_microunits) < 0:
            raise ValueError("planner usage values must not be negative")

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True, slots=True)
class PlannerAdapterResponse:
    plan: PlanHypothesis
    raw_output: bytes
    usage: PlannerUsage

    def __post_init__(self) -> None:
        if not self.raw_output:
            raise ValueError("planner raw output must not be empty")


class PlannerBudgets(ContractModel):
    timeout_seconds: float = Field(gt=0, le=300)
    token_budget: NonNegativeInt
    cost_budget_microunits: NonNegativeInt


class _SafePlannerDetails(ContractModel):
    details: SafeJsonObject


def safe_planner_details(value: JsonObject) -> SafeJsonObject:
    """Validate safe event/error details without exporting a new public schema."""

    return _SafePlannerDetails(details=value).details
