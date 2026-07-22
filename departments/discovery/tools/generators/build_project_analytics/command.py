import typer
import sys
from pathlib import Path
from .schemas import BuildProjectAnalyticsInput
from .logic import run_build_project_analytics


def command(
    workspace: Path = typer.Option(
        ...,
        "--workspace",
        "-w",
        help="Путь к директории workspace/discovery",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
):
    """
    Агрегирует аналитику проекта и сохраняет ее в meta/project_analytics.yaml.
    """
    try:
        input_data = BuildProjectAnalyticsInput(workspace_path=workspace)
        output = run_build_project_analytics(input_data)

        typer.echo(
            f"[SUCCESS] Project Analytics Index generated at: {output.index_path}"
        )
        typer.echo(f"MVP SP Total: {output.total_mvp_sp} ({output.mvp_size_bucket})")
        typer.echo(f"High Risk Stories: {output.high_risk_stories_count}")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        sys.exit(1)
