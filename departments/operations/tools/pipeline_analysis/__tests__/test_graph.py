from __future__ import annotations
from pathlib import Path
from departments.operations.tools.shared import agent_parser
from departments.operations.tools.pipeline_analysis.engine.graph import graph_builder
from departments.operations.tools.pipeline_analysis.engine.validation import (
    status_checker,
)
from departments.operations.tools.pipeline_analysis.engine.core import (
    metrics as metrics_module,
)
from .helpers import make_agent_md


def test_graph_node_types(tmp_path: Path) -> None:
    agents_dir = tmp_path / "staff"
    agents_dir.mkdir()
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()

    make_agent_md(
        agents_dir / "agent-a.md",
        name="agent-a",
        outputs="- workspace/out.yaml",
    )
    raw = agent_parser.parse_all(agents_dir)
    G = graph_builder.build(raw, workspace_dir)

    for n, d in G.nodes(data=True):
        if n == "agent-a":
            assert d["node_type"] == "agent"
        else:
            assert d["node_type"] == "artifact"


def test_orphaned_artifact(tmp_path: Path) -> None:
    agents_dir = tmp_path / "staff"
    agents_dir.mkdir()
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()

    # Agent writes artifact but nobody reads it
    make_agent_md(
        agents_dir / "agent-a.md",
        name="agent-a",
        outputs="- workspace/orphan.yaml",
    )
    raw = agent_parser.parse_all(agents_dir)
    G = graph_builder.build(raw, workspace_dir)
    statuses = status_checker.check_all(raw, G, workspace_dir)
    m = metrics_module.compute(G, statuses, raw, workspace_dir)

    assert any("orphan.yaml" in a for a in m.orphaned_artifacts)


def test_missing_input(tmp_path: Path) -> None:
    agents_dir = tmp_path / "staff"
    agents_dir.mkdir()
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()

    # Agent reads a file that does NOT exist on disk
    make_agent_md(
        agents_dir / "agent-a.md",
        name="agent-a",
        inputs="- workspace/nonexistent.yaml",
        outputs="- workspace/out.yaml",
    )
    raw = agent_parser.parse_all(agents_dir)
    G = graph_builder.build(raw, workspace_dir)
    statuses = status_checker.check_all(raw, G, workspace_dir)
    m = metrics_module.compute(G, statuses, raw, workspace_dir)

    assert any("nonexistent.yaml" in mi for mi in m.missing_inputs)
