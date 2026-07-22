import typer
from pathlib import Path

from ...logic.reports.core import (
    get_toc,
    get_stats,
    get_domain_metrics,
    get_data_model_metrics,
)
from ...logic.queries.flows import get_estimation_summary
from ...logic.reports.exports import get_dependencies


def register_metrics_queries(app: typer.Typer, print_yaml):
    @app.command("toc")
    def toc(
        workspace: Path = typer.Argument(Path("workspace/")),
        domain: str = typer.Option(None, "--domain", "-d"),
    ):
        print_yaml(get_toc(workspace, domain))

    @app.command("stats")
    def stats(workspace: Path = typer.Argument(Path("workspace/"))):
        print_yaml(get_stats(workspace))

    @app.command("estimation")
    def estimation(
        workspace: Path = typer.Argument(Path("workspace/")),
        domain: str = typer.Option(None, "--domain", "-d"),
        epic: str = typer.Option(None, "--epic", "-e"),
        is_global: bool = typer.Option(False, "--global", "-g"),
    ):
        print_yaml(get_estimation_summary(workspace, domain, epic, is_global))

    @app.command("data-model")
    def data_model(
        workspace: Path = typer.Argument(Path("workspace/")),
        domain: str = typer.Option(None, "--domain", "-d"),
        is_global: bool = typer.Option(False, "--global", "-g"),
    ):
        print_yaml(get_data_model_metrics(workspace, domain, is_global))

    @app.command("dependencies")
    def dependencies(
        workspace: Path = typer.Argument(Path("workspace/")),
        domain: str = typer.Option(None, "--domain", "-d"),
    ):
        print_yaml(get_dependencies(workspace, domain))

    @app.command("metrics")
    def metrics(
        workspace: Path = typer.Argument(Path("workspace/")),
        domain: str = typer.Option(None, "--domain", "-d"),
        m_type: str = typer.Option("all", "--type", "-t"),
        is_global: bool = typer.Option(False, "--global", "-g"),
    ):
        print_yaml(get_domain_metrics(workspace, domain, m_type, is_global))
