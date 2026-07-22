from typing import Dict, Any, List

_ON_REF_PREFIX = "ref:"
_ON_FLOW_PREFIX = "flow:"


def find_dangling_transitions(flow: Dict[str, Any]) -> List[Dict[str, str]]:
    """`ref:<shared_state>` and same-file state targets — checked within this
    one file's own `states`/`shared_states`, since both are declared per-flow.
    `flow:` targets are handled separately by `find_dangling_flow_refs`,
    which needs the cross-file registry built from the whole workspace."""
    states = flow.get("states")
    if not isinstance(states, dict):
        return []
    shared_states = flow.get("shared_states")
    state_names = set(states.keys())
    shared_names = (
        set(shared_states.keys()) if isinstance(shared_states, dict) else set()
    )

    findings = []
    for state_name, state_def in states.items():
        if not isinstance(state_def, dict):
            continue
        on = state_def.get("ON")
        if not isinstance(on, dict):
            continue
        for event, target in on.items():
            if not isinstance(target, str) or target.startswith(_ON_FLOW_PREFIX):
                continue
            if target.startswith(_ON_REF_PREFIX):
                if target[len(_ON_REF_PREFIX) :] not in shared_names:
                    findings.append(
                        {"state": state_name, "event": event, "target": target}
                    )
            elif target not in state_names:
                findings.append({"state": state_name, "event": event, "target": target})
    return findings


def find_dangling_flow_refs(
    flow: Dict[str, Any], registry: Dict[str, List[Dict[str, Any]]]
) -> List[Dict[str, str]]:
    """`flow:<flow_id>` and `flow:<flow_id>#<state>` targets, resolved against
    the global registry — `<flow_id>` must be declared somewhere in the
    workspace, and if a `#<state>` suffix is present, that state must exist in
    at least one of that flow_id's declarations."""
    states = flow.get("states")
    if not isinstance(states, dict):
        return []

    findings = []
    for state_name, state_def in states.items():
        if not isinstance(state_def, dict):
            continue
        on = state_def.get("ON")
        if not isinstance(on, dict):
            continue
        for event, target in on.items():
            if not isinstance(target, str) or not target.startswith(_ON_FLOW_PREFIX):
                continue
            ref = target[len(_ON_FLOW_PREFIX) :]
            target_flow_id, _, target_state = ref.partition("#")
            registrations = registry.get(target_flow_id)
            state_missing = target_state and not any(
                target_state in r["states"] for r in (registrations or [])
            )
            if not registrations or state_missing:
                findings.append({"state": state_name, "event": event, "target": target})
    return findings
