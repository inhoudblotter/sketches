import re
from ..schemas import LintError


def check_balanced_xml_tags(body: str) -> list[LintError]:
    errors = []
    # Mask out fenced code blocks
    masked_body = re.sub(
        r"```.*?```", lambda m: "X" * len(m.group(0)), body, flags=re.DOTALL
    )
    # Mask out inline code blocks
    masked_body = re.sub(r"`[^`]*`", lambda m: "X" * len(m.group(0)), masked_body)

    tag_pattern = re.compile(r"<(/?)([a-zA-Z0-9_-]+)(?:\s+[^>]*?)?>")

    stack = []
    for match in tag_pattern.finditer(masked_body):
        is_closing = bool(match.group(1))
        tag_name = match.group(2)

        if not is_closing:
            stack.append((tag_name, match.start()))
        elif not stack:
            errors.append(
                LintError(
                    rule="XML Markup",
                    message=f"Found closing tag </{tag_name}> without an opening tag.",
                )
            )
        else:
            top_tag, _ = stack[-1]
            if top_tag != tag_name:
                errors.append(
                    LintError(
                        rule="XML Markup",
                        message=f"Mismatched closing tag: expected </{top_tag}>, but found </{tag_name}>.",
                    )
                )
                # Try to recover by popping
                popped = False
                for i in range(len(stack) - 1, -1, -1):
                    if stack[i][0] == tag_name:
                        del stack[i:]
                        popped = True
                        break
                if not popped:
                    pass  # Ignore if it doesn't match anything
            else:
                stack.pop()

    for unclosed_tag, _ in stack:
        errors.append(
            LintError(rule="XML Markup", message=f"Unclosed tag: <{unclosed_tag}>.")
        )

    return errors


def check_xml_sections(
    body: str, is_subagent: bool, file_name: str = ""
) -> list[LintError]:
    errors = []

    required_sections = [
        "role",
        "required_skills",
        "guardrails",
        "output_format",
        "workflow",
        "escalation_protocol",
    ]

    for sec in required_sections:
        if sec == "required_skills" and file_name == "tech-lead.md":
            continue
        if not re.search(rf"<{sec}>", body):
            errors.append(
                LintError(
                    rule="XML Sections", message=f"Missing required section: <{sec}>"
                )
            )

    if not is_subagent and not re.search(r"<mindset>", body):
        errors.append(
            LintError(
                rule="XML Sections",
                message="Missing <mindset> section (required for standalone agents)",
            )
        )

    forbidden_sections = {
        "inputs": "Use <read> inside <workflow> instead.",
        "outputs": "Use <write> inside <workflow> instead.",
        "contracts": 'Use <write contract="..."> inside <workflow> instead.',
        "subagents": "Redundant with <call_agent> tags inside <workflow> — remove it.",
    }
    for sec, hint in forbidden_sections.items():
        if re.search(rf"<{sec}>", body):
            errors.append(
                LintError(
                    rule="XML Sections",
                    message=f"Forbidden section used: <{sec}>. {hint}",
                )
            )

    errors.extend(check_balanced_xml_tags(body))

    return errors
