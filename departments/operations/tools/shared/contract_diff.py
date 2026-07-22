"""Detects field-level drift between a linter's pydantic schema and the YAML
contract template it validates against.

A tool declares this pairing explicitly in its meta.yaml:
    contract: "departments/discovery/contracts/xxx_template.yaml"
    contract_schema: "departments.discovery.tools.linters.xxx.schemas.XxxSchema"

Both sides are flattened into dotted-path sets and diffed:
- schema_only: the linter enforces a field the template never shows an author
  — the template is stale/incomplete (or was never updated after the schema
  grew a field).
- template_only: the template documents a field the schema doesn't know about
  at all — an author can fill it in and the linter will silently never check
  it (e.g. a field renamed in one place but not the other).
"""

from __future__ import annotations

import importlib
import sys
import typing
from dataclasses import dataclass, field
from pathlib import Path

import typer
import yaml
from pydantic import BaseModel

from . import tool_parser


def _unwrap_optional(annotation):
    """Strip Optional[X]/X | None down to X. Returns annotation unchanged otherwise."""
    origin = typing.get_origin(annotation)
    if origin is typing.Union:
        args = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


def _list_item_model(annotation):
    """If annotation is List[SomeBaseModel] (optionally wrapped in Optional), return
    SomeBaseModel; otherwise None."""
    annotation = _unwrap_optional(annotation)
    origin = typing.get_origin(annotation)
    if origin in (list, typing.List):
        args = typing.get_args(annotation)
        if args:
            item = _unwrap_optional(args[0])
            if isinstance(item, type) and issubclass(item, BaseModel):
                return item
    return None


_DICT_TYPE_ARGS = 2  # Dict[K, V] always reduces to exactly (K, V) via get_args


def _dict_value_model(annotation):
    """If annotation is Dict[str, SomeBaseModel] (optionally wrapped in Optional),
    return SomeBaseModel; otherwise None. Mirrors _list_item_model — a
    Dict[str, X]-shaped field has runtime-arbitrary keys (e.g. `states` in
    UserFlowsSchema, keyed by author-chosen state names), so like a list it's
    flattened under its own dotted path rather than per-key, matching how
    flatten_yaml_template treats a `[bracketed]` example key in the template."""
    annotation = _unwrap_optional(annotation)
    origin = typing.get_origin(annotation)
    if origin is dict:
        args = typing.get_args(annotation)
        if len(args) == _DICT_TYPE_ARGS:
            value = _unwrap_optional(args[1])
            if isinstance(value, type) and issubclass(value, BaseModel):
                return value
    return None


def flatten_schema(
    model_cls: type[BaseModel], prefix: str = "", _seen: frozenset = frozenset()
) -> set[str]:
    """Walk a pydantic model's fields recursively into a set of dotted paths.

    Nested BaseModel fields (direct, List[BaseModel], or Dict[str, BaseModel])
    recurse using the same dotted path as the field itself — lists and dict
    keys aren't indexed. Any other field type is a leaf. Guards against
    infinite recursion on self-referential models by tracking the chain of
    model classes already on the current path.
    """
    if model_cls in _seen:
        return set()
    seen = _seen | {model_cls}

    paths: set[str] = set()
    for field_name, field_info in model_cls.model_fields.items():
        dotted = f"{prefix}.{field_name}" if prefix else field_name
        annotation = _unwrap_optional(field_info.annotation)

        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            paths |= flatten_schema(annotation, dotted, seen)
            continue

        list_item = _list_item_model(field_info.annotation)
        if list_item is not None:
            paths |= flatten_schema(list_item, dotted, seen)
            continue

        dict_value = _dict_value_model(field_info.annotation)
        if dict_value is not None:
            paths |= flatten_schema(dict_value, dotted, seen)
            continue

        paths.add(dotted)

    return paths


_MAP_KEY_RE = __import__("re").compile(r"^\[.*\]$")


