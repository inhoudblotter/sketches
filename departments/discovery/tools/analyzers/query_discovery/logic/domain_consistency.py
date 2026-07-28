from pathlib import Path
from typing import Any, Dict

from .boundary import check_boundaries
from .persona_consistency import check_persona_consistency


def check_domain_consistency(workspace_dir: Path) -> dict:
    """Compact combined read over the domain tree, for the two consistency
    issues that are judgment calls rather than hard linter failures:

    - duplicate_entities: the same entity name declared by more than one
      domain's manifest.yaml (Boundary Enforcement — likely needs merging via
      MUTATION PROTOCOL, but not always: could be a legitimate namesake).
    - orphaned_personas: a persona/machine_persona from target_audience.yaml
      never referenced by any domain's personas_in_scope (could be a
      deliberate scope decision, or forgotten coverage).

    Referential integrity within a single manifest.yaml (unknown persona ids,
    dangling owning_actor, operational_actors drift against
    domains_manifest.yaml) is NOT re-checked here — that's a hard gate
    enforced by the `domain-manifest` linter itself at write time, with no
    legitimate reason to fail, so it doesn't belong in an advisory read.
    """
    domains_dir = workspace_dir / "discovery" / "domains"
    result: Dict[str, Any] = {}

    boundary = check_boundaries(domains_dir)
    if boundary:
        result["duplicate_entities"] = boundary

    orphaned = check_persona_consistency(workspace_dir).get("orphaned_personas", [])
    if orphaned:
        result["orphaned_personas"] = orphaned

    return result
