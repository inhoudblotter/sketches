"""Parse WORKFLOW.md to extract phase → [agent_names] mapping."""

from __future__ import annotations
import re
from pathlib import Path

# ## Phase 1: ..., ## Phase 7.5: ...
PHASE_HEADER_RE = re.compile(r"^##\s+Phase\s+([\d.]+):", re.MULTILINE)
# **Агенты:** `product-scout.md`, `marketing-scout.md` ...
AGENTS_LINE_RE = re.compile(r"\*\*Агенты:\*\*([^\n]+)")
# backtick-quoted name, strip .md
AGENT_NAME_RE = re.compile(r"`([\w-]+?)(?:\.md)?`")


def parse(workflow_md: Path) -> dict[str, float]:
    """Return {agent_name: phase_number}. Subagents listed in WORKFLOW.md are included."""
    if not workflow_md.exists():
        return {}

    text = workflow_md.read_text(encoding="utf-8")
    phase_index: dict[str, float] = {}

    # Split into sections by phase header
    sections = PHASE_HEADER_RE.split(text)
    # sections = [pre-text, phase_num, section_body, phase_num, section_body, ...]
    it = iter(sections)
    next(it)  # skip pre-text
    for phase_str, body in zip(it, it, strict=False):
        phase_num = float(phase_str)
        for m in AGENTS_LINE_RE.finditer(body):
            for name_m in AGENT_NAME_RE.finditer(m.group(1)):
                agent_name = name_m.group(1)
                phase_index[agent_name] = phase_num

    return phase_index
