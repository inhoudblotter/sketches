from typing import List, Dict, Any
from ..schemas import BoundedContextsOutput, Context, Dependency, SharedSignal


def _build_dependencies(imports: list) -> Dict[str, Dependency]:
    deps_map: Dict[str, Dependency] = {}
    for imp in imports:
        if not isinstance(imp, dict):
            continue

        target_domain = imp.get("from_domain")
        entity = imp.get("entity")
        reason = imp.get("reason", "")

        if not target_domain or not entity:
            continue

        if target_domain not in deps_map:
            deps_map[target_domain] = Dependency(
                target_domain=target_domain,
                relationship_type="Customer-Supplier",
                data_exchanged=[],
                business_reason="",
            )

        dep = deps_map[target_domain]
        if entity not in dep.data_exchanged:
            dep.data_exchanged.append(entity)
        if reason:
            dep.business_reason = (
                f"{dep.business_reason}; {reason}" if dep.business_reason else reason
            )

    return deps_map


def _build_shared_signals(
    signal_type: str, domains_by_value: Dict[str, set]
) -> List[SharedSignal]:
    return [
        SharedSignal(signal_type=signal_type, value=value, domains=sorted(doms))
        for value, doms in domains_by_value.items()
        if len(doms) > 1
    ]


def extract_contexts(summaries: List[Dict[str, Any]]) -> BoundedContextsOutput:
    contexts_map = {}
    event_to_domains: Dict[str, set] = {}
    constraint_to_domains: Dict[str, set] = {}

    for d in summaries:
        domain_name = d.get("domain")
        if not domain_name:
            continue

        for ev in d.get("events_to_handle", []):
            event_to_domains.setdefault(ev, set()).add(domain_name)
        for c in d.get("business_constraints", []):
            constraint_to_domains.setdefault(c, set()).add(domain_name)

        description = d.get("executive_summary", f"Context for {domain_name}")
        deps_map = _build_dependencies(d.get("imports", []))

        contexts_map[domain_name] = Context(
            domain=domain_name,
            description=description,
            dependencies=list(deps_map.values()),
        )

    shared_signals = _build_shared_signals(
        "event_collision", event_to_domains
    ) + _build_shared_signals("constraint_collision", constraint_to_domains)

    return BoundedContextsOutput(
        contexts=list(contexts_map.values()),
        shared_kernel_signals=sorted(
            shared_signals, key=lambda x: (x.signal_type, x.value)
        ),
    )
