from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


class ToolNode(BaseModel):
    name: str
    tool_type: Literal[
        "linter", "generator", "preprocessor", "aggregator", "analyzer", "unknown"
    ]
    description: str = ""
    department: str = ""
    inputs: list[str] = []
    outputs: list[str] = []
    commands: dict[str, dict] = Field(default_factory=dict)
    contract_drift: dict | None = None


class AgentNode(BaseModel):
    name: str
    description: str = ""
    model: str
    temperature: float
    tools: list[str]
    uses_tools: list[str] = []
    required_skills: list[str]
    contracts: list[str]
    reads: list[str]
    writes: list[str]
    optional_reads: list[str]
    optional_writes: list[str]
    escalation_handoff: str | None
    source_file: str = ""
    is_subagent: bool = False
    delegates_to: list[str] = []
    optional_delegates: list[str] = []
    fan_in: int
    fan_out: int
    context_load_kb: float
    context_is_partial: bool = (
        False  # some declared <read> input doesn't exist on disk yet (upstream not run) — estimated via contract template where possible
    )
    artifacts_kb: float = 0.0
    own_write_kb: float = 0.0
    outputs_kb: float = 0.0
    skills_kb: float = 0.0
    contracts_kb: float = 0.0
    tool_output_kb: float = 0.0
    tool_write_kb: float = 0.0
    tool_output_runs: int = 0
    total_sort_kb: float = 0.0
    total_risk_kb: float = 0.0
    status: Literal["DONE", "READY", "BLOCKED", "ESCALATED", "UNKNOWN"]
    blocked_on: list[str]
    playbook_sizes: dict[str, float] = Field(default_factory=dict)
    validation_status: Literal["ok", "error", "unknown"] = "unknown"
    validation_errors: list[str] = Field(default_factory=list)
    stage_number: int = 999
    runs: int = 1
    runs_min: int = 1
    actual_runs: int = 0
    actual_runs_min: int = 0
    actual_own_write_kb: float = 0.0
    actual_outputs_kb: float = 0.0


class GraphEdge(BaseModel):
    source: str
    target: str
    edge_type: Literal[
        "writes",
        "reads",
        "loads_skill",
        "loads_skill_transitive",
        "delegates",
        "template_match",
        "uses_tool",
        "produces",
        "calls_tool",
    ]
    is_optional: bool = False


class ArtifactNode(BaseModel):
    path: str
    locked: bool = False
    validated_by: list[str] = Field(default_factory=list)
    no_producer: bool = False  # read by someone, but nothing writes/produces it
    dead_end: bool = False  # written, but nobody reads it
    exists: bool = True  # present on disk at analysis time
    producers: list[str] = Field(default_factory=list)


class Metrics(BaseModel):
    # Debug
    orphaned_artifacts: list[str]
    missing_inputs: list[str]
    has_cycles: bool
    cycles: list[list[str]] = Field(default_factory=list)
    escalated_agents: list[str]
    # Architecture
    external_inputs: list[str] = Field(default_factory=list)
    external_outputs: list[str] = Field(default_factory=list)
    # Testing
    tool_test_results: str = ""
    tool_test_failures: list[str] = Field(default_factory=list)
    contract_drift: list[dict] = Field(default_factory=list)
    agent_validation_errors: list[dict] = Field(default_factory=list)
    git_coverage_findings: list[dict] = Field(default_factory=list)
    # Optimization
    parallelism_groups: list[list[str]]
    critical_path: list[str]
    # Control
    completion_pct: float
    contract_coverage_pct: float
    output_contract_coverage_pct: float
    temperature_risk_agents: list[str]
    model_distribution: dict[str, int]
    python_linter_results: dict[str, str] = Field(default_factory=dict)


class StageAgent(BaseModel):
    name: str
    status: Literal["DONE", "READY", "BLOCKED", "ESCALATED", "UNKNOWN"]
    subagents: list[str] = Field(default_factory=list)


class ExecutionStage(BaseModel):
    stage_number: int
    parallel_agents: list[StageAgent]


class PlaybookStat(BaseModel):
    name: str
    subscribers: list[str]
    size_kb: float
    references: list[str] = Field(default_factory=list)
    referenced_by: list[str] = Field(default_factory=list)


class LegacyAnalytics(BaseModel):
    unused_playbooks: list[str] = Field(default_factory=list)
    unused_tools: list[str] = Field(default_factory=list)
    unused_contracts: list[str] = Field(default_factory=list)
    dangling_contract_refs: list[str] = Field(default_factory=list)


class ToolInvocationCost(BaseModel):
    agent: str
    tool: str
    subcommand: str | None = None
    invocation: str
    mode: Literal["single", "p90", "full", "write", "skipped"]
    runs: int
    kb: float
    sites: int = 1


class ReportData(BaseModel):
    generated_at: str
    agents_dir: str
    workspace_dir: str
    agents: list[AgentNode]
    edges: list[GraphEdge]
    metrics: Metrics
    playbooks: list[PlaybookStat] = Field(default_factory=list)
    execution_stages: list[ExecutionStage] = Field(default_factory=list)
    tools: list[ToolNode] = Field(default_factory=list)
    artifacts: list[ArtifactNode] = Field(default_factory=list)
    artifact_tree: str = ""
    legacy: LegacyAnalytics = Field(default_factory=LegacyAnalytics)
    tool_invocation_costs: list[ToolInvocationCost] = Field(default_factory=list)
    tool_invocation_cost_summary: list[ToolInvocationCost] = Field(default_factory=list)
    risk_ok_max_kb: float = 150.0
    risk_high_min_kb: float = 300.0


class CLIResult(BaseModel):
    status: str
    output: str
    agents: int
    generated_at: str
