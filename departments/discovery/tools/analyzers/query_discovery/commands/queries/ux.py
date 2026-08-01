import typer
from pathlib import Path

from ...logic.queries.ux import get_ux_constraints_for_domain


def register_ux_queries(app: typer.Typer, print_yaml):
    @app.command("ux-constraints")
    def ux_constraints(
        workspace: Path = typer.Argument(Path("workspace/")),
        domain: str = typer.Option(..., "--domain", "-d", help="Domain ID"),
    ):
        print_yaml(get_ux_constraints_for_domain(workspace, domain))
