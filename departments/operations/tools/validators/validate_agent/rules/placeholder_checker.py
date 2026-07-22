import re
from ..schemas import LintError

PLACEHOLDER_RE = re.compile(r"\{([\w-]+)\}")
FOR_EACH_RE = re.compile(r'<for_each[^>]*item="([^"]+)"')


def check_placeholders(
    workflow_block: str, invocation_contract: str, reads_and_writes: list[str]
) -> list[LintError]:
    errors = []

    # Extract declared placeholders
    declared = set()

    # {patch_name} is never bound via <for_each> or invocation_contract — the
    # orchestrator itself invents a free-form kebab-case name when it writes a
    # patch file (see skill-patch-protocol.md), then reuses that same literal
    # name across the read/write/call_tool/call_agent tags in the same step.
    declared.add("patch_name")

    for item in FOR_EACH_RE.findall(workflow_block):
        declared.add(item)

    if invocation_contract:
        for p in PLACEHOLDER_RE.findall(invocation_contract):
            declared.add(p)

    for path in reads_and_writes:
        used = PLACEHOLDER_RE.findall(path)
        for var in used:
            if var not in declared:
                errors.append(
                    LintError(
                        rule="Placeholder Binding",
                        message=f"Placeholder '{{{var}}}' in path '{path}' is not declared in <for_each> or <invocation_contract>",
                    )
                )

        # Canonical errata path is <scope_unit>/errata.yaml, e.g.
        # workspace/[dept]/domains/{domain}/epics/{epic_name}/errata.yaml (see
        # skill-agent-crafting.md, "Канонический паттерн errata-пути"). The
        # detail-level placeholder must be {epic_name}; {epic}/{issue_name} are not.
        if "errata" in path:
            wrong = {"epic", "issue_name"} & set(used)
            if wrong:
                errors.append(
                    LintError(
                        rule="Errata Path",
                        message=f"Errata path '{path}' must use {{epic_name}}, not {{{sorted(wrong)[0]}}}",
                    )
                )

    return errors
