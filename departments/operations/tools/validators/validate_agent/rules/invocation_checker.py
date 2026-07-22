import re
from ..schemas import LintError

CALL_AGENT_RE = re.compile(r'<call_agent\s+name="([^"]+)">([^<]+)</call_agent>')


def check_agent_calls(workflow_block: str) -> list[LintError]:
    errors: list[LintError] = []
    if not workflow_block:
        return errors

    for match in CALL_AGENT_RE.finditer(workflow_block):
        name = match.group(1)
        body = match.group(2).strip()

        # Check that it starts with WORKSPACE_ROOT: ... | COMMAND: ...
        # TARGET: is optional, but if present it should be formatted properly.
        if not re.match(r"^WORKSPACE_ROOT:\s*[^|]+\|\s*COMMAND:\s*[^|]+", body):
            errors.append(
                LintError(
                    rule="Invocation Format",
                    message=f"<call_agent name=\"{name}\"> body must strictly start with 'WORKSPACE_ROOT: ... | COMMAND: ...'. Found: '{body}'",
                )
            )

    return errors


def check_subagent_contract(
    invocation_contract: str, is_subagent: bool, filename: str
) -> list[LintError]:
    errors: list[LintError] = []
    if is_subagent and filename != "agent_template.md":
        if not invocation_contract:
            errors.append(
                LintError(
                    rule="Invocation Format",
                    message="Subagents must have an <invocation_contract> block.",
                )
            )
        elif (
            "WORKSPACE_ROOT:" not in invocation_contract
            or "COMMAND:" not in invocation_contract
        ):
            errors.append(
                LintError(
                    rule="Invocation Format",
                    message="<invocation_contract> must document the strict format: 'WORKSPACE_ROOT: ... | COMMAND: ...' (TARGET is optional).",
                )
            )
    return errors
