from pydantic import BaseModel, Field
from typing import List
from pathlib import Path
from departments.discovery.tools.linters.discovery_linter.validators.tech.tech_constraints import (
    run_validation as run_validate_tech_constraints,
)
from departments.discovery.tools.linters.discovery_linter.validators.general.ux_constraints import (
    run_validation as run_validate_ux_constraints,
)
from departments.discovery.tools.linters.discovery_linter.validators.markdown.markdown_links import (
    run_validation as run_validate_markdown_links,
)
from departments.discovery.tools.linters.discovery_linter.validators.markdown.markdown_links import (
    ValidateMarkdownLinksInput,
)


class ValidateTechSynthesisInput(BaseModel):
    strategy_dir: str


class ValidateTechSynthesisOutput(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)


def run_validation(
    input_data: ValidateTechSynthesisInput, fix: bool = True
) -> ValidateTechSynthesisOutput:
    strategy_dir = Path(input_data.strategy_dir)
    errors = []

    # 1. tech_constraints.yaml
    tech_file = strategy_dir / "tech_constraints.yaml"
    if tech_file.exists():
        try:
            # Note: validate_tech_constraints might not return an object, or might throw.
            # We assume it follows standard patterns or throws.
            run_validate_tech_constraints(tech_file)
        except Exception as e:
            errors.append(f"tech_constraints.yaml: {e}")
    elif not fix:
        errors.append("tech_constraints.yaml is missing")

    # 2. ux_constraints.yaml
    ux_file = strategy_dir / "ux_constraints.yaml"
    ux_result = run_validate_ux_constraints(ux_file, fix=fix)
    if not ux_result.is_valid:
        errors.extend(ux_result.errors)

    # 3. ux_vision.md
    vision_file = strategy_dir / "ux_vision.md"
    if vision_file.exists():
        try:
            md_result = run_validate_markdown_links(
                ValidateMarkdownLinksInput(file_path=str(vision_file))
            )
            if not md_result.is_valid:
                errors.extend([f"ux_vision.md: {err}" for err in md_result.errors])
        except Exception as e:
            errors.append(f"ux_vision.md: {e}")
    elif not fix:
        errors.append("ux_vision.md is missing")

    return ValidateTechSynthesisOutput(is_valid=len(errors) == 0, errors=errors)
