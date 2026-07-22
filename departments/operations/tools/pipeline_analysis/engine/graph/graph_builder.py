from __future__ import annotations
from pathlib import Path
import networkx as nx

from departments.operations.tools.shared.tool_parser import _norm, _matches_any
from ..playbooks import playbook_analyzer
from ..fs.directory_resolver import resolve_directories
from ..fs.template_resolver import resolve_templates
from ..core.utils import (
    _resolve_tool,
    _invocation_subcommand,
    _artifact_attrs,
    _skill_size_kb,
)
from ..graph.tool_wiring import (
    _wire_command_inputs,
    _subcommand_node,
    _is_soft_scheduling_input,
)
from ..graph.agent_graph import build_agent_subgraph
from ..graph.graph_tool_usages import process_tool_usages
from ..graph.graph_standalone import wire_standalone_tools


def _add_agent_nodes(G: nx.DiGraph, agents: list[dict], project_root: Path) -> None:
    for agent in agents:
        name = agent["name"]
        transitive_skills = playbook_analyzer.transitive_closure(
            agent["required_skills"], project_root
        )
        skill_kb = sum(
            _skill_size_kb(s, project_root)
            for s in list(agent["required_skills"]) + list(transitive_skills)
        )
        agent["transitive_skills"] = sorted(transitive_skills)
        G.add_node(
            name,
            node_type="agent",
            model=agent["model"],
            temperature=agent["temperature"],
            context_load_kb=round(skill_kb, 2),
            is_subagent=agent.get("is_subagent", False),
        )


def _wire_agent_io(
    G: nx.DiGraph,
    agent: dict,
    workspace_dir: Path,
    producer_tools: list,
    linter_tools: list,
) -> None:
    name = agent["name"]
    for path_str in agent["writes"]:
        if path_str not in G:
            G.add_node(path_str, **_artifact_attrs(path_str, workspace_dir))
        is_optional = path_str in agent.get("optional_writes", [])

        producer = next(
            (
                nid
                for nid, t in producer_tools
                if _matches_any(path_str, t.get("outputs", []))
            ),
            None,
        )
        if producer:
            G.add_edge(
                producer, path_str, edge_type="produces", is_optional=is_optional
            )
        else:
            G.add_edge(name, path_str, edge_type="writes", is_optional=is_optional)

        validators = [
            t["name"]
            for _, t in linter_tools
            if _matches_any(path_str, t.get("inputs", []))
        ]
        if producer:
            validators.append(producer)

        if validators:
            existing = set(G.nodes[path_str].get("validated_by", []))
            G.nodes[path_str]["validated_by"] = sorted(existing | set(validators))
            G.nodes[path_str]["locked"] = True

    for path_str in agent["reads"]:
        if path_str not in G:
            G.add_node(path_str, **_artifact_attrs(path_str, workspace_dir))
        is_optional = path_str in agent.get("optional_reads", [])
        G.add_edge(path_str, name, edge_type="reads", is_optional=is_optional)


def _wire_agent_skills_and_delegation(
    G: nx.DiGraph, agent: dict, workspace_dir: Path
) -> None:
    name = agent["name"]
    for skill_path in agent["required_skills"]:
        if skill_path not in G:
            G.add_node(skill_path, **_artifact_attrs(skill_path, workspace_dir))
        G.add_edge(skill_path, name, edge_type="loads_skill")

    for skill_path in agent["transitive_skills"]:
        if skill_path not in G:
            G.add_node(skill_path, **_artifact_attrs(skill_path, workspace_dir))
        G.add_edge(skill_path, name, edge_type="loads_skill_transitive")

    for target_name in agent.get("delegates_to", []):
        if "{" in target_name:
            continue
        if target_name not in G:
            G.add_node(
                target_name,
                node_type="agent",
                model="unknown",
                temperature=0.5,
                context_load_kb=0.0,
            )
        G.add_edge(name, target_name, edge_type="delegates")