def flatten_yaml_template(data, prefix: str = "") -> set[str]:
    """Walk a yaml.safe_load'd contract template into the same dotted-path shape
    flatten_schema produces, so the two sets are directly comparable."""
    paths: set[str] = set()

    if isinstance(data, dict):
        for key, value in data.items():
            # A bracketed key like "[SPIKE REQUIRED]" is a free-form example
            # entry in a Dict[str, X]-shaped field (arbitrary runtime keys),
            # not a fixed record field name — flatten_schema can't expand
            # those either, so don't append the key to the path or every
            # example key would spuriously show up as template-only drift.
            if isinstance(key, str) and _MAP_KEY_RE.match(key):
                paths |= flatten_yaml_template(value, prefix)
                continue
            dotted = f"{prefix}.{key}" if prefix else str(key)
            paths |= flatten_yaml_template(value, dotted)
        return paths

    if isinstance(data, list):
        if data and isinstance(data[0], dict):
            # One representative item, same dotted path as the list field —
            # mirrors the schema side, which doesn't index list members either.
            paths |= flatten_yaml_template(data[0], prefix)
        else:
            paths.add(prefix)
        return paths

    # scalar leaf (str/int/float/bool/None)
    paths.add(prefix)
    return paths


@dataclass
class ContractDrift:
    tool_name: str
    contract_path: str
    contract_schema: str
    schema_only: set[str] = field(default_factory=set)
    template_only: set[str] = field(default_factory=set)

    @property
    def has_drift(self) -> bool:
        return bool(self.schema_only or self.template_only)


def _resolve_schema_class(dotted_path: str) -> type[BaseModel]:
    module_path, _, class_name = dotted_path.rpartition(".")
    if not module_path:
        raise ValueError(f"Invalid contract_schema path: {dotted_path!r}")
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    if not (isinstance(cls, type) and issubclass(cls, BaseModel)):
        raise TypeError(f"{dotted_path} is not a pydantic BaseModel")
    return cls


def diff_tool_contract(
    tool_data: dict, tool_name: str, project_root: Path
) -> ContractDrift:
    contract_rel = tool_data["contract"]
    schema_path = tool_data["contract_schema"]

    schema_cls = _resolve_schema_class(schema_path)

    template_file = project_root / contract_rel
    if not template_file.is_file():
        raise FileNotFoundError(f"contract file not found: {template_file}")

    template_data = yaml.safe_load(template_file.read_text(encoding="utf-8")) or {}

    schema_paths = flatten_schema(schema_cls)
    template_paths = flatten_yaml_template(template_data)

    return ContractDrift(
        tool_name=tool_name,
        contract_path=contract_rel,
        contract_schema=schema_path,
        schema_only=schema_paths - template_paths,
        template_only=template_paths - schema_paths,
    )


def run_all(project_root: Path) -> list[ContractDrift]:
    tools = tool_parser.parse_all(project_root / "departments")
    results = []

    def process_tool_node(t_name, node_data):
        if not node_data.get("contract") or not node_data.get("contract_schema"):
            return None
        try:
            return diff_tool_contract(node_data, t_name, project_root)
        except Exception as e:
            return ContractDrift(
                tool_name=t_name,
                contract_path=node_data.get("contract", ""),
                contract_schema=node_data.get("contract_schema", ""),
                schema_only={f"<error resolving schema/contract: {e}>"},
            )

    for t in tools:
        drift = process_tool_node(t["name"], t)
        if drift:
            results.append(drift)

        for cmd_name, cmd_data in t.get("commands", {}).items():
            drift = process_tool_node(f"{t['name']}::{cmd_name}", cmd_data)
            if drift:
                results.append(drift)

    return results


def main():
    project_root = Path.cwd()
    results = run_all(project_root)
    drifted = [r for r in results if r.has_drift]

    if not drifted:
        typer.echo(
            f"Checked {len(results)} tool(s) with declared contract/contract_schema — no drift found."
        )
        sys.exit(0)

    for r in drifted:
        typer.echo(f"\n[{r.tool_name}] {r.contract_schema} vs {r.contract_path}")
        if r.schema_only:
            typer.echo("  schema-only (linter checks, template never shows it):")
            for p in sorted(r.schema_only):
                typer.echo(f"    - {p}")
        if r.template_only:
            typer.echo(
                "  template-only (author can fill it in, linter never checks it):"
            )
            for p in sorted(r.template_only):
                typer.echo(f"    - {p}")

    typer.echo(
        f"\n{len(drifted)}/{len(results)} tool(s) have contract/schema drift.", err=True
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
