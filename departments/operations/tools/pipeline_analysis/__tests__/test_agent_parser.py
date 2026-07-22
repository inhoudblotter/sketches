from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from departments.operations.tools.shared.agent_parser import (
    parse_agent,
    extract_required_skills,
)

STAFF_DIR = Path(__file__).resolve().parents[5] / "departments/discovery/staff"
PO = STAFF_DIR / "po-strategist.md"


def test_frontmatter_po_strategist():
    agent = parse_agent(PO)
    assert agent["name"] == "po-strategist"


def test_required_skills_strips_comment():
    block = "- ./departments/discovery/playbooks/skill-job-stories.md (Правила)"
    result = extract_required_skills(block)
    assert result == ["departments/discovery/playbooks/skill-job-stories.md"]
