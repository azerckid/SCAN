"""Offline benchmark for the 30 approved expected-problem scenarios."""

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from time import perf_counter
from typing import Annotated

from pydantic import Field, JsonValue, model_validator

from scan_tool.domain import validate_analysis_request
from scan_tool.domain._types import ContractModel
from scan_tool.domain.analysis_request import (
    AnalysisRequest,
    AuthAnalysisRequest,
    BitcoinUtxoAnalysisRequest,
    BridgeTransferAnalysisRequest,
    CexClusterAnalysisRequest,
    DexAnalysisRequest,
    EvmCoreAnalysisRequest,
    EvmSpecialAnalysisRequest,
    FlowPathAnalysisRequest,
    FreezeAnalysisRequest,
    IntelContextAnalysisRequest,
    MixerFlowAnalysisRequest,
)
from scan_tool.domain.analysis_result import AnalysisResult, AnalysisStatus
from scan_tool.slices.auth import analyze_auth_replay
from scan_tool.slices.bitcoin_utxo import analyze_bitcoin_utxo_replay
from scan_tool.slices.bridge_transfer import analyze_bridge_transfer_replay
from scan_tool.slices.cex_cluster import analyze_cex_cluster_replay
from scan_tool.slices.dex import analyze_dex_replay
from scan_tool.slices.evm_core import analyze_evm_core_replay
from scan_tool.slices.evm_special import analyze_evm_special_replay
from scan_tool.slices.flow_path import analyze_flow_path_replay
from scan_tool.slices.freeze import analyze_freeze_replay
from scan_tool.slices.intel_context import analyze_intel_context_replay
from scan_tool.slices.mixer_flow import analyze_mixer_flow_replay

APPROVED_EXPECTED_PROBLEM_IDS = frozenset(
    {
        "ACTOR-REL-001",
        "ACTOR-REL-002",
        "BASIC-EVM-001",
        "BASIC-EVM-002",
        "BTC-UTXO-001",
        "BTC-CJ-001",
        "BTC-UTXO-002",
        "CRIME-EXP-001",
        "CRIME-PHISH-001",
        "CRIME-POISON-001",
        "CRIME-RUG-001",
        "EVM-AUTH-001",
        "EVM-FREEZE-001",
        "EVM-NFT-001",
        "EVM-PROXY-001",
        "EVM-TOKEN-001",
        "EVM-TOKEN-002",
        "FLOW-EVM-001",
        "FLOW-EVM-002",
        "FLOW-MULTI-001",
        "MIXED-CASE-001",
        "MIXED-XCHAIN-001",
        "OSINT-ENS-001",
        "OSINT-LBL-001",
        "OSINT-SAN-001",
        "SVC-BRG-001",
        "SVC-CEX-001",
        "SVC-DEX-001",
        "SVC-LEND-001",
        "SVC-MIX-001",
    }
)
APPROVED_AUTOMATED_PROBLEM_IDS = frozenset(
    {
        "BASIC-EVM-001",
        "BASIC-EVM-002",
        "BTC-UTXO-001",
        "EVM-AUTH-001",
        "EVM-FREEZE-001",
        "EVM-NFT-001",
        "EVM-PROXY-001",
        "EVM-TOKEN-001",
        "EVM-TOKEN-002",
        "FLOW-EVM-001",
        "FLOW-EVM-002",
        "OSINT-LBL-001",
        "SVC-BRG-001",
        "SVC-CEX-001",
        "SVC-DEX-001",
        "SVC-MIX-001",
    }
)


class CoverageLevel(StrEnum):
    AUTOMATED = "automated"
    ASSISTED = "assisted"
    UNSUPPORTED = "unsupported"