def _build_tool_mappings(
    tools: list[dict] | None,
) -> tuple[dict[str, dict], dict[str, dict]]:
    tools_by_key: dict[str, dict] = {}
    tools_by_name: dict[str, dict] = {}
    for t in tools or []:
        tools_by_name[t["name"]] = t
        for key in t.get("match_keys", []) or [_norm(t["name"])]:
            tools_by_key[key] = t
    return tools_by_name, tools_by_key


def _build_composition_mappings(
    compositions: list[tuple[str, str, str | None]] | None, tools_by_name: dict
) -> dict[str, list[tuple[dict, str | None]]]:
    compositions_by_caller: dict[str, list[tuple[dict, str | None]]] = {}
    for caller_name, callee_name, subcommand in compositions or []:
        callee = tools_by_name.get(callee_name)
        if callee:
            compositions_by_caller.setdefault(caller_name, []).append(
                (callee, subcommand)
            )
    return compositions_by_caller


def _wire_agent_tool_inputs(
    G: nx.DiGraph, agents: list[dict], tools_by_key: dict
) -> None:
    for agent in agents:
        for inv in agent.get("tool_invocations", []):
            tool = _resolve_tool(inv["tool"], tools_by_key)
            if (
                not tool
                or not tool.get("commands")
                or tool.get("tool_type") == "linter"
            ):
                continue
            subcommand = _invocation_subcommand(inv["invocation"], tool)
            cmd_meta = tool["commands"].get(subcommand) if subcommand else None
            if not cmd_meta or not subcommand:
                continue
            node_id = _subcommand_node(G, agent["name"], tool, subcommand)
            for input_pattern in cmd_meta.get("inputs", []):
                soft = _is_soft_scheduling_input(
                    tool["name"], subcommand, input_pattern
                )
                _wire_command_inputs(G, node_id, input_pattern, is_optional=soft)
            for input_pattern in cmd_meta.get("optional_inputs", []):
                _wire_command_inputs(G, node_id, input_pattern, is_optional=True)


def _wire_composition_inputs(
    G: nx.DiGraph, composition_subcommand_wiring: list
) -> None:
    for node_id, cmd_meta, tool_name, subcommand in composition_subcommand_wiring:
        for input_pattern in cmd_meta.get("inputs", []):
            soft = _is_soft_scheduling_input(tool_name, subcommand, input_pattern)
            _wire_command_inputs(G, node_id, input_pattern, is_optional=soft)
        for input_pattern in cmd_meta.get("optional_inputs", []):
            _wire_command_inputs(G, node_id, input_pattern, is_optional=True)


def build(
    agents: list[dict],
    workspace_dir: Path,
    tools: list[dict] | None = None,
    compositions: list[tuple[str, str, str | None]] | None = None,
) -> nx.DiGraph:
    G: nx.DiGraph = nx.DiGraph()
    project_root = Path.cwd()

    tools_by_name, tools_by_key = _build_tool_mappings(tools)
    compositions_by_caller = _build_composition_mappings(compositions, tools_by_name)

    composition_subcommand_wiring: list[tuple[str, dict, str, str | None]] = []

    _add_agent_nodes(G, agents, project_root)

    for agent in agents:
        producer_tools, linter_tools = process_tool_usages(
            G,
            agent,
            tools_by_key,
            compositions_by_caller,
            workspace_dir,
            composition_subcommand_wiring,
        )
        _wire_agent_io(G, agent, workspace_dir, producer_tools, linter_tools)
        _wire_agent_skills_and_delegation(G, agent, workspace_dir)

    _wire_agent_tool_inputs(G, agents, tools_by_key)
    _wire_composition_inputs(G, composition_subcommand_wiring)

    resolve_directories(G, agents, workspace_dir, _artifact_attrs)
    resolve_templates(G, agents, workspace_dir, _artifact_attrs)

    wire_standalone_tools(G, tools_by_name, workspace_dir)

    return G


# Re-export
__all__ = ["build", "build_agent_subgraph"]
