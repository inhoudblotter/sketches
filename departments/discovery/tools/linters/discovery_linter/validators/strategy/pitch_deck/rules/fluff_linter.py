import re
from typing import Any
from departments.discovery.tools.shared.dict_utils import walk_strings

FLUFF_WORDS = [r"инновационный", r"революционный"]


def check_fluff_in_text(text: str) -> list[str]:
    errors = []
    for word in FLUFF_WORDS:
        if re.search(word, text, re.IGNORECASE):
            errors.append(f"Found marketing fluff word: '{word}'")
    return errors


def validate_fluff(data: Any) -> list[str]:
    """
    Recursively scans the data structure and checks string values for marketing fluff.
    Returns a list of error messages.
    """
    errors = []
    for path, text in walk_strings(data):
        found_fluff = check_fluff_in_text(text)
        for fluff in found_fluff:
            errors.append(f"{fluff} at {path}")
    return errors
