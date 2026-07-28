from pathlib import Path
from departments.discovery.tools.linters.discovery_linter.validators.general.user_flows import (
    run_validate_user_flows,
)
import yaml


def _load_valid_entities(dictionary_path: Path) -> set:
    if not dictionary_path.exists():
        return set()
    with open(dictionary_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {e["name"] for e in data.get("entities", []) if "name" in e}


def _load_valid_stories(stories_path: Path) -> set:
    if not stories_path.exists():
        return set()
    with open(stories_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {
        s["id"]
        for s in data.get("stories", [])
        if "id" in s and not s.get("is_standard_crud", False)
    }


def _clean_missing_entities(
    flow_entities: list, valid_entities: set, domain_name: str
) -> list:
    # remove brackets if the agent outputs ['[User]'] instead of ['User']
    clean_entities = [e.replace("[", "").replace("]", "") for e in flow_entities]
    missing = []
    for e in clean_entities:
        if "." in e:
            domain_part, entity_part = e.split(".", 1)
            # Skip validation for cross-domain entities here, as they are not
            # in local dictionary
            if domain_part != domain_name:
                continue
            e = entity_part
        if e not in valid_entities:
            missing.append(e)
    return missing


def _validate_flow_file(
    flow_file: Path, valid_stories: set, valid_entities: set, domain_name: str
) -> set:
    """Validates one flow file and returns its covered job story ids."""
    schema_res = run_validate_user_flows(flow_file)

    flow_stories = schema_res.linked_job_stories
    flow_entities = schema_res.entities

    missing_stories = [s for s in flow_stories if s not in valid_stories]
    missing_entities = [e for e in flow_entities if e not in valid_entities]

    err_msgs = []
    if missing_stories and valid_stories:
        err_msgs.append(
            f"Invalid linked_job_stories: {missing_stories} (Not found in stories.yaml)"
        )
    if missing_entities and valid_entities:
        missing_entities_clean = _clean_missing_entities(
            flow_entities, valid_entities, domain_name
        )
        if missing_entities_clean:
            err_msgs.append(
                f"Invalid entities: {missing_entities_clean} (Not found in manifest.yaml)"
            )

    if err_msgs:
        raise ValueError("; ".join(err_msgs))

    return set(flow_stories)


def run_validate_flows_batch(batch_dir: Path, fix: bool = True):
    errors = []

    if not batch_dir.exists() or not batch_dir.is_dir():
        raise ValueError(f"Directory {batch_dir} does not exist.")

    epic_dir = batch_dir.parent
    domain_dir = epic_dir.parents[1]

    valid_entities = _load_valid_entities(domain_dir / "manifest.yaml")
    valid_stories = _load_valid_stories(epic_dir / "stories.yaml")
    covered_stories = set()

    for flow_file in batch_dir.glob("*.yaml"):
        try:
            covered_stories |= _validate_flow_file(
                flow_file, valid_stories, valid_entities, domain_dir.name
            )
        except Exception as e:
            errors.append(f"{flow_file.name}: {e}")

    if valid_stories:
        uncovered = valid_stories - covered_stories
        if uncovered:
            errors.append(
                f"Incomplete coverage: the following job stories are not covered by any flow in this batch: {sorted(uncovered)}"
            )

    if errors:
        raise ValueError("\n\n---\n\n".join(errors))
    return True
