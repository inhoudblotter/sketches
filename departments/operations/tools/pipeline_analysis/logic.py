"""Facade: orchestrates parsers → graph → metrics → schemas."""

from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from departments.operations.tools.shared import agent_parser, tool_parser
from . import config
from .engine.cost import agent_cost
from .engine.fs import artifact_builder
from .engine.playbooks import execution_stages as execution_stages_module
from .engine.graph import graph_builder
from .engine.core import legacy_analysis, metrics as metrics_module
from .engine.playbooks import playbook_stats as playbook_stats_module
from .engine.validation import quality_checks, status_checker
from .schemas import GraphEdge, ReportData, ToolNode


def run(
    agents_dir: Path, workspace_dir: Path, on_stage: Callable[[str], None] | None = None
) -> ReportData:
    _stage = on_stage or (lambda _key: None)

    _stage("parse_agents")
    raw_agents = agent_parser.parse_all(agents_dir)
    # workspace_dir is typically "workspace/<department>", not "workspace" —
    # its parent is NOT the project root, so tools_dir must be derived from
    # cwd (the convention already used for project_root elsewhere in this
    # module), or tool_parser.parse_all silently finds nothing (it treats a
    # missing dir as "no tools" rather than erroring).
    _stage("parse_tools")
    tools_dir = Path.cwd() / "departments"
    raw_tools = tool_parser.parse_all(tools_dir)
    compositions = tool_parser.parse_compositions(tools_dir, raw_tools)

    _stage("build_graph")
    G = graph_builder.build(raw_agents, workspace_dir, raw_tools, compositions)

    _stage("check_status")
    statuses = status_checker.check_all(raw_agents, G, workspace_dir, tools=raw_tools)

    _stage("compute_metrics")
    computed_metrics = metrics_module.compute(G, statuses, raw_agents, workspace_dir)

    project_root = Path.cwd()
    dept_name = workspace_dir.name

    _stage("run_tests")
    quality_checks.run_tests(computed_metrics, project_root, dept_name)

    _stage("run_python_linters")
    quality_checks.run_python_linters(computed_metrics, project_root)

    _stage("check_git_coverage")
    quality_checks.check_git_coverage(computed_metrics, agents_dir)

    _stage("measure_costs")
    agent_nodes, tool_invocation_costs = agent_cost.compute_agent_nodes(
        raw_agents, raw_tools, G, statuses, project_root, workspace_dir
    )

    _stage("check_unknown_tools")
    quality_checks.check_unknown_tools(agent_nodes, raw_tools)

    computed_metrics.agent_validation_errors = [
        {"file_path": a.source_file, "errors": a.validation_errors}
        for a in agent_nodes
        if a.validation_status == "error"
    ]

    edges = [
        GraphEdge(
            source=u,
            target=v,
            edge_type=d["edge_type"],
            is_optional=d.get("is_optional", False),
        )
        for u, v, d in G.edges(data=True)
    ]

    _stage("build_playbooks")
    playbook_dict, playbook_stats = playbook_stats_module.build_playbook_stats(
        raw_agents, project_root
    )

    _stage("build_legacy")
    department_root = agents_dir.parent
    used_playbooks = set(playbook_dict.keys())
    legacy = legacy_analysis.build_legacy(
        raw_agents, raw_tools, compositions, used_playbooks, department_root
    )

    _stage("build_stages")
    execution_stages, stage_map = execution_stages_module.build_execution_stages(
        G, statuses
    )
    for agent in agent_nodes:
        agent.stage_number = stage_map.get(agent.name, 999)

    # Linters never appear on the graph — they don't produce or mediate files,
    # they just validate them, which is instead surfaced on the artifact itself.
    # Also scoped to this department (meta.yaml `department:`), same reasoning
    # as unused_tools in legacy_analysis: tool_parser scans the whole
    # `departments/` tree, so without this a totally unrelated department's
    # tools (e.g. an operations-owned linter/generator no agent here could
    # ever call) would show up as graph/legend nodes for every department's
    # report.
    tool_nodes = [
        ToolNode(**t)
        for t in raw_tools
        if t.get("department") == agents_dir.parent.name
    ]

    _stage("check_contract_drift")
    quality_checks.check_contract_drift(computed_metrics, project_root, tool_nodes)

    _stage("build_artifacts")
    artifact_nodes, artifact_tree = artifact_builder.build_artifacts(G)

    tool_invocation_cost_summary = agent_cost.summarize_tool_invocation_costs(
        tool_invocation_costs
    )

    return ReportData(
        generated_at=datetime.now(timezone.utc).isoformat(),
        agents_dir=str(agents_dir),
        workspace_dir=str(workspace_dir),
        agents=agent_nodes,
        edges=edges,
        metrics=computed_metrics,
        playbooks=playbook_stats,
        execution_stages=execution_stages,
        tools=tool_nodes,
        artifacts=artifact_nodes,
        artifact_tree=artifact_tree,
        legacy=legacy,
        tool_invocation_costs=tool_invocation_costs,
        tool_invocation_cost_summary=tool_invocation_cost_summary,
        risk_ok_max_kb=config.RISK_OK_MAX_KB,
        risk_high_min_kb=config.RISK_HIGH_MIN_KB,
    )
