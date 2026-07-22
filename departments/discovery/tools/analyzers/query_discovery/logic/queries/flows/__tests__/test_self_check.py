from __future__ import annotations

import yaml
from pathlib import Path

from departments.discovery.tools.analyzers.query_discovery.logic.queries.flows import (
    get_flows_self_check,
)

from ....__tests__.helpers import make_domain, write_yaml


def _add_epic(workspace: Path, domain: str, epic_id: str) -> None:
    """A second, minimal epic in an already-`make_domain`'d domain — appends
    to summary.yaml's `epics:` list, since that's what load_domain_snapshot
    walks (a flow file with no summary.yaml entry for its epic is invisible)."""
    summary_path = workspace / "discovery" / "domains" / domain / "summary.yaml"
    data = yaml.safe_load(summary_path.read_text(encoding="utf-8"))
    data["epics"].append(
        {"epic_id": epic_id, "focus": f"{epic_id} focus", "is_standard_crud": False}
    )
    write_yaml(summary_path, data)


def _write_flow(
    workspace: Path,
    domain: str,
    epic_id: str,
    flow_id: str,
    states: dict,
    shared_states=None,
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
            "linked_job_stories": ["story-01"],
            "shared_states": shared_states or {},
            "states": states,
        },
    )


def test_no_dangling_transitions_for_well_formed_flow(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing")
    _write_flow(
        tmp_path,
        "billing",
        "core_epic",
        "flow_a",
        states={"start": {"ON": {"go": "end"}}, "end": {}},
    )

    result = get_flows_self_check(tmp_path)

    assert result["dangling_transitions"] == []


def test_transition_to_undeclared_state_is_reported(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing")
    _write_flow(
        tmp_path,
        "billing",
        "core_epic",
        "flow_a",
        states={"start": {"ON": {"go": "nonexistent_state"}}},
    )

    result = get_flows_self_check(tmp_path)

    assert result["dangling_transitions"] == [
        {
            "domain": "billing",
            "epic": "core_epic",
            "flow": "flow_a",
            "state": "start",
            "event": "go",
            "target": "nonexistent_state",
        }
    ]


def test_ref_to_undeclared_shared_state_is_reported(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing")
    _write_flow(
        tmp_path,
        "billing",
        "core_epic",
        "flow_a",
        states={"start": {"ON": {"fail": "ref:sys_error"}}},
    )

    result = get_flows_self_check(tmp_path)

    assert len(result["dangling_transitions"]) == 1
    assert result["dangling_transitions"][0]["target"] == "ref:sys_error"


def test_flow_prefixed_target_is_not_in_dangling_transitions(tmp_path: Path) -> None:
    # flow: targets are checked separately, in dangling_flow_refs (below) —
    # they must never also show up here.
    make_domain(tmp_path, "billing")
    _write_flow(
        tmp_path,
        "billing",
        "core_epic",
        "flow_a",
        states={"start": {"ON": {"handoff": "flow:other_flow"}}},
    )

    result = get_flows_self_check(tmp_path)

    assert result["dangling_transitions"] == []


def test_flow_ref_to_nonexistent_flow_id_is_reported(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing")
    _write_flow(
        tmp_path,
        "billing",
        "core_epic",
        "flow_a",
        states={"start": {"ON": {"handoff": "flow:nonexistent_flow"}}},
    )

    result = get_flows_self_check(tmp_path)

    assert result["dangling_flow_refs"] == [
        {
            "domain": "billing",
            "epic": "core_epic",
            "flow": "flow_a",
            "state": "start",
            "event": "handoff",
            "target": "flow:nonexistent_flow",
        }
    ]


def test_flow_ref_to_existing_flow_id_is_not_reported(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing")
    _write_flow(
        tmp_path,
        "billing",
        "core_epic",
        "flow_a",
        states={"start": {"ON": {"handoff": "flow:flow_b"}}},
    )
    _write_flow(tmp_path, "billing", "core_epic", "flow_b", states={"entry": {}})

    result = get_flows_self_check(tmp_path)

    assert result["dangling_flow_refs"] == []


def test_flow_ref_can_cross_epics_in_the_same_domain(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing", epic_id="epic_a")
    _add_epic(tmp_path, "billing", "epic_b")
    _write_flow(
        tmp_path,
        "billing",
        "epic_a",
        "flow_a",
        states={"start": {"ON": {"handoff": "flow:flow_b"}}},
    )
    _write_flow(tmp_path, "billing", "epic_b", "flow_b", states={"entry": {}})

    result = get_flows_self_check(tmp_path)

    assert result["dangling_flow_refs"] == []


def test_flow_ref_with_state_fragment_checks_target_state_exists(
    tmp_path: Path,
) -> None:
    make_domain(tmp_path, "billing")
    _write_flow(
        tmp_path,
        "billing",
        "core_epic",
        "flow_a",
        states={"start": {"ON": {"handoff": "flow:flow_b#missing_state"}}},
    )
    _write_flow(tmp_path, "billing", "core_epic", "flow_b", states={"entry": {}})

    result = get_flows_self_check(tmp_path)

    assert result["dangling_flow_refs"] == [
        {
            "domain": "billing",
            "epic": "core_epic",
            "flow": "flow_a",
            "state": "start",
            "event": "handoff",
            "target": "flow:flow_b#missing_state",
        }
    ]


def test_flow_ref_with_valid_state_fragment_is_not_reported(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing")
    _write_flow(
        tmp_path,
        "billing",
        "core_epic",
        "flow_a",
        states={"start": {"ON": {"handoff": "flow:flow_b#entry"}}},
    )
    _write_flow(tmp_path, "billing", "core_epic", "flow_b", states={"entry": {}})

    result = get_flows_self_check(tmp_path)

    assert result["dangling_flow_refs"] == []


def test_duplicate_flow_id_across_files_is_reported(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing", epic_id="epic_a")
    _add_epic(tmp_path, "billing", "epic_b")
    _write_flow(tmp_path, "billing", "epic_a", "shared_name", states={"a": {}})
    _write_flow(tmp_path, "billing", "epic_b", "shared_name", states={"b": {}})

    result = get_flows_self_check(tmp_path)

    assert len(result["duplicate_flow_ids"]) == 1
    dup = result["duplicate_flow_ids"][0]
    assert dup["flow_id"] == "shared_name"
    assert {loc["epic"] for loc in dup["locations"]} == {"epic_a", "epic_b"}


def test_no_duplicate_flow_ids_when_unique(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing")
    _write_flow(tmp_path, "billing", "core_epic", "flow_a", states={"a": {}})

    result = get_flows_self_check(tmp_path)

    assert result["duplicate_flow_ids"] == []


def test_entity_coupling_present_for_real_workspace_tree(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing")

    result = get_flows_self_check(tmp_path)

    assert result["entity_coupling"] is not None
    assert "service_coupling_factor" in result["entity_coupling"]


def test_entity_coupling_none_when_no_domains_dir(tmp_path: Path) -> None:
    result = get_flows_self_check(tmp_path)

    assert result["entity_coupling"] is None
