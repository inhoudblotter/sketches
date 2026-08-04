from pathlib import Path
from ...utils.common import load_strategy_yaml
from departments.discovery.tools.shared.text_utils import clean_links


def _stack_field(stack: dict, key: str) -> str:
    value = stack.get(key)
    if isinstance(value, list):
        value = ", ".join(str(v) for v in value)
    return clean_links(str(value)) if value else ""


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
    data_sourcing = [
        {
            "domain": clean_links(str(entry.get("domain", ""))),
            "feature_id": clean_links(str(entry.get("feature_id", ""))),
            "feature_name": clean_links(str(entry.get("feature_name", ""))),
            "automation_verdict": clean_links(str(entry.get("automation_verdict", ""))),
            "moderation_signal": clean_links(str(entry.get("moderation_signal", ""))),
            "legal_flags": [
                clean_links(str(flag)) for flag in (entry.get("legal_flags") or [])
            ],
        }
        for entry in (tech_data.get("data_sourcing") or [])
    ]
    return {
        "frontend": _stack_field(stack, "frontend"),
        "backend": _stack_field(stack, "backend"),
        "database": _stack_field(stack, "database"),
        "infra": _stack_field(stack, "infrastructure"),
        "p2p": _stack_field(stack, "p2p_network_layer"),
        "insight": clean_links(tech_data.get("strategic_insight", "N/A")),
        "growth_path": growth_path,
        "maintainability": clean_links(tech_data.get("maintainability_notes", "")),
        "data_sourcing": data_sourcing,
    }
