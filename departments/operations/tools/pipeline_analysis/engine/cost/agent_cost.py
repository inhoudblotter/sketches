"""Per-agent cost computation: reads/writes/skills/tool-call sizing → AgentNode.

Split out of logic.run() — this is the single largest, most self-contained
chunk of that function (file-list KB sizing, tool invocation cost measurement,
AgentNode assembly), and doesn't need anything from the artifact/legacy/stage
building that follows it in the orchestrator.
"""

from __future__ import annotations
from pathlib import Path
from typing import Literal

import networkx as nx

from departments.operations.tools.validators.validate_agent import (
    logic as validate_agent_logic,
)
from departments.operations.tools.shared.tool_parser import _norm
from ..core.utils import _skill_size_kb
from ..cost.tool_output_cost import measure_agent_tool_costs
from ...schemas import AgentNode, ToolInvocationCost


from ..fs.file_sizing import build_template_kb_by_path, _calculate_file_list_kb


def _validate_agent_source(
    source_file: str | None,
) -> tuple[Literal["ok", "error", "unknown"], list[str]]:
    if not source_file:
        return "unknown", []
    try:
        lint_result = validate_agent_logic.validate_file(Path(source_file))
        return lint_result.status, [
            f"[{e.rule}] {e.message}" for e in lint_result.errors
        ]
    except Exception as e:
        return "error", [f"[Validator Crash] {e}"]


def _compute_agent_run_counts(
    a: dict, runs_w_unlooped: int, actual_runs_w_unlooped: int
) -> tuple[int, int, int, int]:
    if not a.get("writes"):
        return 1, 1, 0, 0
    return (
        runs_w_unlooped,
        runs_w_unlooped,
        actual_runs_w_unlooped,
        actual_runs_w_unlooped,
    )


def _build_agent_node(
    a: dict,
    G: nx.DiGraph,
    statuses: dict,
    project_root: Path,
    workspace_dir: Path,
    template_kb_by_path: dict[str, float],
    tools_by_key_for_cost: dict[str, dict],
) -> tuple[AgentNode, list[dict]]:
    name = a["name"]
    node_data = G.nodes.get(name, {})
    status_info = statuses.get(name, {"status": "UNKNOWN", "blocked_on": []})

    playbook_sizes = {p: _skill_size_kb(p, project_root) for p in a["required_skills"]}
    validation_status, validation_errors = _validate_agent_source(a.get("source_file"))

    fan_in = sum(
        1 for _, _, d in G.in_edges(name, data=True) if d.get("edge_type") == "reads"
    )
    fan_out = sum(
        1 for _, _, d in G.out_edges(name, data=True) if d.get("edge_type") == "writes"
    )

    skill_kb = node_data.get("context_load_kb", 0.0)
    art_kb, _runs_r, _, art_partial = _calculate_file_list_kb(
        a.get("reads", []),
        a.get("optional_reads", []),
        a.get("looped_reads", []),
        project_root,
        template_kb_by_path,
    )
    contracts_kb, _, _, _ = _calculate_file_list_kb(
        a.get("contracts", []),
        [],
        [],
        project_root,
        template_kb_by_path,
    )
    out_kb, _runs_w, runs_w_unlooped, _out_partial = _calculate_file_list_kb(
        a.get("writes", []),
        a.get("optional_writes", []),
        a.get("looped_writes", []),
        project_root,
        template_kb_by_path,
    )
    actual_out_kb, _actual_runs_w, actual_runs_w_unlooped, _ = _calculate_file_list_kb(
        a.get("writes", []),
        a.get("optional_writes", []),
        a.get("looped_writes", []),
        project_root,
        {},
    )

    runs, runs_min, actual_runs, actual_runs_min = _compute_agent_run_counts(
        a, runs_w_unlooped, actual_runs_w_unlooped
    )

    agent_tool_costs = measure_agent_tool_costs(
        a, tools_by_key_for_cost, project_root, workspace_dir
    )
    # "write"-mode records are never executed here, so they're excluded
    # from context cost (the calling agent never reads this back into its
    # own context that way). Their kb — real for a single-purpose tool's
    # own deterministic output (e.g. generate_pitch_deck), 0.0 for a
    # situational mutation subcommand that's never sized — instead counts
    # as data *produced*, alongside this agent's own <write> tags below.
    context_costs = [r for r in agent_tool_costs if r["mode"] != "write"]
    tool_write_kb = round(
        sum(r["kb"] for r in agent_tool_costs if r["mode"] == "write"), 2
    )
    tool_kb = round(sum(r["kb"] for r in context_costs), 2)
    tool_runs = sum(r["runs"] for r in context_costs)

    own_write_kb = out_kb
    out_kb = round(out_kb + tool_write_kb, 2)

    actual_own_write_kb = actual_out_kb
    actual_outputs_kb = round(actual_own_write_kb + tool_write_kb, 2)

    total_ctx = round(skill_kb + art_kb + tool_kb, 2)
    # Context Budget's "Total KB"/risk flag also counts this agent's own
    # <write> output (own_write_kb) — before it's handed off downstream,
    # it sits in the agent's own working context alongside everything it
    # read. Tool-produced output (e.g. generate_pitch_deck's HTML) is
    # excluded here: that's a separate process's file, never held in this
    # agent's context, so it stays Output-Sizes-only (out_kb above).
    total_risk = round(total_ctx + own_write_kb, 2)

    node = AgentNode(
        name=name,
        description=a.get("description", ""),
        model=a["model"],
        temperature=a["temperature"],
        tools=a["tools"],
        uses_tools=a.get("uses_tools", []),
        required_skills=a["required_skills"],
        contracts=a["contracts"],
        reads=a["reads"],
        writes=a["writes"],
        optional_reads=a.get("optional_reads", []),
        optional_writes=a.get("optional_writes", []),
        escalation_handoff=a["escalation_handoff"],
        source_file=a.get("source_file", ""),
        is_subagent=a.get("is_subagent", False),
        # unresolved template targets (e.g. "{scout_name}") are dropped here too —
        # see the matching skip in graph_builder.build()
        delegates_to=[d for d in a.get("delegates_to", []) if "{" not in d],
        optional_delegates=[d for d in a.get("optional_delegates", []) if "{" not in d],
        fan_in=fan_in,
        fan_out=fan_out,
        context_load_kb=total_ctx,
        context_is_partial=art_partial,
        total_sort_kb=total_risk,
        total_risk_kb=total_risk,
        artifacts_kb=art_kb,
        own_write_kb=own_write_kb,
        outputs_kb=out_kb,
        skills_kb=skill_kb,
        contracts_kb=contracts_kb,
        tool_output_kb=tool_kb,
        tool_write_kb=tool_write_kb,
        tool_output_runs=tool_runs,
        status=status_info["status"],
        blocked_on=status_info["blocked_on"],
        playbook_sizes=playbook_sizes,
        validation_status=validation_status,
        validation_errors=validation_errors,
        runs=runs,
        runs_min=runs_min,
        actual_runs=actual_runs,
        actual_runs_min=actual_runs_min,
        actual_own_write_kb=actual_own_write_kb,
        actual_outputs_kb=actual_outputs_kb,
    )
    return node, agent_tool_costs


