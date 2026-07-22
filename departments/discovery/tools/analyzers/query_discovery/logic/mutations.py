import yaml
from pathlib import Path
import json
from typing import List, Optional, Any
from departments.discovery.tools.shared.epic_utils import iter_epic_feature_files


def rename_entity(workspace_dir: Path, from_entity: str, to_entity: str) -> list:
    domains_dir = workspace_dir / "discovery" / "domains"
    modified_files: List[Any] = []

    if not domains_dir.exists():
        raise FileNotFoundError(
            f"Workspace has no discovery/domains directory: {domains_dir}"
        )

    for domain_dir in domains_dir.iterdir():
        if not domain_dir.is_dir():
            continue

        dict_file = domain_dir / "dictionary.yaml"
        if dict_file.exists():
            with open(dict_file, "r", encoding="utf-8") as f:
                content = f.read()
            if from_entity in content:
                content = content.replace(from_entity, to_entity)
                modified_files.append((dict_file, content))

        summary_file = domain_dir / "summary.yaml"
        if summary_file.exists():
            with open(summary_file, "r", encoding="utf-8") as f:
                content = f.read()
            if from_entity in content:
                content = content.replace(from_entity, to_entity)
                modified_files.append((summary_file, content))

    if not modified_files:
        raise ValueError(
            f"Entity '{from_entity}' was not found in any dictionary.yaml or "
            f"summary.yaml file under {domains_dir}."
        )

    return modified_files


def _get_files_for_replace_term(domain_dir: Path, scope: str) -> list:
    files = []
    if scope in ("dictionary", "all"):
        files.append(domain_dir / "dictionary.yaml")
    if scope in ("stories", "all"):
        epics_dir = domain_dir / "epics"
        if epics_dir.exists() and epics_dir.is_dir():
            for epic_dir in epics_dir.iterdir():
                if epic_dir.is_dir():
                    files.append(epic_dir / "stories.yaml")
    if scope in ("glossary", "all"):
        files.append(domain_dir / "summary.yaml")
    return files


def replace_term(
    workspace_dir: Path,
    pattern: str,
    replacement: str,
    scope: str,
    domain: Optional[str] = None,
) -> list:
    domains_dir = workspace_dir / "discovery" / "domains"
    modified_files: List[Any] = []

    if not domains_dir.exists():
        raise FileNotFoundError(
            f"Workspace has no discovery/domains directory: {domains_dir}"
        )

    if domain and not (domains_dir / domain).is_dir():
        raise ValueError(f"Domain '{domain}' does not exist under {domains_dir}.")

    for domain_dir in domains_dir.iterdir():
        if not domain_dir.is_dir():
            continue
        if domain and domain_dir.name != domain:
            continue

        files_to_check = _get_files_for_replace_term(domain_dir, scope)

        for f in files_to_check:
            if f.exists():
                with open(f, "r", encoding="utf-8") as file:
                    content = file.read()
                if pattern in content:
                    new_content = content.replace(pattern, replacement)
                    modified_files.append((f, new_content))

    if not modified_files:
        scope_desc = f"domain '{domain}'" if domain else "any domain"
        raise ValueError(
            f"Pattern '{pattern}' was not found (scope={scope!r}) in {scope_desc} "
            f"under {domains_dir}."
        )

    return modified_files


def _apply_set_field(data: dict, keys: list, parsed_value: Any, op: str) -> bool:
    curr = data
    for k in keys[:-1]:
        if k not in curr:
            curr[k] = {}
        curr = curr[k]

    last_key = keys[-1]
    modified = False

    if op == "set":
        curr[last_key] = parsed_value
        modified = True
    elif op == "append":
        if last_key not in curr:
            curr[last_key] = []
        if isinstance(curr[last_key], list):
            curr[last_key].append(parsed_value)
            modified = True
    return modified


def set_field(
    workspace_dir: Path, path: str, value: str, op: str, domain: Optional[str] = None
) -> list:
    domains_dir = workspace_dir / "discovery" / "domains"
    modified_files: List[Any] = []

    if not domains_dir.exists():
        return modified_files

    try:
        parsed_value = json.loads(value)
    except json.JSONDecodeError:
        parsed_value = value

    keys = path.split(".")

    for domain_dir in domains_dir.iterdir():
        if not domain_dir.is_dir():
            continue
        if domain and domain_dir.name != domain:
            continue

        summary_file = domain_dir / "summary.yaml"
        if summary_file.exists():
            with open(summary_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            if _apply_set_field(data, keys, parsed_value, op):
                new_content = yaml.dump(data, allow_unicode=True, sort_keys=False)
                modified_files.append((summary_file, new_content))

    return modified_files


def _move_feature(data: dict, feature_id: str, to_priority: str) -> bool:
    target_feature = None
    buckets = data.get("features", {})

    for _priority_key, features in buckets.items():
        if isinstance(features, list):
            for i, f_item in enumerate(features):
                if f_item.get("id") == feature_id:
                    target_feature = f_item
                    del features[i]
                    break
        if target_feature:
            break

    if target_feature:
        if to_priority not in buckets:
            buckets[to_priority] = []
        buckets[to_priority].append(target_feature)
        return True
    return False


def reclassify_feature(workspace_dir: Path, feature_id: str, to_priority: str) -> list:
    domains_dir = workspace_dir / "discovery" / "domains"
    modified_files: List[Any] = []

    if not domains_dir.exists():
        raise FileNotFoundError(
            f"Workspace has no discovery/domains directory: {domains_dir}"
        )

    for domain_dir in domains_dir.iterdir():
        if not domain_dir.is_dir():
            continue

        for features_file, data in iter_epic_feature_files(domain_dir):
            if _move_feature(data, feature_id, to_priority):
                new_content = yaml.dump(data, allow_unicode=True, sort_keys=False)
                modified_files.append((features_file, new_content))

    if not modified_files:
        raise ValueError(
            f"Feature ID '{feature_id}' was not found in any features file under "
            f"{domains_dir}."
        )

    return modified_files
