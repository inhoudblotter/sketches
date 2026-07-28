import typer
import yaml
from typing import Any


class _NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def _print_yaml(data: Any):
    typer.echo(
        yaml.dump(data, allow_unicode=True, sort_keys=False, Dumper=_NoAliasDumper)
    )


def register_queries(app: typer.Typer):
    from .core import register_core_queries
    from .metrics import register_metrics_queries
    from .discovery import register_discovery_queries
    from .errata import register_errata_queries
    from .economics import register_economics_queries

    register_core_queries(app, _print_yaml)
    register_metrics_queries(app, _print_yaml)
    register_discovery_queries(app, _print_yaml)
    register_errata_queries(app, _print_yaml)
    register_economics_queries(app, _print_yaml)
