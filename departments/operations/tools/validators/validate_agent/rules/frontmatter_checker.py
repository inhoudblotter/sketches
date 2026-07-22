from ..schemas import LintError


def check_frontmatter(frontmatter: dict) -> list[LintError]:
    errors = []
    required_fields = ["name", "description", "model"]
    for field in required_fields:
        if field not in frontmatter:
            errors.append(
                LintError(
                    rule="Frontmatter", message=f"Missing required field: {field}"
                )
            )
    return errors
