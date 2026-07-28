import typer
from pathlib import Path

from ...logic.cogs_calculator import calculate_cogs


def register_economics_queries(app: typer.Typer, print_yaml):
    @app.command("cogs-calculate")
    def cogs_calculate(
        draft_path: Path = typer.Argument(
            ...,
            help="Path to a draft unit_economics_model.yaml (revenue_model.yaml must sit next to it)",
        ),
    ):
        print_yaml(calculate_cogs(draft_path))
