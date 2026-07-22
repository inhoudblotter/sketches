"""Artifact node + artifact tree building, split out of logic.run()."""

from __future__ import annotations

import networkx as nx

from ...schemas import ArtifactNode


def _get_agents_using_tool(G: nx.DiGraph, tool_node: str) -> list[str]:
    using_agents = []
    queue = [tool_node]
    seen = {tool_node}
    while queue:
        curr = queue.pop(0)
        for u, _, d in G.in_edges(curr, data=True):
            if d.get("edge_type") in ("uses_tool", "calls_tool"):
                if G.nodes[u].get("node_type") == "agent":
                    using_agents.append(u)
                elif u not in seen:
                    seen.add(u)
                    queue.append(u)
    return using_agents


def _build_tree(paths: list[str]) -> str:
    if not paths:
        return ""
    tree_dict: dict = {}
    for p in paths:
        parts = p.split("/")
        curr = tree_dict
        for part in parts:
            curr = curr.setdefault(part, {})

    def _render_node(node, prefix=""):
        lines = []
        keys = sorted(node.keys())
        for i, key in enumerate(keys):
            is_last = i == len(keys) - 1
            connector = "└── " if is_last else "├── "
            lines.append(prefix + connector + key)
            if node[key]:
                extension = "    " if is_last else "│   "
                lines.extend(_render_node(node[key], prefix + extension))
        return lines

    return "\n".join(_render_node(tree_dict))


def build_artifacts(G: nx.DiGraph) -> tuple[list[ArtifactNode], str]:
    artifact_nodes = []
    for n, d in G.nodes(data=True):
        if d.get("node_type") == "artifact":
            raw_producers = []
            for u, _ in G.in_edges(n):
                if G.nodes[u].get("node_type") == "agent":
                    raw_producers.append(u)
                elif G.nodes[u].get("node_type") == "tool":
                    raw_producers.extend(_get_agents_using_tool(G, u))

            artifact_nodes.append(
                ArtifactNode(
                    path=n,
                    locked=d.get("locked", False),
                    validated_by=d.get("validated_by", []),
                    no_producer=G.in_degree(n) == 0 and G.out_degree(n) > 0,
                    dead_end=G.out_degree(n) == 0 and G.in_degree(n) > 0,
                    exists=d.get("exists", True),
                    producers=sorted(set(raw_producers)),
                )
            )

    # All paths that are internal (not external inputs)
    internal_paths = [
        a.path
        for a in artifact_nodes
        if not (G.in_degree(a.path) == 0 and G.out_degree(a.path) > 0)
    ]
    artifact_tree = _build_tree(internal_paths)

    return artifact_nodes, artifact_tree
