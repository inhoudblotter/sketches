from pathlib import Path
from typing import Dict, List, Set

from departments.discovery.tools.linters.discovery_linter.validators.shared.io import (
    load_yaml,
)
from departments.discovery.tools.linters.discovery_linter.validators.general.workspace.models import (
    CrossDomainIssue,
)
from departments.discovery.tools.shared.epic_utils import (
    iter_domain_dirs,
    iter_epic_dirs,
)


def build_domain_index(domains_dir: Path) -> Dict[str, dict]:
    """
    Returns {domain_name: {entities: Set[str], exports: Set[str]}}
    """
    index: Dict[str, dict] = {}

    for domain_dir in iter_domain_dirs(domains_dir):
        name = domain_dir.name

        entities: Set[str] = set()
        dict_data = load_yaml(domain_dir / "dictionary.yaml")
        if dict_data:
            for entity in dict_data.get("entities", []):
                if isinstance(entity, dict) and entity.get("name"):
                    entities.add(entity["name"])

        exported: Set[str] = set()
        summary_data = load_yaml(domain_dir / "summary.yaml")
        if summary_data:
            for exp in summary_data.get("exports") or []:
                if isinstance(exp, dict) and exp.get("entity"):
                    exported.add(exp["entity"])

        index[name] = {"entities": entities, "exports": exported}

    return index


def _check_import(
    consumer: str, imp: dict, index: Dict[str, dict]
) -> CrossDomainIssue | None:
    if not isinstance(imp, dict):
        return None
    from_domain = imp.get("from_domain", "")
    entity = imp.get("entity", "")
    if not from_domain or not entity:
        return None

    if from_domain not in index:
        return CrossDomainIssue(consumer, from_domain, entity, "domain_not_found")

    domain_info = index[from_domain]
    if entity not in domain_info["entities"]:
        return CrossDomainIssue(
            consumer, from_domain, entity, "entity_not_in_dictionary"
        )

    if entity not in domain_info["exports"]:
        return CrossDomainIssue(consumer, from_domain, entity, "entity_not_exported")

    return None


def check_cross_domain_refs(
    domains_dir: Path, index: Dict[str, dict]
) -> List[CrossDomainIssue]:
    issues: List[CrossDomainIssue] = []

    for domain_dir in iter_domain_dirs(domains_dir):
        consumer = domain_dir.name
        summary_data = load_yaml(domain_dir / "summary.yaml")
        if not summary_data:
            continue

        for imp in summary_data.get("imports") or []:
            issue = _check_import(consumer, imp, index)
            if issue:
                issues.append(issue)

    return issues


def _get_allowed_platforms(workspace_dir: Path) -> set:
    platform_file = workspace_dir / "discovery" / "strategy" / "platform_strategy.yaml"
    if not platform_file.exists():
        return set()  # strategy linter handles missing files

    p_data = load_yaml(platform_file)
    if not p_data:
        return set()

    return {
        p["id"]
        for p in p_data.get("platforms", [])
        if isinstance(p, dict) and p.get("id")
    }


def _check_domain_summary_platforms(
    domain_dir: Path, allowed_platforms: set
) -> List[str]:
    errors: List[str] = []
    summary_data = load_yaml(domain_dir / "summary.yaml")
    if not (summary_data and "target_platforms" in summary_data):
        return errors
    for p in summary_data["target_platforms"]:
        if p not in allowed_platforms:
            errors.append(
                f"Domain '{domain_dir.name}' summary.yaml uses unauthorized platform: '{p}'. Allowed: {list(allowed_platforms)}"
            )
    return errors


def _check_domain_flow_platforms(domain_dir: Path, allowed_platforms: set) -> List[str]:
    errors = []

    for epic_dir in iter_epic_dirs(domain_dir):
        flows_dir = epic_dir / "flows"
        if not flows_dir.is_dir():
            continue
        for flow_file in flows_dir.glob("*.yaml"):
            f_data = load_yaml(flow_file)
            if not (f_data and "platforms" in f_data):
                continue
            for p in f_data["platforms"]:
                if p not in allowed_platforms:
                    errors.append(
                        f"Flow '{epic_dir.name}/{flow_file.name}' uses unauthorized platform: '{p}'. Allowed: {list(allowed_platforms)}"
                    )
    return errors


def check_platforms(workspace_dir: Path, domains_dir: Path) -> List[str]:
    allowed_platforms = _get_allowed_platforms(workspace_dir)
    if not allowed_platforms or not domains_dir.is_dir():
        return []

    errors: list = []
    for domain_dir in iter_domain_dirs(domains_dir):
        errors.extend(_check_domain_summary_platforms(domain_dir, allowed_platforms))
        errors.extend(_check_domain_flow_platforms(domain_dir, allowed_platforms))

    return errors