class Difficulty(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ExpectedBenchmarkResult(ContractModel):
    result_type: Annotated[str, Field(min_length=1, max_length=100)]
    value: dict[str, JsonValue]


class ExecutableFixture(ContractModel):
    fixture_id: Annotated[str, Field(pattern=r"^FX-[A-Z0-9-]+$")]
    request_path: Annotated[str, Field(min_length=1)]
    replay_path: Annotated[str, Field(min_length=1)]
    expected_results: list[ExpectedBenchmarkResult]
    required_fixture_requirements: list[Annotated[str, Field(pattern=r"^REQ-[A-Z0-9-]+$")]]

    @model_validator(mode="after")
    def has_scoring_oracle(self) -> "ExecutableFixture":
        result_types = [item.result_type for item in self.expected_results]
        if not result_types or len(result_types) != len(set(result_types)):
            raise ValueError("automated fixture requires unique expected result types")
        if not self.required_fixture_requirements:
            raise ValueError("automated fixture requires scoring requirements")
        return self


class ExpectedProblemCase(ContractModel):
    problem_id: Annotated[str, Field(pattern=r"^[A-Z]+(?:-[A-Z0-9]+)+-\d{3}$")]
    difficulty: Difficulty
    coverage: CoverageLevel
    reason: Annotated[str, Field(min_length=1, max_length=500)]
    reusable_capabilities: list[Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9-]+$")]]
    blocking_gaps: list[Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9-]+$")]]
    fixture: ExecutableFixture | None = None

    @model_validator(mode="after")
    def fixture_matches_coverage(self) -> "ExpectedProblemCase":
        if self.coverage is CoverageLevel.AUTOMATED and self.fixture is None:
            raise ValueError("automated case requires an executable fixture")
        if self.coverage is not CoverageLevel.AUTOMATED and self.fixture is not None:
            raise ValueError("only automated cases may define an executable fixture")
        if self.coverage is CoverageLevel.AUTOMATED and self.blocking_gaps:
            raise ValueError("automated case cannot contain blocking gaps")
        if self.coverage is not CoverageLevel.AUTOMATED and not self.blocking_gaps:
            raise ValueError("non-automated case requires blocking gaps")
        return self


class ExpectedProblemBenchmarkManifest(ContractModel):
    benchmark_version: Annotated[str, Field(pattern=r"^0\.1$")]
    problem_bank_version: Annotated[str, Field(pattern=r"^Draft 2$")]
    cases: list[ExpectedProblemCase]

    @model_validator(mode="after")
    def contains_the_approved_bank(self) -> "ExpectedProblemBenchmarkManifest":
        problem_ids = [item.problem_id for item in self.cases]
        if len(problem_ids) != len(set(problem_ids)):
            raise ValueError("benchmark manifest must not contain duplicate expected problems")
        if set(problem_ids) != APPROVED_EXPECTED_PROBLEM_IDS:
            raise ValueError("benchmark manifest must contain the approved expected-problem bank")
        automated_ids = {
            item.problem_id for item in self.cases if item.coverage is CoverageLevel.AUTOMATED
        }
        if automated_ids != APPROVED_AUTOMATED_PROBLEM_IDS:
            raise ValueError("benchmark manifest must use the approved automated problem set")
        return self


class BenchmarkCaseResult(ContractModel):
    problem_id: str
    fixture_id: str
    passed: bool
    status_complete: bool
    answer_exact: bool
    evidence_complete: bool
    requirements_complete: bool
    deterministic: bool
    elapsed_ms: Annotated[float, Field(ge=0)]
    findings: list[str]


class ExpectedProblemBenchmarkReport(ContractModel):
    benchmark_version: str
    total_problems: int
    automated: int
    assisted: int
    unsupported: int
    executed: int
    passed: int
    failed: int
    automated_pass_rate: Annotated[float, Field(ge=0, le=1)]
    cases: list[BenchmarkCaseResult]


@dataclass(frozen=True, slots=True)
class ExpectedProblemBenchmarkRunner:
    repository_root: Path

    def load_manifest(self, path: Path) -> ExpectedProblemBenchmarkManifest:
        resolved = _safe_path(self.repository_root, path)
        return ExpectedProblemBenchmarkManifest.model_validate(json.loads(resolved.read_text()))

    def run(
        self,
        manifest: ExpectedProblemBenchmarkManifest,
    ) -> ExpectedProblemBenchmarkReport:
        executable = [item for item in manifest.cases if item.coverage is CoverageLevel.AUTOMATED]
        results = [self._run_case(item) for item in executable]
        passed = sum(item.passed for item in results)
        counts = {
            level: sum(item.coverage is level for item in manifest.cases) for level in CoverageLevel
        }
        return ExpectedProblemBenchmarkReport(
            benchmark_version=manifest.benchmark_version,
            total_problems=len(manifest.cases),
            automated=counts[CoverageLevel.AUTOMATED],
            assisted=counts[CoverageLevel.ASSISTED],
            unsupported=counts[CoverageLevel.UNSUPPORTED],
            executed=len(results),
            passed=passed,
            failed=len(results) - passed,
            automated_pass_rate=passed / len(results) if results else 0,
            cases=results,
        )

    def _run_case(self, case: ExpectedProblemCase) -> BenchmarkCaseResult:
        fixture = case.fixture
        if fixture is None:
            raise ValueError("benchmark runner received a non-executable case")
        request = validate_analysis_request(
            json.loads(_safe_path(self.repository_root, Path(fixture.request_path)).read_text())
        )
        replay_path = _safe_path(self.repository_root, Path(fixture.replay_path))
        replay = replay_path.read_bytes()
        package_dir = replay_path.parent
        started = perf_counter()
        first = _analyze(request, replay, package_dir=package_dir)
        second = _analyze(request, replay, package_dir=package_dir)
        elapsed_ms = (perf_counter() - started) * 1000
        expected = {item.result_type: item.value for item in fixture.expected_results}
        actual_result_count = len(first.root.results)
        actual = {item.result_type: item.value for item in first.root.results}
        evidence_ids = {item.evidence_id for item in first.root.evidence}
        requirement_ids = {
            requirement_id
            for item in first.root.results
            for requirement_id in item.fixture_requirement_ids
        }
        checks = {
            "status_complete": first.root.status is AnalysisStatus.COMPLETE,
            "answer_exact": len(actual) == actual_result_count and actual == expected,
            "evidence_complete": bool(first.root.evidence)
            and all(set(item.evidence_refs) <= evidence_ids for item in first.root.results),
            "requirements_complete": set(fixture.required_fixture_requirements) <= requirement_ids,
            "deterministic": first.to_contract_dict() == second.to_contract_dict(),
        }
        findings = [name for name, passed in checks.items() if not passed]
        return BenchmarkCaseResult(
            problem_id=case.problem_id,
            fixture_id=fixture.fixture_id,
            passed=not findings,
            elapsed_ms=elapsed_ms,
            findings=findings,
            **checks,
        )


def _safe_path(repository_root: Path, path: Path) -> Path:
    root = repository_root.resolve()
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError("benchmark path must reference an existing repository file")
    return resolved


def _analyze(
    request: AnalysisRequest,
    replay: bytes,
    *,
    package_dir: Path,
) -> AnalysisResult:
    document = request.root
    if isinstance(document, DexAnalysisRequest):
        return analyze_dex_replay(document, replay)
    if isinstance(document, AuthAnalysisRequest):
        return analyze_auth_replay(document, replay)
    if isinstance(document, FreezeAnalysisRequest):
        return analyze_freeze_replay(document, replay)
    if isinstance(document, EvmCoreAnalysisRequest):
        return analyze_evm_core_replay(document, replay)
    if isinstance(document, EvmSpecialAnalysisRequest):
        return analyze_evm_special_replay(document, replay)
    if isinstance(document, FlowPathAnalysisRequest):
        return analyze_flow_path_replay(document, replay)
    if isinstance(document, IntelContextAnalysisRequest):
        return analyze_intel_context_replay(document, replay)
    if isinstance(document, BridgeTransferAnalysisRequest):
        return analyze_bridge_transfer_replay(document, replay, package_dir=package_dir)
    if isinstance(document, BitcoinUtxoAnalysisRequest):
        return analyze_bitcoin_utxo_replay(document, replay, package_dir=package_dir)
    if isinstance(document, CexClusterAnalysisRequest):
        return analyze_cex_cluster_replay(document, replay, package_dir=package_dir)
    if isinstance(document, MixerFlowAnalysisRequest):
        return analyze_mixer_flow_replay(document, replay, package_dir=package_dir)
    raise ValueError("unsupported benchmark analysis type")
