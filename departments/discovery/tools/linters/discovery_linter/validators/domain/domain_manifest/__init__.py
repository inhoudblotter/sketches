from departments.discovery.tools.linters.discovery_linter.validators.shared.validation_utils import (
    validate_yaml_file,
)
from departments.discovery.tools.linters.discovery_linter.validators.shared.io import (
    load_yaml,
)
from pydantic import BaseModel, Field, model_validator
from typing import List, Literal, Optional
from pathlib import Path
import yaml

from .rules.validators import validate_banned_words, validate_no_shared_context


class Coverage(BaseModel):
    mode: str
    by: Optional[str] = None
    justification: str


class OperationalActor(BaseModel):
    id: str
    name: str
    responsibilities: List[str]
    jtbd_motivations: List[str]
    coverage: Coverage


class PersonaInScope(BaseModel):
    id: str
    type: Literal["human", "machine"]
    pain_summary: str
    machine_type: Optional[Literal["ai_agent", "software_client", "iot_device"]] = None
    owning_actor: Optional[str] = None
    physical_constraints: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_machine_fields(self) -> "PersonaInScope":
        if self.type == "machine":
            if not self.machine_type:
                raise ValueError(
                    f"personas_in_scope '{self.id}': type=machine требует machine_type"
                )
            if not self.owning_actor:
                raise ValueError(
                    f"personas_in_scope '{self.id}': type=machine требует owning_actor"
                )
        return self


class Attribute(BaseModel):
    name: str
    semantic_type: str
    description: str
    is_required: bool = True


class Relationship(BaseModel):
    type: str
    target: str
    description: str


class Entity(BaseModel):
    name: str
    description: str
    type: str
    attributes: List[Attribute]
    relationships: List[Relationship] = []


class GlossaryItem(BaseModel):
    term: str
    definition: str


class DomainManifestSchema(BaseModel):
    domain: str
    personas_in_scope: List[PersonaInScope] = []
    platforms: List[str] = []
    operational_actors: List[OperationalActor] = []
    entities: List[Entity]
    glossary: List[GlossaryItem] = []


def _resolve_workspace_dir(manifest_file: Path) -> Path:
    # manifest_file: workspace/discovery/domains/{domain}/manifest.yaml
    return manifest_file.parent.parent.parent.parent


def _known_target_audience_ids(workspace_dir: Path) -> tuple[set[str], set[str]]:
    """Returns (all_ids, machine_ids) from target_audience.yaml, or ({}, {}) if
    the file is missing/unreadable — cross-checks are skipped, not failed, in
    that case (e.g. isolated unit-test fixtures without a full workspace)."""
    ta = load_yaml(workspace_dir / "discovery" / "strategy" / "target_audience.yaml")
    if not ta:
        return set(), set()
    all_ids = {
        p["id"]
        for p in ta.get("personas", []) or []
        if isinstance(p, dict) and p.get("id")
    }
    machine_ids = {
        m["id"]
        for m in ta.get("machine_personas", []) or []
        if isinstance(m, dict) and m.get("id")
    }
    all_ids |= machine_ids
    return all_ids, machine_ids


def _canonical_operational_actors(
    workspace_dir: Path, domain: str
) -> Optional[dict[str, Optional[str]]]:
    """Returns {actor_id: coverage.mode} from domains_manifest.yaml for this
    domain, or None if the file/domain entry is missing (skip the check)."""
    dm = load_yaml(workspace_dir / "discovery" / "meta" / "domains_manifest.yaml")
    if not dm:
        return None
    for d in dm.get("domains", []) or []:
        if isinstance(d, dict) and d.get("id") == domain:
            return {
                oa["id"]: (oa.get("coverage") or {}).get("mode")
                for oa in d.get("operational_actors", []) or []
                if isinstance(oa, dict) and oa.get("id")
            }
    return None


def _validate_persona_consistency(
    model: DomainManifestSchema, workspace_dir: Path
) -> List[str]:
    """Hard cross-file checks against target_audience.yaml and
    domains_manifest.yaml — no legitimate reason for these to fail, unlike
    orphaned-persona coverage (a judgment call left to `query-discovery
    persona-consistency`, not this linter)."""
    errors: List[str] = []

    known_ids, machine_ids = _known_target_audience_ids(workspace_dir)
    local_ids = {p.id for p in model.personas_in_scope} | {
        a.id for a in model.operational_actors
    }

    if known_ids:
        for persona in model.personas_in_scope:
            if persona.id not in known_ids:
                errors.append(
                    f"personas_in_scope '{persona.id}': не найден в target_audience.yaml "
                    "(personas/machine_personas) — опечатка или выдуманный id"
                )
            is_machine = persona.type == "machine" or persona.id in machine_ids
            if is_machine and (
                not persona.owning_actor or persona.owning_actor not in local_ids
            ):
                errors.append(
                    f"personas_in_scope '{persona.id}': owning_actor '{persona.owning_actor}' "
                    "не резолвится в personas_in_scope/operational_actors этого же manifest.yaml"
                )

    canonical = _canonical_operational_actors(workspace_dir, model.domain)
    if canonical:
        local = {a.id: a.coverage.mode for a in model.operational_actors}
        missing_ids = sorted(set(canonical) - set(local))
        extra_ids = sorted(set(local) - set(canonical))
        mode_mismatches = sorted(
            aid for aid in set(canonical) & set(local) if canonical[aid] != local[aid]
        )
        if missing_ids:
            errors.append(
                f"operational_actors: отсутствуют id из domains_manifest.yaml: {missing_ids}"
            )
        if extra_ids:
            errors.append(
                f"operational_actors: id, которых нет в domains_manifest.yaml: {extra_ids}"
            )
        if mode_mismatches:
            errors.append(
                f"operational_actors: coverage.mode разошёлся с domains_manifest.yaml: {mode_mismatches}"
            )

    return errors


def run_validation(file_path: Path) -> DomainManifestSchema:
    model = validate_yaml_file(file_path, DomainManifestSchema)

    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    validate_no_shared_context(file_path, data)
    validate_banned_words(data)

    consistency_errors = _validate_persona_consistency(
        model, _resolve_workspace_dir(file_path)
    )
    if consistency_errors:
        raise ValueError("\n".join(consistency_errors))

    return model
