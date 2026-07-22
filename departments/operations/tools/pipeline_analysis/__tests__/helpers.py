from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

_AGENT_TEMPLATE = """\
---
name: {name}
description: {description}
model: {model}
temperature: {temperature}
tools:
  - read_file
  - write_file
---

<required_skills>
- departments/discovery/playbooks/skill-job-stories.md
</required_skills>

<workflow>
<step id="1">
{reads}
</step>
{workflow}
<step id="99">
{writes}
</step>
</workflow>

<escalation_protocol>
Handoff: workspace/discovery/handoff/{name}.md
</escalation_protocol>
"""


def _bullets_to_tags(block: str, tag: str) -> str:
    """Convert a legacy '- workspace/x.yaml' bullet list into '<read>x</read>'
    (or '<write>') tags, one per line."""
    lines = []
    for line in block.splitlines():
        stripped = line.strip().lstrip("- ").strip()
        if stripped and not stripped.startswith("#"):
            lines.append(f"<{tag}>{stripped}</{tag}>")
    return "\n".join(lines)


def make_agent_md(
    path: Path,
    *,
    name: str = "test-agent",
    description: str = "",
    model: str = "gemini-1.5-pro",
    temperature: float = 0.7,
    workflow: str = "",
    inputs: str = "",
    outputs: str = "",
) -> Path:
    path.write_text(
        _AGENT_TEMPLATE.format(
            name=name,
            description=description,
            model=model,
            temperature=temperature,
            workflow=workflow,
            reads=_bullets_to_tags(inputs, "read"),
            writes=_bullets_to_tags(outputs, "write"),
        ),
        encoding="utf-8",
    )
    return path


def minimal_agent(
    name: str, reads: list[str], writes: list[str], handoff: str | None = None
) -> dict:
    return {
        "name": name,
        "model": "m",
        "temperature": 0.1,
        "tools": [],
        "required_skills": [],
        "contracts": [],
        "reads": reads,
        "writes": writes,
        "escalation_handoff": handoff,
    }
