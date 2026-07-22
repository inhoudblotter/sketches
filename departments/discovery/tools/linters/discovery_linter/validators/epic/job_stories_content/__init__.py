import re
from pathlib import Path

from departments.discovery.tools.shared_rules.banned_tech_vendors import (
    BANNED_VENDORS_REGEX,
)

BANNED_WORDS = [
    r"кнопк",
    r"нажать",
    r"клик",
    r"модал",
    r"попап",
    r"дашборд",
    r"экран",
    r"страниц",
    r"чекбокс",
    r"выпадающ",
    r"тумблер",
    r"button",
    r"click",
    r"modal",
    r"dashboard",
    r"screen",
    r"page",
    r"checkbox",
    r"dropdown",
]
PATTERN = re.compile(r"\b(" + "|".join(BANNED_WORDS) + r")\w*", re.IGNORECASE)


def _lint_stories_file(js_file: Path) -> list[str]:
    errors = []
    label = f"epics/{js_file.parent.name}/{js_file.name}"
    with js_file.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            matches = PATTERN.findall(line)
            if matches:
                matched_words = ", ".join(matches)
                errors.append(
                    f"{label}:{i} contains UI-related terms: {matched_words}. Line: {line.strip()}"
                )
            vendor_match = BANNED_VENDORS_REGEX.search(line)
            if vendor_match:
                errors.append(
                    f"{label}:{i} contains banned tech/vendor: {vendor_match.group(0)}. Line: {line.strip()}"
                )
    return errors


def _lint_vendor_leaks(yaml_file: Path, file_name: str) -> list[str]:
    errors = []
    with yaml_file.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            vendor_match = BANNED_VENDORS_REGEX.search(line)
            if vendor_match:
                errors.append(
                    f"{file_name}:{i} contains banned tech/vendor: {vendor_match.group(0)}. Line: {line.strip()}"
                )
    return errors


def run_lint_job_stories_content(domain_dir: Path):
    errors = []

    epics_dir = domain_dir / "epics"
    if epics_dir.exists() and epics_dir.is_dir():
        for js_file in sorted(epics_dir.glob("*/stories.yaml")):
            errors.extend(_lint_stories_file(js_file))

    for file_name in ["features.yaml", "summary.yaml"]:
        yaml_file = domain_dir / file_name
        if yaml_file.exists():
            errors.extend(_lint_vendor_leaks(yaml_file, file_name))

    if errors:
        raise ValueError("\n".join(errors))
