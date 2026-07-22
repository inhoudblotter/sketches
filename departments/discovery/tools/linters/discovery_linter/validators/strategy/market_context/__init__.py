from pydantic import BaseModel
from typing import List
import re
from pathlib import Path


class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str]


def _extract_sections(text: str) -> dict:
    sections = {}
    for i in range(1, 9):
        pattern = rf"^## {i}\.\s+(.*?)(?=^## |\Z)"
        match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
        if match:
            sections[i] = match.group(1).strip()
        else:
            sections[i] = ""
    return sections


def validate_tracer_pattern(file_path: Path) -> ValidationResult:
    if not file_path.exists():
        return ValidationResult(is_valid=False, errors=[f"File not found: {file_path}"])

    content = file_path.read_text(encoding="utf-8")

    template_path = Path("departments/discovery/contracts/market_context_template.md")
    template_content = ""
    if template_path.exists():
        template_content = template_path.read_text(encoding="utf-8")

    actual_sections = _extract_sections(content)
    template_sections = _extract_sections(template_content)

    errors = []

    link_regex = re.compile(
        r"(\[.*?\]\(.*?(?:\.md|\.yaml|#L\d+).*?\))|(\[.*?(?:\.md|\.yaml|#L\d+).*?\])",
        re.IGNORECASE,
    )

    for sec_num, sec_content in actual_sections.items():
        if not sec_content:
            continue

        if template_content and sec_content == template_sections.get(sec_num, ""):
            continue

        if not link_regex.search(sec_content):
            errors.append(
                f"Секция '## {sec_num}.' заполнена, но не содержит ссылок Tracer Pattern (например, [file.md#L1-L2])."
            )

    if errors:
        return ValidationResult(is_valid=False, errors=errors)

    return ValidationResult(is_valid=True, errors=[])
