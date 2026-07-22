from __future__ import annotations
from pathlib import Path
import networkx as nx
import pytest
from departments.operations.tools.shared import agent_parser
from departments.operations.tools.pipeline_analysis.engine.graph import graph_builder
from departments.operations.tools.pipeline_analysis.engine.validation import (
    status_checker,
)
from departments.operations.tools.pipeline_analysis.engine.core import (
    metrics as metrics_module,
)
from .helpers import make_agent_md, minimal_agent

TOTAL_AGENTS = 8
DONE_AGENTS = 4
EXPECTED_COMPLETION_PCT = 50.0


def test_parallelism_groups(tmp_path: Path) -> None:
    """Two agents with no shared artifacts → same parallelism layer."""
    agents_dir = tmp_path / "staff"
    agents_dir.mkdir()
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()

    make_agent_md(agents_dir / "a.md", name="agent-a", outputs="- workspace/a.yaml")
    make_agent_md(agents_dir / "b.md", name="agent-b", outputs="- workspace/b.yaml")

    raw = agent_parser.parse_all(agents_dir)
    G = graph_builder.build(raw, workspace_dir)
    statuses = status_checker.check_all(raw, G, workspace_dir)
    m = metrics_module.compute(G, statuses, raw, workspace_dir)

    all_agents_in_groups = [a for group in m.parallelism_groups for a in group]
    assert "agent-a" in all_agents_in_groups
    assert "agent-b" in all_agents_in_groups

    group_of_a = next(i for i, g in enumerate(m.parallelism_groups) if "agent-a" in g)
    group_of_b = next(i for i, g in enumerate(m.parallelism_groups) if "agent-b" in g)
    assert group_of_a == group_of_b


def test_critical_path(tmp_path: Path) -> None:
    """Chain A→artifact→B→artifact2→C produces critical path [A, B, C]."""
    agents_dir = tmp_path / "staff"
    agents_dir.mkdir()
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()

    make_agent_md(
        agents_dir / "a.md",
        name="agent-a",
        outputs="- workspace/ab.yaml",
    )
    make_agent_md(
        agents_dir / "b.md",
        name="agent-b",
        inputs="- workspace/ab.yaml",
        outputs="- workspace/bc.yaml",
    )
    make_agent_md(
        agents_dir / "c.md",
        name="agent-c",
        inputs="- workspace/bc.yaml",
    )

    raw = agent_parser.parse_all(agents_dir)
    G = graph_builder.build(raw, workspace_dir)
    statuses = status_checker.check_all(raw, G, workspace_dir)
    m = metrics_module.compute(G, statuses, raw, workspace_dir)

    assert "agent-a" in m.critical_path
    assert "agent-b" in m.critical_path
    assert "agent-c" in m.critical_path
    # Correct order
    assert m.critical_path.index("agent-a") < m.critical_path.index("agent-b")
    assert m.critical_path.index("agent-b") < m.critical_path.index("agent-c")


def test_completion_pct(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()

    agents = []
    for i in range(TOTAL_AGENTS):
        out = tmp_path / f"out_{i}.yaml"
        if i < DONE_AGENTS:
            out.write_text("done")
        agents.append(minimal_agent(f"agent-{i}", reads=[], writes=[str(out)]))

    G: nx.DiGraph = nx.DiGraph()
    for a in agents:
        G.add_node(a["name"], node_type="agent")

    statuses = status_checker.check_all(agents, G, workspace_dir)
    m = metrics_module.compute(G, statuses, agents, workspace_dir)

    assert m.completion_pct == pytest.approx(EXPECTED_COMPLETION_PCT)
