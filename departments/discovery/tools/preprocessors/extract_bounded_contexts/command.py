import sys
import typer
from .schemas import ExtractBoundedContextsInput
from .logic import execute


def extract_bounded_contexts_cmd(
    domains_dir: str = typer.Argument(..., help="Path to the directory with domains"),
    output_file: str = typer.Argument(..., help="Path to save bounded_contexts.yaml"),
):
    """
    Extract bounded contexts from domain dictionary files.
    """
    try:
        input_data = ExtractBoundedContextsInput(
            domains_dir=domains_dir, output_file=output_file
        )
        result = execute(input_data)
        typer.echo(result.model_dump_json(indent=2))
        sys.exit(0)
    except Exception as e:
        typer.echo(f"Error extracting bounded contexts: {e}", err=True)
        sys.exit(1)


command = extract_bounded_contexts_cmd
