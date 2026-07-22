from __future__ import annotations
from pathlib import Path
import pytest
from departments.operations.tools.shared import agent_parser
from .helpers import make_agent_md

EXPECTED_TEMPERATURE = 0.3


def test_parse_agent_frontmatter(tmp_path: Path) -> None:
    md = make_agent_md(
        tmp_path / "agent.md",
        name="my-agent",
        model="gemini-1.5-pro",
        temperature=EXPECTED_TEMPERATURE,
    )
    result = agent_parser.parse_agent(md)
    assert result["name"] == "my-agent"
    assert result["model"] == "gemini-1.5-pro"
    assert result["temperature"] == pytest.approx(EXPECTED_TEMPERATURE)
    assert "read_file" in result["tools"]
    assert "write_file" in result["tools"]


def test_parse_agent_xml_blocks(tmp_path: Path) -> None:
    md = make_agent_md(
        tmp_path / "agent.md",
        name="xml-agent",
        inputs="- workspace/discovery/market_context.md",
        workflow=(
            '<step id="2">'
            '<write contract="departments/discovery/contracts/features_template.yaml">'
            "workspace/discovery/output.yaml</write>"
            "</step>"
        ),
    )
    result = agent_parser.parse_agent(md)

    assert any("skill-job-stories.md" in s for s in result["required_skills"])
    assert any("features_template.yaml" in c for c in result["contracts"])
    assert result["write_contracts"]["workspace/discovery/output.yaml"] == (
        "departments/discovery/contracts/features_template.yaml"
    )
    assert any("market_context.md" in r for r in result["reads"])
    assert any("output.yaml" in w for w in result["writes"])
