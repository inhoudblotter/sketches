import networkx as nx


def _get_orchestrator(node: str, G: nx.DiGraph, agent_set: set[str]) -> str | None:
    if node in agent_set:
        return node
    if G.nodes[node].get("is_subagent"):
        parents = [
            u
            for u, v, d in G.in_edges(node, data=True)
            if d.get("edge_type") == "delegates"
        ]
        if parents:
            return parents[0]
        return node
    return None


def _get_agents_using_tool(tool_node: str, G: nx.DiGraph) -> list[str]:
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


def _get_raw_producers(artifact: str, G: nx.DiGraph) -> list[str]:
    raw_producers = []
    for u, _ in G.in_edges(artifact):
        if G.nodes[u].get("node_type") == "agent":
            raw_producers.append(u)
        elif (
            G.nodes[u].get("node_type") == "tool"
            and G.nodes[u].get("tool_type") != "linter"
        ):
            raw_producers.extend(_get_agents_using_tool(u, G))
    return raw_producers


def _get_raw_consumers(artifact: str, G: nx.DiGraph) -> list[str]:
    raw_consumers = []
    for _, v, d in G.out_edges(artifact, data=True):
        if d.get("is_optional"):
            continue
        if G.nodes[v].get("node_type") == "agent":
            raw_consumers.append(v)
        elif (
            G.nodes[v].get("node_type") == "tool"
            and G.nodes[v].get("tool_type") != "linter"
        ):
            raw_consumers.extend(_get_agents_using_tool(v, G))
    return raw_consumers


def _process_artifact(
    artifact: str, G: nx.DiGraph, agent_set: set[str], ag: nx.DiGraph
) -> None:
    raw_producers = _get_raw_producers(artifact, G)
    raw_consumers = _get_raw_consumers(artifact, G)

    producers = {_get_orchestrator(u, G, agent_set) for u in raw_producers} - {None}
    consumers = {_get_orchestrator(v, G, agent_set) for v in raw_consumers} - {None}

    for p in producers:
        for c in consumers:
            if p != c:
                ag.add_edge(p, c)


def build_agent_subgraph(G: nx.DiGraph) -> nx.DiGraph:
    agents = []
    for n, d in G.nodes(data=True):
        if d.get("node_type") == "agent":
            if not d.get("is_subagent", False):
                agents.append(n)
            else:
                parents = [
                    u
                    for u, v, e in G.in_edges(n, data=True)
                    if e.get("edge_type") == "delegates"
                ]
                if not parents:
                    agents.append(n)

    agent_set = set(agents)
    ag: nx.DiGraph = nx.DiGraph()
    ag.add_nodes_from(agents)

    artifacts = [n for n, d in G.nodes(data=True) if d.get("node_type") == "artifact"]
    for artifact in artifacts:
        _process_artifact(artifact, G, agent_set, ag)

    return ag
