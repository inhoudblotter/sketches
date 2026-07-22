import networkx as nx
from pathlib import Path
from departments.operations.tools.shared.tool_parser import _matches_any
from ..core.utils import _artifact_attrs

_SOFT_SCHEDULING_INPUTS: set[tuple[str, str, str]] = {
    (
        "Query Discovery",
        "stories",
        "workspace/discovery/domains/*/epics/*/estimation.yaml",
    ),
}


def _is_soft_scheduling_input(
    tool_name: str, subcommand: str | None, input_pattern: str
) -> bool:
    return (tool_name, subcommand, input_pattern) in _SOFT_SCHEDULING_INPUTS


def _wire_command_outputs(
    G: nx.DiGraph, node_id: str, output_pattern: str, workspace_dir: Path
) -> None:
    if output_pattern == "stdout":
        return
    artifact_nodes = [
        n for n, d in G.nodes(data=True) if d.get("node_type") == "artifact"
    ]
    matched = False
    for artifact in artifact_nodes:
        if (
            artifact != node_id
            and not G.has_edge(node_id, artifact)
            and _matches_any(artifact, [output_pattern])
        ):
            G.add_edge(node_id, artifact, edge_type="produces", is_optional=False)
            existing = set(G.nodes[artifact].get("validated_by", []))
            G.nodes[artifact]["validated_by"] = sorted(existing | {node_id})
            matched = True
    if not matched and "*" not in output_pattern and "?" not in output_pattern:
        if output_pattern not in G:
            G.add_node(output_pattern, **_artifact_attrs(output_pattern, workspace_dir))
        if not G.has_edge(node_id, output_pattern):
            G.add_edge(node_id, output_pattern, edge_type="produces", is_optional=False)
            existing = set(G.nodes[output_pattern].get("validated_by", []))
            G.nodes[output_pattern]["validated_by"] = sorted(existing | {node_id})


def _wire_command_inputs(
    G: nx.DiGraph, node_id: str, input_pattern: str, is_optional: bool = False
) -> None:
    artifact_nodes = [
        n for n, d in G.nodes(data=True) if d.get("node_type") == "artifact"
    ]
    for artifact in artifact_nodes:
        if (
            artifact != node_id
            and not G.has_edge(artifact, node_id)
            and _matches_any(artifact, [input_pattern])
        ):
            G.add_edge(artifact, node_id, edge_type="reads", is_optional=is_optional)


def _subcommand_node(
    G: nx.DiGraph,
    caller_id: str,
    tool: dict,
    subcommand: str,
    edge_type: str = "uses_tool",
) -> str:
    node_id = f"{tool['name']}::{subcommand}"
    if node_id not in G:
        G.add_node(
            node_id,
            node_type="tool",
            tool_type=tool.get("tool_type", "unknown"),
            contract=tool.get("contract"),
        )
    if not G.has_edge(caller_id, node_id):
        G.add_edge(caller_id, node_id, edge_type=edge_type)
    return node_id
