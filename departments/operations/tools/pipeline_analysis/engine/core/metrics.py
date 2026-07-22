"""Compute all report metrics from the DiGraph and status map."""

from __future__ import annotations
from pathlib import Path

import networkx as nx

from ..graph.agent_graph import build_agent_subgraph
from ...schemas import Metrics


def compute(
    G: nx.DiGraph,
    statuses: dict[str, dict],
    agents: list[dict],
    workspace_dir: Path,
) -> Metrics:
    artifact_nodes = [
        n for n, d in G.nodes(data=True) if d.get("node_type") == "artifact"
    ]

    # --- Debug ---
    orphaned_artifacts = [
        n for n in artifact_nodes if G.out_degree(n) == 0 and G.in_degree(n) > 0
    ]
    external_outputs = orphaned_artifacts

    external_inputs = []
    for n in artifact_nodes:
        if (
            G.in_degree(n) == 0
            and G.out_degree(n) > 0
            and any(
                d.get("edge_type") == "reads" for _, _, d in G.out_edges(n, data=True)
            )
        ):
            external_inputs.append(n)

    missing_inputs = [
        n
        for n in artifact_nodes
        if not G.nodes[n].get("exists", True)
        and G.out_degree(n) > 0
        and G.in_degree(n) == 0
        and any(
            not d.get("is_optional", False) for _, _, d in G.out_edges(n, data=True)
        )
    ]

    escalated_agents = [
        name for name, s in statuses.items() if s["status"] == "ESCALATED"
    ]

    # --- Optimization ---
    agent_graph = build_agent_subgraph(G)

    # Checked on the collapsed agent graph, not the raw G: subagent calls are
    # synchronous (delegate → wait → return), so an orchestrator handing a
    # scout a feedback file and re-reading its redone draft (refine loop)
    # shows up as agent → feedback.md → scout → draft.md → agent in the raw
    # artifact graph even though nothing is actually scheduled in a cycle.
    # build_agent_subgraph already resolves that back through the delegating
    # orchestrator and drops the resulting self-loop.
    has_cycles = not nx.is_directed_acyclic_graph(agent_graph)

    # A cycle in the raw agent graph (usually a false-positive scheduling
    # dependency, e.g. a subagent's tool call declaring an input that its
    # orchestrator's sibling phase produces later) makes dag_longest_path /
    # topological_generations raise outright, which used to blank out the
    # whole report. Collapse each strongly-connected component into a single
    # node (same technique logic.py's build_stages already uses for
    # execution_stages) so a cycle only fuzzes the agents actually involved
    # in it instead of hiding critical path / parallelism for the entire graph.
    condensed = nx.condensation(agent_graph)
    parallelism_groups = [
        [m for scc in gen for m in sorted(condensed.nodes[scc]["members"])]
        for gen in nx.topological_generations(condensed)
    ]
    scc_path = nx.dag_longest_path(condensed)
    critical_path = [
        m for scc in scc_path for m in sorted(condensed.nodes[scc]["members"])
    ]

    # --- Control ---
    top_agents = [a for a in agents if not a.get("is_subagent", False)]
    done_count = sum(
        1 for a in top_agents if statuses.get(a["name"], {}).get("status") == "DONE"
    )
    total = len(top_agents)
    completion_pct = round(done_count / total * 100, 1) if total else 0.0

    # workspace_dir is "workspace/<department>" — its parent is "workspace",
    # not the project root, so contract paths (e.g. "departments/.../x.yaml")
    # resolved against it would never exist. Contracts are declared relative
    # to cwd (the convention used everywhere else tool/skill paths resolve).
    project_root = Path.cwd()
    all_contracts: list[str] = []

    # Extract contracts declared by agents
    for agent in agents:
        all_contracts.extend(agent.get("contracts", []))

    # Extract contracts declared by tools
    for _n, d in G.nodes(data=True):
        if d.get("node_type") == "tool" and d.get("contract"):
            all_contracts.append(d["contract"])

    unique_contracts = list(dict.fromkeys(all_contracts))
    if unique_contracts:
        existing = sum(1 for c in unique_contracts if (project_root / c).exists())
        contract_coverage_pct = round(existing / len(unique_contracts) * 100, 1)
    else:
        contract_coverage_pct = 100.0

    output_artifacts = [n for n in artifact_nodes if G.in_degree(n) > 0]
    if output_artifacts:
        locked_count = sum(
            1 for n in output_artifacts if G.nodes[n].get("locked", False)
        )
        output_contract_coverage_pct = round(
            locked_count / len(output_artifacts) * 100, 1
        )
    else:
        output_contract_coverage_pct = 100.0

    HIGH_TEMPERATURE_THRESHOLD = 0.5
    temperature_risk_agents = [
        a["name"]
        for a in agents
        if a["temperature"] > HIGH_TEMPERATURE_THRESHOLD
        and "write_file" in a.get("tools", [])
    ]

    model_distribution: dict[str, int] = {}
    for a in agents:
        m = a["model"]
        model_distribution[m] = model_distribution.get(m, 0) + 1

    return Metrics(
        orphaned_artifacts=orphaned_artifacts,
        missing_inputs=missing_inputs,
        has_cycles=has_cycles,
        escalated_agents=escalated_agents,
        external_inputs=external_inputs,
        external_outputs=external_outputs,
        tool_test_results="",
        parallelism_groups=parallelism_groups,
        critical_path=critical_path,
        completion_pct=completion_pct,
        contract_coverage_pct=contract_coverage_pct,
        output_contract_coverage_pct=output_contract_coverage_pct,
        temperature_risk_agents=temperature_risk_agents,
        model_distribution=model_distribution,
    )
