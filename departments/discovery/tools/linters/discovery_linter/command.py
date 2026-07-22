import sys
import json
from pathlib import Path
import typer
from pydantic import BaseModel, ValidationError
import yaml
import importlib
import inspect

app = typer.Typer(add_completion=False, help="Discovery Linter Multi-Tool")


def run_safe(func, *args, **kwargs):
    try:
        result = func(*args, **kwargs)
        if hasattr(result, "model_dump_json"):
            typer.echo(result.model_dump_json(indent=2))
        elif result is True:
            typer.echo('{"status": "ok"}')
        else:
            typer.echo(json.dumps(result, indent=2))
        sys.exit(0)
    except ValidationError as e:
        typer.echo(f"Validation Error:\n{e}", err=True)
        sys.exit(1)
    except Exception as e:
        typer.echo(f"Execution Error:\n{e}", err=True)
        sys.exit(1)


validators_dir = Path(__file__).parent / "validators"
for meta_path in validators_dir.rglob("meta.yaml"):
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}

        cmd_name = meta.get("name")
        entrypoint_name = meta.get("entrypoint")
        if not cmd_name or not entrypoint_name:
            continue

        # meta_path is like .../validators/epic/estimation/meta.yaml
        # module path should be departments.discovery.tools.linters.discovery_linter.validators.epic.estimation
        # We can construct it directly:
        rel_parts = meta_path.parent.relative_to(Path(__file__).parent).parts
        module_name = (
            "departments.discovery.tools.linters.discovery_linter."
            + ".".join(rel_parts)
        )

        module = importlib.import_module(module_name)
        func = getattr(module, entrypoint_name)

        # Some validators (e.g. stress-test) require more than one distinct
        # required input path and already ship their own fully-formed Typer
        # command (with dedicated --flags and sensible defaults) in a sibling
        # `command.py`, used today by their standalone dispatcher entrypoint.
        # Prefer that dedicated command over the generic single-PATH wrapper
        # below, which can only ever populate one required Path/str field.
        try:
            dedicated_module = importlib.import_module(f"{module_name}.command")
            dedicated_cmd = getattr(dedicated_module, "command", None)
        except ModuleNotFoundError:
            dedicated_cmd = None

        if dedicated_cmd is not None and dedicated_cmd is not func:
            app.command(cmd_name, help=f"Run {cmd_name} validation")(dedicated_cmd)
            continue

        def make_cmd(f):
            def cmd(
                path: Path = typer.Argument(..., help="Path to check"),
                fix: bool = typer.Option(True, help="Auto-fix errors if possible"),
            ):
                sig = inspect.signature(f)
                kwargs = {"fix": fix} if "fix" in sig.parameters else {}

                params = list(sig.parameters.values())
                first_annotation = params[0].annotation if params else None

                if isinstance(first_annotation, type) and issubclass(
                    first_annotation, BaseModel
                ):
                    model_cls = first_annotation

                    # Special case: ValidatePlatformCoverageInput requires two
                    # distinct paths (platform_strategy_path, domains_manifest_path)
                    # that cannot be derived from a single CLI `path` argument.
                    # It is only ever invoked internally by the `strategy`
                    # aggregate validator (general/strategy/__init__.py), which
                    # constructs both paths explicitly - it is not meant to be
                    # driven standalone via this generic single-path CLI. We
                    # special-case it here (by model name, not by hardcoding
                    # business logic) rather than silently mis-wiring it.
                    if model_cls.__name__ == "ValidatePlatformCoverageInput":
                        raise RuntimeError(
                            "platform-coverage requires two distinct input paths "
                            "(platform_strategy_path, domains_manifest_path) and "
                            "cannot be run standalone from a single CLI path "
                            "argument; it is invoked internally by the `strategy` "
                            "aggregate validator instead."
                        )

                    # Find the model's required fields whose type is Path.
                    path_fields = [
                        name
                        for name, field in model_cls.model_fields.items()
                        if field.is_required() and field.annotation is Path
                    ]

                    if len(path_fields) == 1:
                        model_instance = model_cls(**{path_fields[0]: path})
                        run_safe(f, model_instance, **kwargs)
                    elif len(path_fields) == 0:
                        # Fall back to a string-typed required field (e.g.
                        # ValidateMarkdownLinksInput.file_path: str) so
                        # entrypoints that model a path as `str` still work.
                        str_fields = [
                            name
                            for name, field in model_cls.model_fields.items()
                            if field.is_required() and field.annotation is str
                        ]
                        if len(str_fields) == 1:
                            model_instance = model_cls(**{str_fields[0]: str(path)})
                            run_safe(f, model_instance, **kwargs)
                        else:
                            raise RuntimeError(
                                f"Cannot generically resolve a single CLI path "
                                f"argument to {model_cls.__name__}: no single "
                                f"required Path/str field found."
                            )
                    else:
                        raise RuntimeError(
                            f"Cannot generically resolve a single CLI path "
                            f"argument to {model_cls.__name__}: multiple "
                            f"required Path fields found ({path_fields}); this "
                            f"validator needs a dedicated caller."
                        )
                else:
                    # Bare Path (or unannotated) parameter - keep prior behavior.
                    run_safe(f, path, **kwargs)

            return cmd

        # We use short_help because Typer extracts help from docstrings
        app.command(cmd_name, help=f"Run {cmd_name} validation")(make_cmd(func))
    except Exception as e:
        print(f"Warning: Failed to load command from {meta_path}: {e}", file=sys.stderr)

command = app
