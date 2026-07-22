from typing import Dict, Any, List


def build_flow_registry(idx: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """flow_id -> every {domain, epic, states} that declares it, built from
    the full snapshot regardless of --domain — a `flow:` target resolves by
    bare flow_id with no domain/epic qualifier, so it can legitimately point
    at another epic (even another domain), and detecting a same-flow_id
    collision needs visibility across all of them, not just the ones the
    caller happens to be filtering to."""
    registry: Dict[str, List[Dict[str, Any]]] = {}
    for d_name, d_data in idx.get("domains", {}).items():
        for e in d_data.get("epics", []):
            epic_id = e.get("epic_id")
            for flow in e.get("flows", []):
                flow_id = flow.get("flow_id")
                if not flow_id:
                    continue
                states = flow.get("states")
                registry.setdefault(flow_id, []).append(
                    {
                        "domain": d_name,
                        "epic": epic_id,
                        "states": (
                            set(states.keys()) if isinstance(states, dict) else set()
                        ),
                    }
                )
    return registry


def find_duplicate_flow_ids(
    registry: Dict[str, List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """flow_id values declared by more than one file — a `flow:<flow_id>`
    target resolves by bare flow_id, so a collision makes that resolution
    ambiguous even though nothing else about either file is wrong."""
    return [
        {
            "flow_id": flow_id,
            "locations": [
                {"domain": r["domain"], "epic": r["epic"]} for r in registrations
            ],
        }
        for flow_id, registrations in registry.items()
        if len(registrations) > 1
    ]
