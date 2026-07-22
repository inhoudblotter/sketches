import re
from ..schemas import LintError

READ_RE = re.compile(r'<read((?:\s+[\w-]+="[^"]*")*)\s*>\s*([^<]+?)\s*</read>')
WRITE_RE = re.compile(r'<write((?:\s+[\w-]+="[^"]*")*)\s*>\s*([^<]+?)\s*</write>')
FOR_EACH_RE = re.compile(r"<for_each\b([^>]*)>", re.DOTALL)
ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')


def _parse_attrs(attr_str: str) -> dict:
    return dict(ATTR_RE.findall(attr_str or ""))


MAX_CONCURRENT_LIMIT = 5


def _check_tags_outside_workflow(
    workflow_block: str, full_body: str, errors: list[LintError]
) -> None:
    tags_to_check = ["read", "write", "call_tool", "call_agent", "for_each"]
    workflow_start = full_body.find("<workflow>")
    workflow_end = full_body.find("</workflow>")

    if workflow_start != -1 and workflow_end != -1:
        outside_body = full_body[:workflow_start] + full_body[workflow_end:]
        for tag in tags_to_check:
            for m in re.finditer(rf"<{tag}\b", outside_body):
                if m.start() > 0 and outside_body[m.start() - 1] == "`":
                    continue
                errors.append(
                    LintError(
                        rule="Workflow Tags",
                        message=f"Tag <{tag}> used outside of <workflow> block.",
                    )
                )
                break


def _check_reads_writes(workflow_block: str, errors: list[LintError]) -> None:
    for _attr_str, path in READ_RE.findall(workflow_block):
        path = path.strip()
        if "," in path:
            errors.append(
                LintError(
                    rule="Workflow Tags", message=f"Comma found in <read> path: {path}"
                )
            )
        if "*" in path:
            errors.append(
                LintError(
                    rule="Workflow Tags",
                    message=f"Glob '*' found in <read> path: {path}",
                )
            )

    for attr_str, path in WRITE_RE.findall(workflow_block):
        path = path.strip()
        if "," in path:
            errors.append(
                LintError(
                    rule="Workflow Tags", message=f"Comma found in <write> path: {path}"
                )
            )
        if "*" in path:
            errors.append(
                LintError(
                    rule="Workflow Tags",
                    message=f"Glob '*' found in <write> path: {path}",
                )
            )

        attrs = _parse_attrs(attr_str)
        if attrs.get("optional") == "true" and "condition" not in attrs:
            errors.append(
                LintError(
                    rule="Workflow Tags",
                    message=f"<write optional='true'> missing 'condition' attribute for path: {path}",
                )
            )


def _check_for_each(workflow_block: str, errors: list[LintError]) -> None:
    for m in FOR_EACH_RE.finditer(workflow_block):
        attrs = _parse_attrs(m.group(1))
        if attrs.get("execution") != "parallel":
            continue
        mc_raw = attrs.get("max_concurrent")
        if mc_raw is None:
            errors.append(
                LintError(
                    rule="Workflow Tags",
                    message="<for_each execution='parallel'> is missing mandatory `max_concurrent` attribute (PIT-16).",
                )
            )
        else:
            try:
                mc = int(mc_raw)
                if mc < 1 or mc > MAX_CONCURRENT_LIMIT:
                    errors.append(
                        LintError(
                            rule="Workflow Tags",
                            message=f"<for_each execution='parallel' max_concurrent='{mc_raw}'> — value must be 1–{MAX_CONCURRENT_LIMIT} (PIT-16).",
                        )
                    )
            except ValueError:
                errors.append(
                    LintError(
                        rule="Workflow Tags",
                        message=f"<for_each execution='parallel' max_concurrent='{mc_raw}'> — value must be an integer.",
                    )
                )


def check_workflow_tags(workflow_block: str, full_body: str) -> list[LintError]:
    errors: list[LintError] = []
    _check_tags_outside_workflow(workflow_block, full_body, errors)
    _check_reads_writes(workflow_block, errors)
    _check_for_each(workflow_block, errors)
    return errors
