from pathlib import Path

from departments.operations.tools.validators.validate_agent.command import (
    _find_files_to_check,
)

_MIN_AGENT_MD = """\
---
name: {name}
description: does something
model: sonnet
temperature: 0.5
---

<workflow>
<step id="1">
</step>
</workflow>
"""


def test_finds_md_files_directly_inside_staff_dir(tmp_path: Path) -> None:
    """Regression: pointing validate-agent straight at a staff/ directory
    (rather than an ancestor of one) used to report "No markdown files
    found" even though the directory contains agent .md files directly,
    because the glob patterns only matched staff/ nested under another dir."""
    staff_dir = tmp_path / "staff"
    staff_dir.mkdir()
    (staff_dir / "agent-a.md").write_text(
        _MIN_AGENT_MD.format(name="agent-a"), encoding="utf-8"
    )

    found = _find_files_to_check(staff_dir)

    assert found == [staff_dir / "agent-a.md"]


def test_finds_md_files_directly_inside_subagents_dir(tmp_path: Path) -> None:
    subagents_dir = tmp_path / "subagents"
    subagents_dir.mkdir()
    (subagents_dir / "scout.md").write_text(
        _MIN_AGENT_MD.format(name="scout"), encoding="utf-8"
    )

    found = _find_files_to_check(subagents_dir)

    assert found == [subagents_dir / "scout.md"]


def test_finds_md_files_via_ancestor_dir(tmp_path: Path) -> None:
    """Original behavior (pointing at a dir containing staff/) must keep working."""
    staff_dir = tmp_path / "staff"
    staff_dir.mkdir()
    (staff_dir / "agent-a.md").write_text(
        _MIN_AGENT_MD.format(name="agent-a"), encoding="utf-8"
    )

    found = _find_files_to_check(tmp_path)

    assert found == [staff_dir / "agent-a.md"]


def test_unrelated_dir_with_no_agent_files_returns_empty(tmp_path: Path) -> None:
    (tmp_path / "notes.md").write_text("hello", encoding="utf-8")

    found = _find_files_to_check(tmp_path)

    assert found == []
