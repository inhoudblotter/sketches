from pathlib import Path
from ...utils.common import load_strategy_yaml
from departments.discovery.tools.shared.text_utils import clean_links


def build_errata(errata_path: Path) -> dict | None:
    if not errata_path.exists():
        return None
    errata_data = load_strategy_yaml(errata_path)
    blockers: list = []
    if isinstance(errata_data, dict) and "critical_errata" in errata_data:
        errata_node = errata_data["critical_errata"]
        blockers = (
            errata_node.get("actionable_blockers", [])
            if isinstance(errata_node, dict)
            else (errata_node if isinstance(errata_node, list) else [])
        )
    elif isinstance(errata_data, dict) and "actionable_blockers" in errata_data:
        blockers = errata_data.get("actionable_blockers", [])
    elif isinstance(errata_data, list):
        blockers = errata_data

    # MAGIC NUMBERS FIX: PLR2004
    MAX_BLOCKERS = 4
    parsed_blockers = []
    for b in blockers[:MAX_BLOCKERS]:
        source = b.get("source") or b.get("domain") or "Unknown"
        issue = b.get("issue") or b.get("description") or str(b)
        parsed_blockers.append(
            {
                "source": clean_links(str(source)),
                "issue": clean_links(str(issue)),
            }
        )
    return {"blockers": parsed_blockers}
