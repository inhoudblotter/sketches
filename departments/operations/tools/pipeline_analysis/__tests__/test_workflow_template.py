from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from departments.operations.tools.pipeline_analysis.command import _render
from departments.operations.tools.pipeline_analysis import logic

_AGENT_TEMPLATE = """\
---
name: {name}
description: {description}
model: sonnet
temperature: 0.5
---

<required_skills>
</required_skills>

<workflow>
<step id="1">
{reads}
{writes}
</step>
</workflow>
"""


def _make_agent(
    path: Path, *, name: str, description: str, reads: str = "", writes: str = ""
) -> None:
    path.write_text(
        _AGENT_TEMPLATE.format(
            name=name, description=description, reads=reads, writes=writes
        ),
        encoding="utf-8",
    )


def _run_cli(agents_dir: Path, workspace_dir: Path, output: Path) -> None:
    data = logic.run(agents_dir, workspace_dir)
    fmt = "workflow" if output.name == "WORKFLOW.md" else "md"
    text = _render(data, serve_mode=False, fmt=fmt)
    output.write_text(text, encoding="utf-8")


def test_workflow_output_selected_by_filename(tmp_path: Path) -> None:
    """--output ending in WORKFLOW.md must render via workflow.md.j2, not report.md.j2."""
    agents_dir = tmp_path / "staff"
    agents_dir.mkdir()
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()

    _make_agent(
        agents_dir / "a.md",
        name="agent-a",
        description="Does the important thing.",
        writes="<write>workspace/out.yaml</write>",
    )

    output = tmp_path / "WORKFLOW.md"
    _run_cli(agents_dir, workspace_dir, output)

    text = output.read_text(encoding="utf-8")
    assert "WORKFLOW" in text.splitlines()[0]
    assert "Does the important thing." in text
    assert "## Execution Plan" in text
    assert "Phase 1" in text
    assert "`agent-a`" in text
    # The dashboard-only sections (status table, context budget, orphan/missing-input
    # debug dump) belong to report.md.j2 and must not leak into the workflow doc.
    assert "## Pipeline Status" not in text
    assert "## Context Budget" not in text


def test_report_md_still_used_for_other_filenames(tmp_path: Path) -> None:
    """A plain .md output (not named WORKFLOW.md) keeps using report.md.j2."""
    agents_dir = tmp_path / "staff"
    agents_dir.mkdir()
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()

    _make_agent(agents_dir / "a.md", name="agent-a", description="Does the thing.")

    output = tmp_path / "report.md"
    _run_cli(agents_dir, workspace_dir, output)

    text = output.read_text(encoding="utf-8")
    assert "# Discovery Department Report" in text
    assert "## Pipeline Status" in text


def test_multi_stage_workflow_groups_agents_by_phase(tmp_path: Path) -> None:
    """Two agents in a producer/consumer chain land in successive phases."""
    agents_dir = tmp_path / "staff"
    agents_dir.mkdir()
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()

    _make_agent(
        agents_dir / "a.md",
        name="agent-a",
        description="Produces the seed file.",
        writes="<write>workspace/seed.yaml</write>",
    )
    _make_agent(
        agents_dir / "b.md",
        name="agent-b",
        description="Consumes the seed file.",
        reads="<read>workspace/seed.yaml</read>",
    )

    output = tmp_path / "WORKFLOW.md"
    _run_cli(agents_dir, workspace_dir, output)
    text = output.read_text(encoding="utf-8")

    phase1 = text.index("Phase 1")
    phase2 = text.index("Phase 2")
    agent_a_pos = text.index("`agent-a`")
    agent_b_pos = text.index("`agent-b`")
    assert phase1 < agent_a_pos < phase2 < agent_b_pos
