from __future__ import annotations
from pathlib import Path
import networkx as nx

from ..graph.tool_wiring import _subcommand_node, _wire_command_outputs
from ..core.utils import _resolve_tool, _invocation_subcommand


def _resolve_uses_tools(
    G: nx.DiGraph, name: str, uses_tools: list, tools_by_key: dict
) -> list:
    resolved_tools = []
    for tool_name in uses_tools:
        tool = _resolve_tool(tool_name, tools_by_key)
        node_id = tool["name"] if tool else tool_name
        if node_id not in G:
            G.add_node(
                node_id,
                node_type="tool",
                tool_type=(tool or {}).get("tool_type", "unknown"),
                contract=(tool or {}).get("contract"),
            )
        G.add_edge(name, node_id, edge_type="uses_tool")
        resolved_tools.append((node_id, tool))
    return resolved_tools


def _handle_composition_subcommand(
    G: nx.DiGraph,
    caller: dict,
    callee: dict,
    subcommand: str,
    expanded_tools: list,
    workspace_dir: Path,
    composition_subcommand_wiring: list,
) -> None:
    node_id = _subcommand_node(
        G, caller["name"], callee, subcommand, edge_type="calls_tool"
    )
    cmd_meta = callee["commands"][subcommand]
    for output_pattern in cmd_meta.get("outputs", []):
        _wire_command_outputs(G, node_id, output_pattern, workspace_dir)
    composition_subcommand_wiring.append(
        (node_id, cmd_meta, callee["name"], subcommand)
    )
    if callee.get("tool_type") == "linter":
        synth_linter = dict(callee)
        synth_linter["name"] = node_id
        synth_linter["inputs"] = cmd_meta.get("inputs", []) + cmd_meta.get(
            "optional_inputs", []
        )
        expanded_tools.append((node_id, synth_linter))


def _process_compositions(
    G: nx.DiGraph,
    resolved_tools: list,
    compositions_by_caller: dict,
    expanded_tools: list,
    seen_tool_names: set,
    workspace_dir: Path,
    composition_subcommand_wiring: list,
) -> None:
    queue = [t for _, t in resolved_tools if t]
    while queue:
        caller = queue.pop()
        for callee, subcommand in compositions_by_caller.get(caller["name"], []):
            if subcommand and callee.get("commands", {}).get(subcommand):
                _handle_composition_subcommand(
                    G,
                    caller,
                    callee,
                    subcommand,
                    expanded_tools,
                    workspace_dir,
                    composition_subcommand_wiring,
                )
                continue

            if callee["name"] not in G:
                G.add_node(
                    callee["name"],
                    node_type="tool",
                    tool_type=callee.get("tool_type", "unknown"),
                    contract=callee.get("contract"),
                )
            G.add_edge(caller["name"], callee["name"], edge_type="calls_tool")
            if callee["name"] not in seen_tool_names:
                seen_tool_names.add(callee["name"])
                expanded_tools.append((callee["name"], callee))
                queue.append(callee)


def _process_tool_invocations(
    G: nx.DiGraph,
    name: str,
    invocations: list,
    tools_by_key: dict,
    expanded_tools: list,
    workspace_dir: Path,
) -> None:
    for inv in invocations:
        tool = _resolve_tool(inv["tool"], tools_by_key)
        if not tool or not tool.get("commands"):
            continue
        subcommand = _invocation_subcommand(inv["invocation"], tool)
        cmd_meta = tool["commands"].get(subcommand) if subcommand else None
        if not cmd_meta or not subcommand:
            continue

        node_id = _subcommand_node(G, name, tool, subcommand)
        for output_pattern in cmd_meta.get("outputs", []):
            _wire_command_outputs(G, node_id, output_pattern, workspace_dir)

        if tool.get("tool_type") == "linter":
            synth_linter = dict(tool)
            synth_linter["name"] = node_id
            synth_linter["inputs"] = cmd_meta.get("inputs", []) + cmd_meta.get(
                "optional_inputs", []
            )
            expanded_tools.append((node_id, synth_linter))


def process_tool_usages(
    G: nx.DiGraph,
    agent: dict,
    tools_by_key: dict,
    compositions_by_caller: dict,
    workspace_dir: Path,
    composition_subcommand_wiring: list,
) -> tuple[list, list]:
    name = agent["name"]
    resolved_tools = _resolve_uses_tools(
        G, name, agent.get("uses_tools", []), tools_by_key
    )

    expanded_tools = list(resolved_tools)
    seen_tool_names = {t["name"] for _, t in resolved_tools if t}

    _process_compositions(
        G,
        resolved_tools,
        compositions_by_caller,
        expanded_tools,
        seen_tool_names,
        workspace_dir,
        composition_subcommand_wiring,
    )

    _process_tool_invocations(
        G,
        name,
        agent.get("tool_invocations", []),
        tools_by_key,
        expanded_tools,
        workspace_dir,
    )

    producer_tools = [
        (nid, t) for nid, t in expanded_tools if t and t.get("tool_type") != "linter"
    ]
    linter_tools = [
        (nid, t) for nid, t in expanded_tools if t and t.get("tool_type") == "linter"
    ]
    return producer_tools, linter_tools
