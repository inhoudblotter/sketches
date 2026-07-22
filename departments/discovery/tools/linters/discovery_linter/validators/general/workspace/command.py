import sys
import typer
from pathlib import Path
from . import run_validate_workspace


def workspace_cmd(
    workspace_dir: Path = typer.Argument(
        Path("workspace/"), help="Path to the workspace root (containing discovery/)"
    ),
    fix: bool = typer.Option(True, help="Auto-fix errors if possible"),
):
    """Run the full workspace validation suite (strategy, domains, cross-domain
    references, AST graph coupling, markdown links, global errata/estimation)."""
    try:
        result = run_validate_workspace(workspace_dir, fix=fix)
        typer.echo(result.summary())
        sys.exit(0 if result.passed else 1)
    except Exception as e:
        typer.echo(f"Execution Error:\n{e}", err=True)
        sys.exit(1)


command = workspace_cmd
