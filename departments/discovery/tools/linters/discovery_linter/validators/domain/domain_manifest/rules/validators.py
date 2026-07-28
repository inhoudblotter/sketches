from pathlib import Path
from typing import Any, Dict

from departments.discovery.tools.shared_rules.banned_tech_vendors import (
    BANNED_VENDORS_REGEX,
)


def validate_banned_words(data: Any) -> None:
    if isinstance(data, str):
        match = BANNED_VENDORS_REGEX.search(data)
        if match:
            raise ValueError(
                f"Found banned word/pattern: '{match.group(0)}'. SaaS solutions, manual roles, and specific DB/crypto types are restricted."
            )
    elif isinstance(data, dict):
        for key, value in data.items():
            validate_banned_words(key)
            validate_banned_words(value)
    elif isinstance(data, list):
        for item in data:
            validate_banned_words(item)


def validate_no_shared_context(file_path: Path, data: Dict[str, Any]) -> None:
    if "shared" in [p.lower() for p in file_path.parts]:
        raise ValueError(
            f"Banned directory name: 'shared' is not allowed in path {file_path}"
        )

    if isinstance(data, dict):
        domain = data.get("domain")
        if isinstance(domain, str) and domain.strip().lower() == "shared":
            raise ValueError(
                "Banned boundary context: 'shared' is not allowed as a domain."
            )
