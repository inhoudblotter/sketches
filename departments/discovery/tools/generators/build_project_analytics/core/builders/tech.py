from pathlib import Path
from ...utils.common import load_strategy_yaml
from departments.discovery.tools.shared.text_utils import clean_links


def build_tech(strategy_dir: Path) -> dict | None:
    tech_path = strategy_dir / "tech_constraints.yaml"
    if not tech_path.exists():
        return None
    tech_data = load_strategy_yaml(tech_path)
    stack = tech_data.get("technology_stack", {})
    growth_path = [
        {
            "component": clean_links(str(entry.get("component", ""))),
            "trigger": clean_links(str(entry.get("trigger", ""))),
            "action": clean_links(str(entry.get("action", ""))),
            "rewrite_cost": clean_links(str(entry.get("rewrite_cost", ""))),
        }
        for entry in (tech_data.get("growth_path") or [])
    ]
    return {
        "frontend": clean_links(stack.get("frontend", "Unknown")),
        "backend": clean_links(stack.get("backend", "Unknown")),
        "database": clean_links(stack.get("database", "Unknown")),
        "infra": clean_links(stack.get("infrastructure", "Unknown")),
        "p2p": clean_links(stack.get("p2p_network_layer", "")),
        "insight": clean_links(tech_data.get("strategic_insight", "N/A")),
        "growth_path": growth_path,
        "maintainability": clean_links(tech_data.get("maintainability_notes", "")),
    }
