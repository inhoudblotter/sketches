from __future__ import annotations

from pathlib import Path

from departments.discovery.tools.analyzers.query_discovery.logic.queries.flows import (
    get_flows_self_check_summary,
)

from ....__tests__.helpers import make_domain, write_yaml


def _write_flow(
    workspace: Path, domain: str, epic_id: str, flow_id: str, states: dict
) -> None:
    write_yaml(
        workspace
        / "discovery"
        / "domains"
        / domain
        / "epics"
        / epic_id
        / "flows"
        / f"{flow_id}.yaml",
        {
            "flow_id": flow_id,
            "linked_job_stories": [],
            "shared_states": {},
            "states": states,
        },
    )


def test_summary_reports_counts_not_findings(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing")
    _write_flow(
        tmp_path,
        "billing",
        "core_epic",
        "flow_a",
        states={
            "start": {"ON": {"go": "nonexistent_state", "handoff": "flow:missing_flow"}}
        },
    )

    summary = get_flows_self_check_summary(tmp_path)

    assert summary["dangling_transitions"] == 1
    assert summary["dangling_flow_refs"] == 1
    assert "entity_coupling_is_valid" in summary
    # Counts only — no per-finding detail (state/event/target dicts) leaks through.
    assert all(isinstance(v, (int, bool)) or v is None for v in summary.values())


def test_summary_entity_coupling_is_valid_none_when_no_domains_dir(
    tmp_path: Path,
) -> None:
    summary = get_flows_self_check_summary(tmp_path)

    assert summary["entity_coupling_is_valid"] is None
