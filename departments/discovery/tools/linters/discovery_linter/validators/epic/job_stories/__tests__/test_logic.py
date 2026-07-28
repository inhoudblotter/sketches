from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from departments.discovery.tools.linters.discovery_linter.validators.epic.job_stories import (
    run_validation,
)

VALID_STORY = {
    "author_agent": "po-strategist-sub",
    "domain": "billing",
    "epic": "growth",
    "epic_type": "growth",
    "description": "",
    "epic_requirements": {
        "platforms": ["curator_web"],
        "is_headless": False,
        "offline_first": False,
        "events_to_handle": [],
        "business_constraints": [],
    },
    "stories": [
        {
            "id": "growth-01",
            "title": "Title",
            "situation": "Situation",
            "motivation": "Motivation",
            "outcome": "Outcome",
            "actor_id": "regular_user",
            "pain_level": "High",
            "metrics": ["metric"],
        }
    ],
}


def _write(path: Path, data: dict) -> Path:
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def test_valid_pain_level_passes(tmp_path: Path):
    p = _write(tmp_path / "stories.yaml", VALID_STORY)
    model = run_validation(p)
    assert model.stories[0].pain_level == "High"


def test_invalid_pain_level_is_rejected(tmp_path: Path):
    # Regression test: pain_level was previously typed as a bare `str`, so
    # values outside the contract's documented enum (Critical/High/Medium/Low)
    # silently passed validation instead of being caught.
    data = yaml.safe_load(yaml.safe_dump(VALID_STORY))
    data["stories"][0]["pain_level"] = "SuperExtreme"
    p = _write(tmp_path / "stories.yaml", data)

    with pytest.raises(ValidationError, match="pain_level"):
        run_validation(p)
