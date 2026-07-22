from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

from departments.discovery.tools.analyzers.query_discovery.logic.transaction import (
    TransactionManager,
)


@dataclass
class _Result:
    returncode: int
    stdout: str = ""
    stderr: str = ""


def _completed(returncode: int, stdout: str = "", stderr: str = "") -> _Result:
    return _Result(returncode, stdout, stderr)


def test_dry_run_does_not_write_files(tmp_path: Path, capsys) -> None:
    target = tmp_path / "file.yaml"
    target.write_text("old: value\n", encoding="utf-8")

    tx = TransactionManager(tmp_path)
    tx.add_modification(target, "new: value\n")
    tx.execute(apply=False)

    assert target.read_text(encoding="utf-8") == "old: value\n"
    out = capsys.readouterr().out
    assert "DRY RUN" in out
    assert "-old: value" in out or "old: value" in out
    assert "new: value" in out


def test_apply_writes_files_when_validation_passes(tmp_path: Path) -> None:
    target = tmp_path / "file.yaml"
    target.write_text("old: value\n", encoding="utf-8")

    tx = TransactionManager(tmp_path)
    tx.add_modification(target, "new: value\n")

    with patch(
        "departments.discovery.tools.analyzers.query_discovery.logic.transaction.subprocess.run",
        return_value=_completed(0),
    ):
        tx.execute(apply=True)

    assert target.read_text(encoding="utf-8") == "new: value\n"


def test_apply_rolls_back_when_validation_fails(tmp_path: Path, capsys) -> None:
    target = tmp_path / "file.yaml"
    target.write_text("old: value\n", encoding="utf-8")

    tx = TransactionManager(tmp_path)
    tx.add_modification(target, "new: value\n")

    with patch(
        "departments.discovery.tools.analyzers.query_discovery.logic.transaction.subprocess.run",
        return_value=_completed(1, stderr="boom"),
    ):
        tx.execute(apply=True)

    assert target.read_text(encoding="utf-8") == "old: value\n"
    out = capsys.readouterr().out
    assert "Rollback complete" in out


def test_apply_deletes_newly_created_file_on_rollback(tmp_path: Path) -> None:
    target = tmp_path / "new_file.yaml"
    assert not target.exists()

    tx = TransactionManager(tmp_path)
    tx.add_modification(target, "content: here\n")

    with patch(
        "departments.discovery.tools.analyzers.query_discovery.logic.transaction.subprocess.run",
        return_value=_completed(1),
    ):
        tx.execute(apply=True)

    assert not target.exists()


def test_no_modifications_is_a_no_op(tmp_path: Path, capsys) -> None:
    tx = TransactionManager(tmp_path)
    tx.execute(apply=True)

    out = capsys.readouterr().out
    assert "No changes to apply" in out
