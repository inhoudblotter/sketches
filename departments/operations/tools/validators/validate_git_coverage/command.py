from pathlib import Path
import typer

from . import logic


def validate_git_coverage_cmd(
    path: Path = typer.Argument(
        ..., help="Путь к директории staff/ агентов (departments/<dept>/staff)"
    ),
) -> None:
    """Статический линтер git-safety гарантий агентов: MISSING_COMMIT,
    PATH_MISMATCH, STILL_SELF_COMMITS_BUT_PARALLEL, DESTRUCTIVE_GIT_OP."""

    if not path.exists() or not path.is_dir():
        typer.echo(f"[ERROR] Staff directory not found: {path}", err=True)
        raise typer.Exit(1)

    try:
        result = logic.analyze(path)
    except Exception as e:
        typer.echo(f"[CRASH] {path}: {e}", err=True)
        raise typer.Exit(1) from e

    if not result.files_checked:
        typer.echo(f"[ERROR] No agent .md files found under: {path}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Checked {len(result.files_checked)} agent file(s) under {path}\n")

    if not result.findings:
        typer.echo("All files passed git-coverage validation.")
        raise typer.Exit(0)

    by_file: dict[str, list] = {}
    for f in result.findings:
        by_file.setdefault(f.file_path, []).append(f)

    for file_path, file_findings in sorted(by_file.items()):
        typer.echo(f"[FAIL] {file_path}", err=True)
        for finding in file_findings:
            detail = f" ({finding.detail})" if finding.detail else ""
            typer.echo(f"  - [{finding.category}] {finding.message}{detail}", err=True)
        typer.echo("", err=True)

    typer.echo(
        f"{len(result.findings)} finding(s) across {len(by_file)} file(s).", err=True
    )
    raise typer.Exit(1)


command = validate_git_coverage_cmd
