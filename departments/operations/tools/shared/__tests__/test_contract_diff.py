from typing import Dict, List, Optional
from pydantic import BaseModel

from pathlib import Path

from ..contract_diff import (
    flatten_schema,
    flatten_yaml_template,
    diff_tool_contract,
    run_all,
    ContractDrift,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[5]

# --- flatten_schema ---


def test_flatten_schema_leaf_fields():
    class Flat(BaseModel):
        name: str
        age: int
        active: bool

    assert flatten_schema(Flat) == {"name", "age", "active"}


def test_flatten_schema_nested_model():
    class Inner(BaseModel):
        x: str
        y: int

    class Outer(BaseModel):
        id: str
        inner: Inner

    assert flatten_schema(Outer) == {"id", "inner.x", "inner.y"}


def test_flatten_schema_optional_nested_model_unwrapped():
    class Inner(BaseModel):
        x: str

    class Outer(BaseModel):
        inner: Optional[Inner] = None

    assert flatten_schema(Outer) == {"inner.x"}


def test_flatten_schema_list_of_models_not_indexed():
    class Item(BaseModel):
        entity: str
        description: str

    class Outer(BaseModel):
        exports: List[Item]

    assert flatten_schema(Outer) == {"exports.entity", "exports.description"}


def test_flatten_schema_optional_list_of_models():
    class Item(BaseModel):
        a: str

    class Outer(BaseModel):
        items: Optional[List[Item]] = None

    assert flatten_schema(Outer) == {"items.a"}


def test_flatten_schema_list_of_scalars_is_leaf():
    class Outer(BaseModel):
        tags: List[str]

    assert flatten_schema(Outer) == {"tags"}


def test_flatten_schema_dict_field_is_leaf():
    class Outer(BaseModel):
        states: dict

    assert flatten_schema(Outer) == {"states"}


def test_flatten_schema_dict_of_scalars_is_leaf():
    class Outer(BaseModel):
        on: Dict[str, str]

    assert flatten_schema(Outer) == {"on"}


def test_flatten_schema_dict_of_models_recurses_not_indexed():
    # Arbitrary-keyed Dict[str, BaseModel] (e.g. UserFlowsSchema.states, keyed
    # by author-chosen state names) must recurse into the value model under
    # the field's own path, same as List[BaseModel] — otherwise the schema
    # side of a contract-drift diff sees the field as an opaque leaf while
    # the template side (which does recurse past a `[bracketed]` example key)
    # doesn't, producing permanent false-positive drift.
    class StateDef(BaseModel):
        display_data: List[str]

    class Outer(BaseModel):
        states: Dict[str, StateDef]

    assert flatten_schema(Outer) == {"states.display_data"}


def test_flatten_schema_optional_dict_of_models():
    class StateDef(BaseModel):
        a: str

    class Outer(BaseModel):
        states: Optional[Dict[str, StateDef]] = None

    assert flatten_schema(Outer) == {"states.a"}


def test_flatten_schema_self_referential_model_does_not_recurse_infinitely():
    class Node(BaseModel):
        name: str
        children: Optional[List["Node"]] = None

    Node.model_rebuild()

    # Must terminate rather than looping forever. The model class is already
    # on the path the moment we start expanding it, so self-recursive fields
    # (children: List[Node]) are cut off immediately rather than expanded
    # one extra level — "children" itself is dropped, not left as a leaf.
    result = flatten_schema(Node)
    assert result == {"name"}


# --- flatten_yaml_template ---


def test_flatten_yaml_template_scalars():
    data = {"name": "x", "age": 5, "active": True}
    assert flatten_yaml_template(data) == {"name", "age", "active"}


def test_flatten_yaml_template_nested_dict():
    data = {"id": "x", "inner": {"x": "a", "y": 1}}
    assert flatten_yaml_template(data) == {"id", "inner.x", "inner.y"}


def test_flatten_yaml_template_list_of_dicts_uses_first_item_not_indexed():
    data = {
        "exports": [
            {"entity": "A", "description": "d"},
            {"entity": "B", "description": "d2"},
        ]
    }
    assert flatten_yaml_template(data) == {"exports.entity", "exports.description"}


def test_flatten_yaml_template_empty_list_is_leaf():
    data = {"tags": []}
    assert flatten_yaml_template(data) == {"tags"}


def test_flatten_yaml_template_list_of_scalars_is_leaf():
    data = {"tags": ["a", "b"]}
    assert flatten_yaml_template(data) == {"tags"}


# --- diff_tool_contract ---


def test_diff_tool_contract_detects_both_directions(tmp_path, monkeypatch):
    class Item(BaseModel):
        entity: str
        # 'extra_in_schema' only exists on the schema side.
        extra_in_schema: str

    class Root(BaseModel):
        domain: str
        exports: List[Item]

    # Make the class importable via a dotted path for _resolve_schema_class.
    import sys
    import types

    mod = types.ModuleType("_contract_diff_fixture_module")
    mod.Root = Root
    sys.modules["_contract_diff_fixture_module"] = mod

    contract_file = tmp_path / "root_template.yaml"
    contract_file.write_text(
        "domain: 'x'\nexports:\n  - entity: 'E'\n    description: 'only in template'\n"
    )

    tool = {
        "name": "Fixture Tool",
        "contract": str(contract_file.relative_to(tmp_path)),
        "contract_schema": "_contract_diff_fixture_module.Root",
    }

    drift = diff_tool_contract(tool, tool_name=tool["name"], project_root=tmp_path)

    assert isinstance(drift, ContractDrift)
    assert drift.has_drift
    assert "exports.extra_in_schema" in drift.schema_only
    assert "exports.description" in drift.template_only

    del sys.modules["_contract_diff_fixture_module"]


def test_diff_tool_contract_no_drift_when_shapes_match(tmp_path):
    class Root(BaseModel):
        domain: str
        name: str

    import sys
    import types

    mod = types.ModuleType("_contract_diff_fixture_module_2")
    mod.Root = Root
    sys.modules["_contract_diff_fixture_module_2"] = mod

    contract_file = tmp_path / "root_template.yaml"
    contract_file.write_text("domain: 'x'\nname: 'y'\n")

    tool = {
        "name": "Fixture Tool 2",
        "contract": str(contract_file.relative_to(tmp_path)),
        "contract_schema": "_contract_diff_fixture_module_2.Root",
    }

    drift = diff_tool_contract(tool, tool_name=tool["name"], project_root=tmp_path)
    assert not drift.has_drift

    del sys.modules["_contract_diff_fixture_module_2"]


def test_run_all_real_project_has_no_contract_drift():
    # Regression guard for the actual repo's linter schemas vs. their
    # contracts/*.yaml templates — catches both a template falling out of
    # sync with its schema, and flatten_schema/flatten_yaml_template
    # themselves regressing on a shape they should treat as equivalent
    # (e.g. Dict[str, BaseModel] schema fields vs. `[bracketed]` example
    # keys in the template).
    drifts = run_all(_PROJECT_ROOT)
    drifting = [d for d in drifts if d.has_drift]
    assert drifting == [], drifting
