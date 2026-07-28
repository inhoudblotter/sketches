from pathlib import Path
from ...utils.common import load_strategy_yaml
from departments.discovery.tools.shared.text_utils import clean_links, clean_list

# MAGIC NUMBERS FIX: PLR2004
TOP_PERSONAS_COUNT = 4


def build_actors(discovery_dir: Path) -> dict | None:
    """External personas/machine_personas (target_audience.yaml) + operational
    actors per domain (meta/domains_manifest.yaml, canonical registry), plus
    optional headcount type (operations_team.yaml) — for the pitch deck's Actors
    slide, placed right after Market & Competition (who we serve, concretely).
    """
    audience_path = discovery_dir / "strategy" / "target_audience.yaml"
    manifest_path = discovery_dir / "meta" / "domains_manifest.yaml"
    if not audience_path.exists() and not manifest_path.exists():
        return None

    audience_data = load_strategy_yaml(audience_path)
    personas = [
        {
            "name": clean_links(str(p.get("name", p.get("id", "Unknown")))),
            "pain_points": clean_list(p.get("pain_points", [])),
            "magnet_features": clean_list(p.get("magnet_features", [])),
        }
        for p in (audience_data.get("personas") or [])[:TOP_PERSONAS_COUNT]
    ]
    machine_personas = [
        {
            "name": clean_links(str(mp.get("name", mp.get("id", "Unknown")))),
            "machine_type": mp.get("machine_type", ""),
            "owning_actor": mp.get("owning_actor", ""),
        }
        for mp in (audience_data.get("machine_personas") or [])
    ]

    manifest_data = load_strategy_yaml(manifest_path)
    domains = manifest_data.get("domains") or []
    operational_actors = []
    zero_admin_domains_count = 0
    coverage_mode_breakdown: dict = {}
    for d in domains:
        actors = d.get("operational_actors") or []
        if not actors:
            zero_admin_domains_count += 1
            continue
        for a in actors:
            mode = ((a.get("coverage") or {}).get("mode")) or "unknown"
            coverage_mode_breakdown[mode] = coverage_mode_breakdown.get(mode, 0) + 1
            operational_actors.append(
                {
                    "domain": d.get("id", "Unknown"),
                    "name": clean_links(str(a.get("name", a.get("id", "Unknown")))),
                    "responsibilities": clean_list(a.get("responsibilities", [])),
                    "coverage_mode": mode,
                }
            )

    ops_team_path = discovery_dir / "strategy" / "operations_team.yaml"
    ops_team_data = load_strategy_yaml(ops_team_path)
    fte_vs_retainer_count: dict = {}
    for role in ops_team_data.get("roles") or []:
        role_type = role.get("type", "fte")
        fte_vs_retainer_count[role_type] = fte_vs_retainer_count.get(role_type, 0) + 1

    if not personas and not machine_personas and not operational_actors:
        return None

    return {
        "personas": personas,
        "personas_count": len(audience_data.get("personas") or []),
        "machine_personas": machine_personas,
        "machine_personas_count": len(machine_personas),
        "operational_actors": operational_actors,
        "operational_actors_count": len(operational_actors),
        "zero_admin_domains_count": zero_admin_domains_count,
        "coverage_mode_breakdown": coverage_mode_breakdown,
        "fte_vs_retainer_count": fte_vs_retainer_count,
    }
