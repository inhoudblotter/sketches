from __future__ import annotations

from pathlib import Path

from departments.discovery.tools.analyzers.query_discovery.logic.core import (
    load_domain_snapshot,
)

from .helpers import make_domain


def test_load_domain_snapshot_missing_domains_dir_warns_and_returns_empty(
    tmp_path: Path, capsys
) -> None:
    """Regression: a mistyped/nonexistent workspace path used to render
    identically to "workspace exists but has no domains yet" -- a silent
    empty `{"domains": {}}` with no diagnostic. It must now warn on stderr."""
    idx = load_domain_snapshot(tmp_path / "nonexistent_workspace")

    assert idx == {"domains": {}}
    captured = capsys.readouterr()
    assert "does not exist" in captured.err


def test_load_domain_snapshot_reads_real_domain(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing", entity="Invoice")

    idx = load_domain_snapshot(tmp_path)

    assert "billing" in idx["domains"]
    d = idx["domains"]["billing"]
    assert d["executive_summary"] == "billing summary"
    assert len(d["epics"]) == 1
    assert d["epics"][0]["epic_id"] == "core_epic"
    assert d["epics"][0]["stories"][0]["id"] == "story-01"


def test_load_domain_snapshot_no_warning_when_domains_dir_present(
    tmp_path: Path, capsys
) -> None:
    make_domain(tmp_path, "billing")

    load_domain_snapshot(tmp_path)

    captured = capsys.readouterr()
    assert captured.err == ""
