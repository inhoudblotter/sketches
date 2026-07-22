import sys
import typer
from pathlib import Path
from typing import Optional
from ...linters.discovery_linter.validators.strategy.pitch_deck import (
    run_validation as validate_pitch_deck,
)
from .schemas import GeneratePitchDeckInput
from .logic import run_generate_pitch_deck


def generate_pitch_deck_cmd(
    yaml_path: Path = typer.Argument(..., help="Path to input pitch_deck.yaml"),
    out_path: Optional[Path] = typer.Option(
        None,
        "--out",
        "-o",
        help="Path to output HTML file (defaults to <yaml_path>.html)",
    ),
    analytics_path: Optional[Path] = typer.Option(
        Path("workspace/discovery/meta/project_analytics.yaml"),
        "--analytics",
        help="Path to project_analytics.yaml (compact, produced by build-project-analytics)",
    ),
    detail_path: Optional[Path] = typer.Option(
        Path("workspace/discovery/meta/project_analytics_detail.yaml"),
        "--detail",
        help="Path to project_analytics_detail.yaml (verbose pitch-deck-only data, produced by build-project-analytics)",
    ),
):
    """Validate (fail-fast) then generate Reveal.js HTML presentation from YAML narrative and pre-aggregated project analytics."""
    try:
        validation = validate_pitch_deck(yaml_path)
        if not validation.is_valid:
            typer.echo(validation.model_dump_json(indent=2), err=True)
            sys.exit(1)

        input_data = GeneratePitchDeckInput(
            yaml_path=yaml_path,
            out_path=out_path or yaml_path.with_suffix(".html"),
            analytics_path=analytics_path,
            detail_path=detail_path,
        )
        result = run_generate_pitch_deck(input_data)
        typer.echo(result.model_dump_json(indent=2))
        sys.exit(0)
    except Exception as e:
        typer.echo(f"Execution Error:\n{e}", err=True)
        sys.exit(1)


command = generate_pitch_deck_cmd
