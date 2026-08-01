from pathlib import Path
from typing import Any, Dict

from ...core import load_domain_snapshot

_DEFAULT_FREQUENCY_CLASS = "interaction"


def get_telemetry_events_global(workspace_dir: Path) -> dict:
    """Aggregates telemetry_events across every flow project-wide. Kept compact
    on purpose: session/interaction events (the bulk, low-volume-per-item) only
    contribute to counts_by_frequency_class; only high_frequency events (the
    ones that actually threaten batching/indexing/retention sizing) are listed
    individually, deduped by event_name — devops-scout needs volume and where
    it comes from, not a per-flow-occurrence catalog."""
    idx = load_domain_snapshot(workspace_dir)

    counts: Dict[str, int] = {}
    high_frequency: Dict[str, Dict[str, Any]] = {}

    for d_name, d_data in idx.get("domains", {}).items():
        for e in d_data.get("epics", []):
            for flow in e.get("flows", []):
                for event in flow.get("telemetry_events", []) or []:
                    freq_class = (
                        event.get("frequency_class") or _DEFAULT_FREQUENCY_CLASS
                    )
                    counts[freq_class] = counts.get(freq_class, 0) + 1

                    if freq_class != "high_frequency":
                        continue
                    event_name = event.get("event_name")
                    if not event_name:
                        continue
                    entry = high_frequency.setdefault(
                        event_name,
                        {"event_name": event_name, "occurrences": 0, "domains": []},
                    )
                    entry["occurrences"] += 1
                    if d_name not in entry["domains"]:
                        entry["domains"].append(d_name)

    return {
        "counts_by_frequency_class": counts,
        "high_frequency_events": list(high_frequency.values()),
    }
