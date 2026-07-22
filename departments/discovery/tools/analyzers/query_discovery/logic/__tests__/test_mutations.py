from __future__ import annotations

from pathlib import Path

import pytest

from departments.discovery.tools.analyzers.query_discovery.logic.mutations import (
    rename_entity,
    replace_term,
    set_field,
    reclassify_feature,
)

from .helpers import make_domain


def test_rename_entity_not_found_raises_clear_error(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing", entity="Invoice")

    with pytest.raises(ValueError, match="was not found"):
        rename_entity(tmp_path, "NoSuchEntity", "Renamed")


def test_rename_entity_missing_workspace_raises_clear_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="discovery/domains"):
        rename_entity(tmp_path / "nope", "Invoice", "Renamed")


def test_rename_entity_updates_dictionary_and_summary(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing", entity="Invoice")

    modified = rename_entity(tmp_path, "Invoice", "Bill")

    modified_paths = {p.name for p, _ in modified}
    assert "dictionary.yaml" in modified_paths
    assert "summary.yaml" in modified_paths
    for _path, content in modified:
        assert "Invoice" not in content
        assert "Bill" in content


def test_replace_term_unknown_domain_raises_clear_error(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing")

    with pytest.raises(ValueError, match="does not exist"):
        replace_term(tmp_path, "x", "y", scope="all", domain="nonexistent_domain")


def test_replace_term_pattern_not_found_raises_clear_error(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing")

    with pytest.raises(ValueError, match="was not found"):
        replace_term(tmp_path, "ZZZNOPE", "y", scope="all")


def test_replace_term_applies_replacement(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing", entity="Widget")

    modified = replace_term(
        tmp_path, "Widget", "Gadget", scope="dictionary", domain="billing"
    )

    assert len(modified) == 1
    path, content = modified[0]
    assert path.name == "dictionary.yaml"
    assert "Gadget" in content
    assert "Widget" not in content


def test_set_field_unknown_domain_returns_no_modifications(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing")

    modified = set_field(
        tmp_path, "test_marker", '"x"', "set", domain="nonexistent_domain"
    )

    assert modified == []


def test_set_field_sets_value_in_summary(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing")

    modified = set_field(tmp_path, "test_marker", '"hello"', "set", domain="billing")

    assert len(modified) == 1
    _path, content = modified[0]
    assert "test_marker" in content
    assert "hello" in content


def test_reclassify_feature_not_found_raises_clear_error(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing")

    with pytest.raises(ValueError, match="was not found"):
        reclassify_feature(tmp_path, "no_such_feature", "mvp_nice_to_have")


def test_reclassify_feature_moves_feature_between_buckets(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing")

    modified = reclassify_feature(tmp_path, "billing_feature", "mvp_nice_to_have")

    assert len(modified) == 1
    _path, content = modified[0]
    assert "mvp_nice_to_have" in content
