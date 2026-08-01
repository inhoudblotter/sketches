import typer
from pathlib import Path

from ...logic.queries.core import (
    get_slice,
    get_filtered_stories,
    get_filtered_features,
    get_filtered_epics,
)
from ...logic.queries.flows import get_filtered_flows, get_telemetry_events_global


def register_core_queries(app: typer.Typer, print_yaml):
    @app.command("get")
    def get(
        domain: str = typer.Option(..., "--domain", "-d", help="Domain ID"),
        section: str = typer.Option(..., "--section", "-s", help="Section to extract"),
        workspace: Path = typer.Argument(Path("workspace/")),
    ):
        print_yaml(get_slice(workspace, domain, section))

    @app.command("stories")
    def stories(
        workspace: Path = typer.Argument(Path("workspace/")),
        domain: str = typer.Option(None, "--domain", "-d"),
        pain_level: str = typer.Option(None, "--pain-level", "-p"),
        priority: str = typer.Option(None, "--priority", "-r"),
        epic_type: str = typer.Option(None, "--epic-type", "-t"),
        actor: str = typer.Option(
            None, "--actor", "-a", help="Filter by story `actor_id` (see manifest.yaml)"
        ),
        only_metrics: bool = typer.Option(False, "--only-metrics", "-m"),
    ):
        print_yaml(
            get_filtered_stories(
                workspace, domain, pain_level, priority, epic_type, actor, only_metrics
            )
        )

    @app.command("features")
    def features(
        workspace: Path = typer.Argument(Path("workspace/")),
        domain: str = typer.Option(None, "--domain", "-d"),
        priority: str = typer.Option(None, "--priority", "-p"),
        pain_level: str = typer.Option(None, "--pain-level", "-l"),
        epic_type: str = typer.Option(None, "--epic-type", "-t"),
    ):
        print_yaml(
            get_filtered_features(workspace, domain, priority, pain_level, epic_type)
        )

    @app.command("epics")
    def epics(
        workspace: Path = typer.Argument(Path("workspace/")),
        domain: str = typer.Option(None, "--domain", "-d"),
        crud_only: bool = typer.Option(False, "--crud-only", "-c"),
        complex_only: bool = typer.Option(False, "--complex-only", "-x"),
        epic_type: str = typer.Option(None, "--epic-type", "-t"),
    ):
        print_yaml(
            get_filtered_epics(workspace, domain, crud_only, complex_only, epic_type)
        )

    @app.command("flows")
    def flows(
        workspace: Path = typer.Argument(Path("workspace/")),
        domain: str = typer.Option(None, "--domain", "-d"),
        epic: str = typer.Option(None, "--epic", "-e"),
        only_sla: bool = typer.Option(False, "--only-sla", "-s"),
    ):
        print_yaml(get_filtered_flows(workspace, domain, epic, only_sla))

    @app.command("telemetry-events")
    def telemetry_events(
        workspace: Path = typer.Argument(Path("workspace/")),
        is_global: bool = typer.Option(
            False, "--global", "-g", help="Aggregate across all domains"
        ),
    ):
        if not is_global:
            raise typer.BadParameter("telemetry-events currently requires --global")
        print_yaml(get_telemetry_events_global(workspace))
