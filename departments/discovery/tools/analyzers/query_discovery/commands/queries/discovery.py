import typer
from pathlib import Path

from ...logic.reports.exports import (
    get_exports,
    search_index,
    get_trajectory,
    get_epic_requirements,
)
from ...logic.boundary import check_boundaries
from ...logic.trace import trace_source, trace_feature
from ...logic.orphans import get_orphans, get_coverage


def _run_boundary_check(domains_dir: Path, print_yaml) -> None:
    res = check_boundaries(domains_dir)
    if not res:
        typer.echo("No boundary violations (duplicate entities) found.")
    else:
        typer.echo("Found duplicate entities across domains:")
        print_yaml(res)


def _run_trace(workspace: Path, source: str, feature: str, print_yaml) -> None:
    if source and feature:
        typer.echo(
            "Error: Please provide either --source or --feature, not both.",
            err=True,
        )
        raise typer.Exit(1)
    if source:
        res = trace_source(workspace, source)
        if not res:
            typer.echo(f"Source reference '{source}' not found in any files.")
        else:
            print_yaml(res)
    elif feature:
        print_yaml(trace_feature(workspace, feature))
    else:
        typer.echo("Error: Must provide either --source or --feature.", err=True)
        raise typer.Exit(1)


def _run_orphans(workspace: Path, domain: str, print_yaml) -> None:
    res = get_orphans(workspace, domain)
    if not res:
        typer.echo("No orphan entities found.")
    else:
        print_yaml(res)


def _run_coverage(workspace: Path, check_mandatory_epics: bool, print_yaml) -> None:
    if check_mandatory_epics:
        print_yaml(get_coverage(workspace))
    else:
        typer.echo("Specify a coverage check, e.g. --check mandatory-epics")


def register_discovery_queries(app: typer.Typer, print_yaml):
    @app.command("exports")
    def exports(
        entity: str = typer.Option(..., "--entity", help="Entity to search in exports"),
        workspace: Path = typer.Argument(Path("workspace/")),
    ):
        print_yaml(get_exports(workspace, entity))

    @app.command("search")
    def search(
        query: str = typer.Argument(..., help="Query string"),
        scope: str = typer.Option("all", "--scope", help="Search scope"),
        workspace: Path = typer.Argument(Path("workspace/")),
    ):
        print_yaml(search_index(workspace, query, scope))

    @app.command("boundary-check")
    def boundary_check(
        domains_dir: Path = typer.Option(Path("workspace/discovery/domains"), "-d"),
    ):
        _run_boundary_check(domains_dir, print_yaml)

    @app.command("trajectory")
    def trajectory(
        workspace: Path = typer.Argument(Path("workspace/")),
        domain: str = typer.Option(None, "--domain", "-d"),
    ):
        print_yaml(get_trajectory(workspace, domain))

    @app.command("requirements")
    def requirements(
        workspace: Path = typer.Argument(Path("workspace/")),
        domain: str = typer.Option(None, "--domain", "-d"),
        is_global: bool = typer.Option(False, "--global", "-g"),
        section: str = typer.Option(None, "--section", "-s"),
        epic_type: str = typer.Option(None, "--epic-type", "-t"),
    ):
        print_yaml(
            get_epic_requirements(workspace, domain, is_global, section, epic_type)
        )

    @app.command("trace")
    def trace_cmd(
        source: str = typer.Option(
            None, "--source", help="Trace a source document reference"
        ),
        feature: str = typer.Option(None, "--feature", help="Trace a feature ID"),
        workspace: Path = typer.Argument(Path("workspace/")),
    ):
        _run_trace(workspace, source, feature, print_yaml)

    @app.command("orphans")
    def orphans(
        workspace: Path = typer.Argument(Path("workspace/")),
        domain: str = typer.Option(None, "--domain", "-d"),
    ):
        _run_orphans(workspace, domain, print_yaml)

    @app.command("coverage")
    def coverage(
        workspace: Path = typer.Argument(Path("workspace/")),
        check_mandatory_epics: bool = typer.Option(False, "--check"),
    ):
        _run_coverage(workspace, check_mandatory_epics, print_yaml)
