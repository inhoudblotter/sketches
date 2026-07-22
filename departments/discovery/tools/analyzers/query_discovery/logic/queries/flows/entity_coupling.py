from pathlib import Path
from typing import Optional, Dict, Any

from departments.discovery.tools.linters.discovery_linter.validators.tech.entity_graph import (
    ValidateEntityGraphInput,
    run_validate_entity_graph,
)


def get_entity_coupling(workspace_dir: Path) -> Optional[Dict[str, Any]]:
    """Service Coupling Factor across the whole domain tree (discovery-linter
    entity-graph). Cross-domain coupling is inherently a whole-tree metric,
    so unlike the other self-check lists this isn't affected by --domain."""
    domains_dir = workspace_dir / "discovery" / "domains"
    if not domains_dir.is_dir():
        return None
    result = run_validate_entity_graph(
        ValidateEntityGraphInput(domains_dir=domains_dir)
    )
    return {
        "service_coupling_factor": result.service_coupling_factor,
        "is_valid": result.is_valid,
        "latency_risk_path_length": result.latency_risk_path_length,
    }
