from __future__ import annotations
from pathlib import Path
import networkx as nx

from departments.operations.tools.shared.tool_parser import _matches_any
from ..core.utils import _artifact_attrs


def _wire_standalone_tool_outputs(
    G: nx.DiGraph, tool_name: str, tool: dict, workspace_dir: Path
) -> None:
    artifact_nodes_for_outputs = [
        n for n, d in G.nodes(data=True) if d.get("node_type") == "artifact"
    ]
    for output_pattern in tool.get("outputs", []):
        if output_pattern == "stdout":
            continue

        matched = False
        for artifact in artifact_nodes_for_outputs:
            if (
                artifact != tool_name
                and not G.has_edge(tool_name, artifact)
                and _matches_any(artifact, [output_pattern])
            ):
                G.add_edge(tool_name, artifact, edge_type="produces", is_optional=False)
                G.nodes[artifact]["locked"] = True
                existing = set(G.nodes[artifact].get("validated_by", []))
                G.nodes[artifact]["validated_by"] = sorted(existing | {tool_name})
                matched = True

        if not matched and "*" not in output_pattern and "?" not in output_pattern:
            if output_pattern not in G:
                G.add_node(
                    output_pattern, **_artifact_attrs(output_pattern, workspace_dir)
                )
            if not G.has_edge(tool_name, output_pattern):
                G.add_edge(
                    tool_name,
                    output_pattern,
                    edge_type="produces",
                    is_optional=False,
                )
                G.nodes[output_pattern]["locked"] = True
                existing = set(G.nodes[output_pattern].get("validated_by", []))
                G.nodes[output_pattern]["validated_by"] = sorted(existing | {tool_name})


def _wire_standalone_tool_inputs(G: nx.DiGraph, tool_name: str, tool: dict) -> None:
    tool_inputs = tool.get("inputs", [])
    optional_tool_inputs = tool.get("optional_inputs", [])
    if not tool_inputs and not optional_tool_inputs:
        return
    artifact_nodes_for_inputs = [
        n for n, d in G.nodes(data=True) if d.get("node_type") == "artifact"
    ]
    for artifact in artifact_nodes_for_inputs:
        if artifact == tool_name or G.has_edge(artifact, tool_name):
            continue
        if _matches_any(artifact, tool_inputs):
            G.add_edge(artifact, tool_name, edge_type="reads", is_optional=False)
        elif _matches_any(artifact, optional_tool_inputs):
            G.add_edge(artifact, tool_name, edge_type="reads", is_optional=True)


def wire_standalone_tools(
    G: nx.DiGraph, tools_by_name: dict, workspace_dir: Path
) -> None:
    tool_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "tool"]
    for tool_name in tool_nodes:
        tool = tools_by_name.get(tool_name)
        if not tool:
            continue
        _wire_standalone_tool_outputs(G, tool_name, tool, workspace_dir)
        _wire_standalone_tool_inputs(G, tool_name, tool)
