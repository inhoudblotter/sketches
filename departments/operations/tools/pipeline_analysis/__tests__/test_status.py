from __future__ import annotations
from pathlib import Path
import networkx as nx
from departments.operations.tools.pipeline_analysis.engine.validation import (
    status_checker,
)
from .helpers import minimal_agent


def test_status_done(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    out = tmp_path / "out.yaml"
    out.write_text("content")

    agent = minimal_agent("a", reads=[], writes=[str(out)])
    G: nx.DiGraph = nx.DiGraph()
    G.add_node("a", node_type="agent")
    result = status_checker.check_all([agent], G, workspace_dir)
    assert result["a"]["status"] == "DONE"


def test_status_ready(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    inp = tmp_path / "input.yaml"
    inp.write_text("content")

    agent = minimal_agent(
        "a", reads=[str(inp)], writes=[str(tmp_path / "missing_out.yaml")]
    )
    G: nx.DiGraph = nx.DiGraph()
    G.add_node("a", node_type="agent")
    result = status_checker.check_all([agent], G, workspace_dir)
    assert result["a"]["status"] == "READY"


def test_status_blocked(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()

    missing = str(tmp_path / "does_not_exist.yaml")
    agent = minimal_agent("a", reads=[missing], writes=[])
    G: nx.DiGraph = nx.DiGraph()
    G.add_node("a", node_type="agent")
    result = status_checker.check_all([agent], G, workspace_dir)
    assert result["a"]["status"] == "BLOCKED"
    assert any("does_not_exist.yaml" in b for b in result["a"]["blocked_on"])


def test_status_escalated(tmp_path: Path) -> None:
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    handoff = tmp_path / "handoff.md"
    handoff.write_text("escalated")

    agent = minimal_agent("a", reads=[], writes=[], handoff=str(handoff))
    G: nx.DiGraph = nx.DiGraph()
    G.add_node("a", node_type="agent")
    result = status_checker.check_all([agent], G, workspace_dir)
    assert result["a"]["status"] == "ESCALATED"
