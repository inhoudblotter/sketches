import sys
import typer
from pathlib import Path
from pydantic import ValidationError
from . import run_stress_test


def stress_test_economics_cmd(
    revenue_file: str = typer.Argument(
        "workspace/discovery/strategy/revenue_model.yaml",
        help="Путь к YAML файлу Revenue Model",
    ),
    economics_file: str = typer.Argument(
        "workspace/discovery/strategy/unit_economics_model.yaml",
        help="Путь к YAML файлу Unit Economics Model",
    ),
):
    """
    Выполняет стресс-тестирование юнит-экономики (Margin of Safety).
    Симулирует падение ARPU на 20% и рост COGS на 40%.
    Выводит JSON отчет. Падает с кодом 1, если маржа уходит в минус (CRITICAL RISK).
    """
    try:
        rev_path = Path(revenue_file)
        eco_path = Path(economics_file)
        result = run_stress_test(rev_path, eco_path)

        typer.echo(result.model_dump_json(indent=2))

        if result.overall_status == "CRITICAL_RISK":
            sys.exit(1)
        sys.exit(0)
    except ValidationError as e:
        typer.echo(e.json(), err=True)
        sys.exit(1)
    except Exception as e:
        typer.echo(f"Error during stress testing: {str(e)}", err=True)
        sys.exit(1)


command = stress_test_economics_cmd
