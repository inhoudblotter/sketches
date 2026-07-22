from typing import Dict, Any

REQUIRED_SECTIONS = [
    "problem",
    "solution",
    "market_and_competition",
    "go_to_market",
    "risks",
]


def validate_structure(data: Dict[str, Any]) -> None:
    """
    Validates that the pitch deck contains all required mandatory_slides sections.
    Raises ValueError if any section is missing.
    """
    mandatory_slides = data.get("mandatory_slides", {})
    if not isinstance(mandatory_slides, dict):
        raise ValueError("'mandatory_slides' is missing or not an object.")
    missing = [
        section for section in REQUIRED_SECTIONS if section not in mandatory_slides
    ]
    if missing:
        raise ValueError(f"Missing required pitch deck sections: {', '.join(missing)}")
