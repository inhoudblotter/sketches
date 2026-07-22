import re
from ..schemas import LintError


def check_guardrails_and_escalation(
    guardrails_block: str, escalation_block: str
) -> list[LintError]:
    errors = []

    if escalation_block:
        if not re.search(r"<triggers>", escalation_block):
            errors.append(
                LintError(
                    rule="Escalation Protocol",
                    message="Missing <triggers> block inside <escalation_protocol>",
                )
            )
        if not re.search(r"<action>", escalation_block):
            errors.append(
                LintError(
                    rule="Escalation Protocol",
                    message="Missing <action> block inside <escalation_protocol>",
                )
            )

        action_match = re.search(r"<action>(.*?)</action>", escalation_block, re.DOTALL)
        if action_match and "escalation_report_template.md" not in action_match.group(
            1
        ):
            errors.append(
                LintError(
                    rule="Escalation Protocol",
                    message="<action> block must contain a reference to 'escalation_report_template.md'",
                )
            )

    # Guardrails are required to exist, but the content should be agent-specific critical rules
    # We no longer enforce boilerplate like 'Traceability' or 'Escalation' here.
    if guardrails_block and (
        not guardrails_block.strip() or not re.search(r"<rule>", guardrails_block)
    ):
        errors.append(
            LintError(
                rule="Guardrails",
                message="<guardrails> block is empty or missing <rule> tags",
            )
        )

    return errors
