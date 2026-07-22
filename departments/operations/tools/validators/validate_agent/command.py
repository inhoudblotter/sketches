from pathlib import Path
import typer

from . import logic

AGENT_DIR_GLOBS = ("**/staff/*.md", "**/staff/subagents/*.md", "**/agents/*.md")


def _find_files_to_check(path: Path) -> list[Path]:
    files_to_check = []
    if path.is_file():
        if path.suffix == ".md":
            files_to_check.append(path)
    elif path.is_dir():
        seen = set()
        patterns = list(AGENT_DIR_GLOBS)
        if path.name in ("staff", "subagents", "agents"):
            # Path already points at an agent directory itself (not an
            # ancestor of one), so also match .md files directly inside it.
            patterns.append("*.md")
        for pattern in patterns:
            for f in path.glob(pattern):
                if f not in seen:
                    seen.add(f)
                    files_to_check.append(f)
        files_to_check.sort()
    return files_to_check


def _check_files(files_to_check: list[Path]) -> bool:
    has_errors = False
    for f in files_to_check:
        try:
            result = logic.validate_file(f)
            if result.status == "error":
                has_errors = True
                typer.echo(f"\n[FAIL] {f}", err=True)
                for err in result.errors:
                    line_info = f" (line {err.line})" if err.line else ""
                    typer.echo(f"  - [{err.rule}] {err.message}{line_info}", err=True)
            else:
                typer.echo(f"[OK] {f}")
        except Exception as e:
            has_errors = True
            typer.echo(f"\n[CRASH] {f}: {e}", err=True)
    return has_errors


def validate_agent_cmd(
    path: Path = typer.Argument(
        ..., help="Путь к markdown файлу агента или директории"
    ),
) -> None:
    """Линтер для проверки маркдаун-файлов агентов."""

    if not path.exists():
        typer.echo(f"[ERROR] Path not found: {path}", err=True)
        raise typer.Exit(1)

    files_to_check = _find_files_to_check(path)

    if not files_to_check:
        typer.echo(f"[ERROR] No markdown files found at: {path}", err=True)
        raise typer.Exit(1)

    has_errors = _check_files(files_to_check)

    if has_errors:
        raise typer.Exit(1)
    typer.echo("\nAll files passed validation.")
    raise typer.Exit(0)


command = validate_agent_cmd
