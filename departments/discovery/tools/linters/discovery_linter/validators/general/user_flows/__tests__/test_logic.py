import pytest

from ...user_flows import run_validate_user_flows


def _write_flow(tmp_path, states, shared_states=None):
    import yaml

    data = {
        "author_agent": "test",
        "flow_id": "test_flow",
        "domain": "test_domain",
        "platforms": ["web"],
        "intent": "test",
        "linked_job_stories": [],
        "shared_states": shared_states or {},
        "states": states,
    }
    path = tmp_path / "flow.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_transitions_to_declared_states_pass(tmp_path):
    states = {
        "start": {"ON": {"go": "end"}},
        "end": {},
    }
    schema = run_validate_user_flows(_write_flow(tmp_path, states))
    assert schema.flow_id == "test_flow"


def test_transition_to_undeclared_state_is_flagged(tmp_path):
    states = {"start": {"ON": {"go": "nonexistent_state"}}}
    path = _write_flow(tmp_path, states)
    with pytest.raises(ValueError, match="undeclared state 'nonexistent_state'"):
        run_validate_user_flows(path)


def test_ref_to_declared_shared_state_passes(tmp_path):
    states = {"start": {"ON": {"fail": "ref:sys_error"}}}
    shared_states = {"sys_error": {"Recovery": "retry"}}
    schema = run_validate_user_flows(_write_flow(tmp_path, states, shared_states))
    assert schema.shared_states["sys_error"].Recovery == "retry"


def test_ref_to_undeclared_shared_state_is_flagged(tmp_path):
    states = {"start": {"ON": {"fail": "ref:sys_error"}}}
    path = _write_flow(tmp_path, states)
    with pytest.raises(ValueError, match="undeclared shared state 'ref:sys_error'"):
        run_validate_user_flows(path)


def test_flow_prefixed_target_is_not_validated(tmp_path):
    # Cross-file handoff — flows-batch's job, not this per-file check.
    states = {"start": {"ON": {"handoff": "flow:some_other_flow"}}}
    schema = run_validate_user_flows(_write_flow(tmp_path, states))
    assert schema.states["start"].ON["handoff"] == "flow:some_other_flow"
