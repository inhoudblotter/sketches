from pydantic import BaseModel, Field
import os
from .rules.regex_validator import validate_markdown_content
from .rules.fixer import fix_markdown_content
from departments.discovery.tools.linters.discovery_linter.validators.shared.formatters import (
    auto_fix_xml_strings,
    auto_fix_markdown,
)


class ValidateMarkdownLinksInput(BaseModel):
    file_path: str = Field(..., description="Path to the markdown file to validate")


class ValidateMarkdownLinksOutput(BaseModel):
    is_valid: bool
    errors: list[str]


def run_validation(
    input_data: ValidateMarkdownLinksInput, fix: bool = True
) -> ValidateMarkdownLinksOutput:
    if not os.path.exists(input_data.file_path):
        return ValidateMarkdownLinksOutput(
            is_valid=False, errors=[f"File not found: {input_data.file_path}"]
        )

    with open(input_data.file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if fix:
        content = auto_fix_xml_strings(content)
        content = auto_fix_markdown(content)
        new_content = fix_markdown_content(content)
        if new_content != content:
            with open(input_data.file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            content = new_content

    errors = validate_markdown_content(content)

    return ValidateMarkdownLinksOutput(is_valid=len(errors) == 0, errors=errors)
