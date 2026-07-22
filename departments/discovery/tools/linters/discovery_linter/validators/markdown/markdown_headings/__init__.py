from pydantic import BaseModel, ConfigDict
from pathlib import Path
import re


class MarkdownHeadingsOutput(BaseModel):
    is_valid: bool
    missing_headings: list[str]
    template_path: str

    model_config = ConfigDict(extra="allow")


def extract_headings(content: str) -> set[str]:
    headings = set()
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("#"):
            h = line.lstrip("#").strip()
            # Strip leading digits and dots like "1. ", "2.1 ", "1.1.1. "
            h = re.sub(r"^[\d\.]+\s*", "", h).strip()
            if h:
                headings.add(h)
    return headings


def run_validate_markdown_headings(
    file_path: Path, fix: bool = True
) -> MarkdownHeadingsOutput:
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    filename = file_path.name
    template_name = filename.replace(".md", "_template.md")

    project_root = Path.cwd()

    template_paths = [
        project_root / "departments" / "discovery" / "contracts" / template_name,
        project_root / "departments" / "operations" / "contracts" / template_name,
    ]

    template_path = None
    for tp in template_paths:
        if tp.exists():
            template_path = tp
            break

    if not template_path:
        raise FileNotFoundError(
            f"Template not found for {filename} (searched for {template_name})"
        )

    with open(file_path, "r", encoding="utf-8") as f:
        target_content = f.read()

    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()

    target_headings = extract_headings(target_content)
    template_headings = extract_headings(template_content)

    missing = [h for h in template_headings if h not in target_headings]

    if missing:
        raise ValueError(f"Missing required headings from template: {missing}")

    return MarkdownHeadingsOutput(
        is_valid=True, missing_headings=[], template_path=str(template_path)
    )