def compute_agent_nodes(
    raw_agents: list[dict],
    raw_tools: list[dict],
    G: nx.DiGraph,
    statuses: dict,
    project_root: Path,
    workspace_dir: Path,
) -> tuple[list[AgentNode], list[ToolInvocationCost]]:
    template_kb_by_path = build_template_kb_by_path(raw_agents, project_root)

    tools_by_key_for_cost: dict[str, dict] = {}
    for t in raw_tools:
        for key in t.get("match_keys", []) or [_norm(t["name"])]:
            tools_by_key_for_cost[key] = t

    tool_invocation_costs: list[ToolInvocationCost] = []
    agent_nodes: list[AgentNode] = []

    for a in raw_agents:
        node, agent_tool_costs = _build_agent_node(
            a,
            G,
            statuses,
            project_root,
            workspace_dir,
            template_kb_by_path,
            tools_by_key_for_cost,
        )
        agent_nodes.append(node)
        tool_invocation_costs.extend(
            ToolInvocationCost(agent=a["name"], **r) for r in agent_tool_costs
        )

    return agent_nodes, tool_invocation_costs


def summarize_tool_invocation_costs(
    tool_invocation_costs: list[ToolInvocationCost],
) -> list[ToolInvocationCost]:
    # tool_invocation_costs (raw, one entry per <call_tool> *site*, skipped
    # included) stays as-is — agents.html.j2 uses it to tag which tools an
    # agent calls at all, skipped ones included. For the cost tables
    # (report.md.j2 / analytics.html.j2 "Tool Invocation Cost"), a workflow
    # that checks something, acts, then re-checks the same query (or a
    # Validate Patch call repeated across several gap-fix branches) produces
    # several byte-identical rows there, and skipped entries (linters/
    # validators never executed, always 0 KB) add pure noise on top. Build a
    # deduped, non-skipped summary for those views: merge identical (agent,
    # tool, subcommand, invocation, mode) rows into one, tracking how many
    # sites they came from.
    invocation_summary: dict[tuple, ToolInvocationCost] = {}
    for c in tool_invocation_costs:
        if c.mode == "skipped":
            continue
        key = (c.agent, c.tool, c.subcommand, c.invocation, c.mode)
        existing = invocation_summary.get(key)
        if existing:
            existing.runs += c.runs
            existing.kb = round(existing.kb + c.kb, 2)
            existing.sites += 1
        else:
            invocation_summary[key] = c.model_copy()
    return list(invocation_summary.values())
