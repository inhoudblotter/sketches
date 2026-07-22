import typer
import yaml
from pathlib import Path

from ..logic.errata import resolve_errata
from ..logic.mutations import rename_entity, replace_term, set_field, reclassify_feature
from ..logic.transaction import TransactionManager


def _print_yaml(data: dict):
    typer.echo(yaml.dump(data, allow_unicode=True, sort_keys=False))


def _run_mutation(fn, *args, **kwargs) -> list:
    """Call a mutation-lookup function, turning "target not found" style
    errors into a clear CLI message instead of an unhandled traceback."""
    try:
        return fn(*args, **kwargs)
    except (FileNotFoundError, ValueError) as e:
        typer.echo(typer.style(f"Error: {e}", fg=typer.colors.RED))
        raise typer.Exit(1) from e


def _register_resolve_errata(app: typer.Typer):
    @app.command("resolve-errata")
    def resolve_errata_cmd(
        domain: str = typer.Option(..., "--domain", help="Domain ID"),
        errata_id: str = typer.Option(..., "--id", help="Errata ID"),
        resolution: str = typer.Option(..., "--resolution", help="Resolution text"),
        source: str = typer.Option(
            None,
            "--source",
            help="Errata file stem to target when a domain has multiple errata files (e.g. an epic name, or 'domain_strategy'). Omit to auto-search all errata files in the domain.",
        ),
        apply: bool = typer.Option(False, "--apply", help="Apply changes"),
        workspace: Path = typer.Argument(Path("workspace/")),
    ):
        """Resolve a specific errata entry."""
        modifications = _run_mutation(
            resolve_errata, workspace, domain, errata_id, resolution, source
        )
        tx = TransactionManager(workspace)
        for path, content in modifications:
            tx.add_modification(path, content)
        tx.execute(apply)


def _register_rename_entity(app: typer.Typer):
    @app.command("rename-entity")
    def rename_entity_cmd(
        from_name: str = typer.Option(..., "--from", help="Original entity name"),
        to_name: str = typer.Option(..., "--to", help="New entity name"),
        apply: bool = typer.Option(False, "--apply", help="Apply changes"),
        workspace: Path = typer.Argument(Path("workspace/")),
    ):
        """Mass rename an entity across dictionary and summary files."""
        modifications = _run_mutation(rename_entity, workspace, from_name, to_name)
        tx = TransactionManager(workspace)
        for path, content in modifications:
            tx.add_modification(path, content)
        tx.execute(apply)


def _register_replace_term(app: typer.Typer):
    @app.command("replace-term")
    def replace_term_cmd(
        pattern: str = typer.Option(..., "--pattern", help="String to replace"),
        replacement: str = typer.Option(
            ..., "--replacement", help="Replacement string"
        ),
        scope: str = typer.Option(
            "all", "--scope", help="Search scope: dictionary, stories, glossary, all"
        ),
        domain: str = typer.Option(
            None, "--domain", "-d", help="Filter by specific domain"
        ),
        apply: bool = typer.Option(False, "--apply", help="Apply changes"),
        workspace: Path = typer.Argument(Path("workspace/")),
    ):
        """Bulk find and replace across domains."""
        modifications = _run_mutation(
            replace_term, workspace, pattern, replacement, scope, domain
        )
        tx = TransactionManager(workspace)
        for path, content in modifications:
            tx.add_modification(path, content)
        tx.execute(apply)


def _register_set_field(app: typer.Typer):
    @app.command("set-field")
    def set_field_cmd(
        path: str = typer.Option(
            ..., "--key", help="YAML path (e.g. domain_metrics.kpi)"
        ),
        value: str = typer.Option(
            ..., "--value", help="Value to set or append (JSON parsable)"
        ),
        op: str = typer.Option("set", "--op", help="Operation: set or append"),
        domain: str = typer.Option(
            None, "--domain", "-d", help="Filter by specific domain"
        ),
        apply: bool = typer.Option(False, "--apply", help="Apply changes"),
        workspace: Path = typer.Argument(Path("workspace/")),
    ):
        """Bulk update or append fields in summary files."""
        modifications = _run_mutation(set_field, workspace, path, value, op, domain)
        tx = TransactionManager(workspace)
        for p, content in modifications:
            tx.add_modification(p, content)
        tx.execute(apply)


def _register_reclassify_feature(app: typer.Typer):
    @app.command("reclassify-feature")
    def reclassify_feature_cmd(
        feature_id: str = typer.Option(..., "--id", help="Feature ID to reclassify"),
        to_priority: str = typer.Option(
            ..., "--to", help="Target priority array (e.g. mvp_mandatory)"
        ),
        apply: bool = typer.Option(False, "--apply", help="Apply changes"),
        workspace: Path = typer.Argument(Path("workspace/")),
    ):
        """Move a feature to a different priority bucket across all domains."""
        modifications = _run_mutation(
            reclassify_feature, workspace, feature_id, to_priority
        )
        tx = TransactionManager(workspace)
        for p, content in modifications:
            tx.add_modification(p, content)
        tx.execute(apply)


def register_mutations(app: typer.Typer):
    _register_resolve_errata(app)
    _register_rename_entity(app)
    _register_replace_term(app)
    _register_set_field(app)
    _register_reclassify_feature(app)
