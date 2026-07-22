from __future__ import annotations

from pathlib import Path

from departments.discovery.tools.analyzers.query_discovery.logic.queries.core import (
    get_slice,
    get_filtered_epics,
    get_filtered_stories,
    get_filtered_features,
)

from ...__tests__.helpers import make_domain


def test_get_slice_unknown_domain_reports_error(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing")

    result = get_slice(tmp_path, "nonexistent", "epics")

    assert result == {"error": "Domain nonexistent not found"}


def test_get_slice_unknown_section_reports_error(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing")

    result = get_slice(tmp_path, "billing", "nonexistent_section")

    assert result == {
        "error": "Section nonexistent_section not found in domain billing"
    }


def test_get_slice_returns_requested_section(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing")

    result = get_slice(tmp_path, "billing", "epics")

    assert "epics" in result
    assert result["epics"][0]["epic_id"] == "core_epic"


def test_get_filtered_epics_by_domain(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing", epic_id="billing_epic")
    make_domain(tmp_path, "crew", epic_id="crew_epic")

    result = get_filtered_epics(tmp_path, domain="billing")

    assert len(result) == 1
    assert result[0]["epic_id"] == "billing_epic"
    assert result[0]["_domain"] == "billing"


def test_get_filtered_epics_unknown_domain_returns_empty(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing")

    result = get_filtered_epics(tmp_path, domain="nonexistent_domain")

    assert result == []


def test_get_filtered_stories_by_pain_level(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing", story_id="story-01")

    matching = get_filtered_stories(tmp_path, pain_level="High")
    non_matching = get_filtered_stories(tmp_path, pain_level="Low")

    assert len(matching) == 1
    assert matching[0]["id"] == "story-01"
    assert non_matching == []


def test_get_filtered_features_by_domain(tmp_path: Path) -> None:
    make_domain(tmp_path, "billing")
    make_domain(tmp_path, "crew")

    result = get_filtered_features(tmp_path, domain="billing")

    assert len(result) == 1
    assert result[0]["_domain"] == "billing"
