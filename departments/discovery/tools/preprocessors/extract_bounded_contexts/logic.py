import yaml
from pathlib import Path
from typing import List, Dict, Any
from .schemas import ExtractBoundedContextsInput, BoundedContextsOutput
from .rules.parser import extract_contexts
from departments.discovery.tools.shared.file_utils import load_yaml


def _collect_epic_requirements(epics_dir: Path) -> tuple[set, set]:
    events: set = set()
    constraints: set = set()
    if not epics_dir.exists():
        return events, constraints

    for epic_dir in epics_dir.iterdir():
        if not epic_dir.is_dir():
            continue
        stories_path = epic_dir / "stories.yaml"
        if not stories_path.exists():
            continue
        s_data = load_yaml(stories_path) or {}
        reqs = s_data.get("epic_requirements", {})
        events.update(reqs.get("events_to_handle", []))
        constraints.update(reqs.get("business_constraints", []))

    return events, constraints


def load_domain_data(domains_dir: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    base_path = Path(domains_dir)
    if not base_path.exists():
        return results

    for domain_dir in base_path.iterdir():
        if not domain_dir.is_dir():
            continue

        summary_path = domain_dir / "summary.yaml"
        if not summary_path.exists():
            continue

        data = load_yaml(summary_path) or {}
        if not data.get("domain"):
            data["domain"] = domain_dir.name

        events, constraints = _collect_epic_requirements(domain_dir / "epics")
        data["events_to_handle"] = list(events)
        data["business_constraints"] = list(constraints)
        results.append(data)

    return results


def execute(input_data: ExtractBoundedContextsInput) -> BoundedContextsOutput:
    summaries = load_domain_data(input_data.domains_dir)
    output = extract_contexts(summaries)

    out_path = Path(input_data.output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            output.model_dump(mode="json"), f, allow_unicode=True, sort_keys=False
        )

    return output
