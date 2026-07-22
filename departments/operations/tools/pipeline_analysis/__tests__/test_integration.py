from __future__ import annotations
from pathlib import Path
import networkx as nx
from departments.operations.tools.shared import agent_parser
from departments.operations.tools.pipeline_analysis.engine.graph import graph_builder
from departments.operations.tools.pipeline_analysis.engine.validation import (
    status_checker,
)
from departments.operations.tools.pipeline_analysis.engine.core import (
    metrics as metrics_module,
)
from departments.operations.tools.pipeline_analysis import logic
from departments.operations.tools.pipeline_analysis.schemas import ReportData
from .helpers import make_agent_md

EXPECTED_AGENT_COUNT = 2


def test_html_render(tmp_path: Path) -> None:
    """logic.run() returns ReportData with correct agent count."""
    agents_dir = tmp_path / "staff"
    agents_dir.mkdir()
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()

    make_agent_md(agents_dir / "a.md", name="agent-a")
    make_agent_md(agents_dir / "b.md", name="agent-b")

    result = logic.run(agents_dir, workspace_dir)

    assert isinstance(result, ReportData)
    assert len(result.agents) == EXPECTED_AGENT_COUNT
    names = {a.name for a in result.agents}
    assert "agent-a" in names
    assert "agent-b" in names


def test_agent_description_propagates_to_report(tmp_path: Path) -> None:
    """The frontmatter `description:` field must survive parse → graph → AgentNode,
    since the workflow.md.j2 template uses it as the per-agent summary."""
    agents_dir = tmp_path / "staff"
    agents_dir.mkdir()
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()

    make_agent_md(agents_dir / "a.md", name="agent-a", description="Does the thing.")

    result = logic.run(agents_dir, workspace_dir)
    agent = next(a for a in result.agents if a.name == "agent-a")
    assert agent.description == "Does the thing."


def test_cycle_detection() -> None:
    G: nx.DiGraph = nx.DiGraph()
    G.add_edges_from([("A", "B"), ("B", "C"), ("C", "A")])
    assert not nx.is_directed_acyclic_graph(G)


def test_subagent_refine_loop_is_not_a_cycle(tmp_path: Path) -> None:
    """An orchestrator that hands a subagent a feedback file, then reads the
    subagent's redone draft, forms agent -> feedback.md -> subagent ->
    draft.yaml -> agent in the raw artifact graph. Subagent calls are
    synchronous (call, wait, return) so this is a bounded refine loop, not a
    scheduling cycle, and must not trip has_cycles."""
    agents_dir = tmp_path / "staff"
    agents_dir.mkdir()
    subagents_dir = agents_dir / "subagents"
    subagents_dir.mkdir()
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()

    make_agent_md(
        agents_dir / "orchestrator.md",
        name="orchestrator",
        outputs="- workspace/feedback.md",
        inputs="- workspace/draft.yaml",
        workflow='<call_agent name="scout">',
    )
    make_agent_md(
        subagents_dir / "scout.md",
        name="scout",
        inputs="- workspace/feedback.md",
        outputs="- workspace/draft.yaml",
    )

    raw = agent_parser.parse_all(agents_dir)
    G = graph_builder.build(raw, workspace_dir)
    statuses = status_checker.check_all(raw, G, workspace_dir)
    m = metrics_module.compute(G, statuses, raw, workspace_dir)

    assert not nx.is_directed_acyclic_graph(
        G
    ), "fixture should reproduce the raw-graph cycle"
    assert m.has_cycles is False
