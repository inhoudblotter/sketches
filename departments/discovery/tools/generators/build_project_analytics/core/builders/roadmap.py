from pathlib import Path
from ...utils.common import load_strategy_yaml
from departments.discovery.tools.shared.text_utils import clean_links, clean_list


def build_roadmap(strategy_dir: Path) -> dict | None:
    roadmap_path = strategy_dir / "launch_roadmap.yaml"
    if not roadmap_path.exists():
        return None
    data = load_strategy_yaml(roadmap_path)
    phases = data.get("phases", {})
    parsed_phases = [
        {
            "id": phase_id,
            "description": clean_links(phase_data.get("description", "")),
            "primary_growth_loop": clean_list(
                phase_data.get("primary_growth_loop", [])
            ),
            "cold_start_tactics": clean_list(phase_data.get("cold_start_tactics", [])),
            "friction_management": clean_list(
                phase_data.get("friction_management", [])
            ),
            "ecosystem_symbiosis": clean_list(
                phase_data.get("ecosystem_symbiosis", [])
            ),
            "defensibility_moats": clean_list(
                phase_data.get("defensibility_moats", [])
            ),
            "unit_economics_validation": clean_links(
                phase_data.get("unit_economics_validation", "N/A")
            ),
            "source_ref": phase_data.get("source_ref", ""),
        }
        for phase_id, phase_data in phases.items()
    ]
    return {"phases": parsed_phases}
