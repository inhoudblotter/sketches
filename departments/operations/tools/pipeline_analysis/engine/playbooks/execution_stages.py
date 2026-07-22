"""Topological stage/parallelism-group computation, split out of logic.run()."""

from __future__ import annotations

import networkx as nx
from networkx import topological_generations

from ..graph.agent_graph import build_agent_subgraph
from ...schemas import ExecutionStage, StageAgent


def build_execution_stages(
    G: nx.DiGraph, statuses: dict
) -> tuple[list[ExecutionStage], dict[str, int]]:
    ag = build_agent_subgraph(G)
    cg = nx.condensation(ag)

    execution_stages: list[ExecutionStage] = []
    try:
        generations = list(topological_generations(cg))
        stage_idx = 1
        for gen in generations:
            stage_agents = []
            for node_id in gen:
                members = [m for m in cg.nodes[node_id]["members"] if "{" not in m]
                for m in members:
                    subagents = [
                        v
                        for _, v, d in G.out_edges(m, data=True)
                        if d.get("edge_type") == "delegates" and "{" not in v
                    ]
                    status_info = statuses.get(m, {"status": "UNKNOWN"})
                    stage_agents.append(
                        StageAgent(
                            name=m,
                            status=status_info.get("status", "UNKNOWN"),
                            subagents=subagents,
                        )
                    )
            if stage_agents:
                execution_stages.append(
                    ExecutionStage(stage_number=stage_idx, parallel_agents=stage_agents)
                )
                stage_idx += 1
    except Exception as e:
        print(f"[WARNING] Could not calculate execution stages: {e}")

    stage_map: dict[str, int] = {}
    for stage in execution_stages:
        for sa in stage.parallel_agents:
            stage_map[sa.name] = stage.stage_number

    return execution_stages, stage_map
