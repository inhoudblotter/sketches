from pathlib import Path
from .schemas import LintResult, LintError
from typing import Literal
from departments.operations.tools.shared.parsers import split_zones, extract_xml_block

from .rules.frontmatter_checker import check_frontmatter
from .rules.xml_sections_checker import check_xml_sections
from .rules.workflow_tags_checker import (
    check_workflow_tags,
    READ_RE,
    WRITE_RE,
)
from .rules.placeholder_checker import check_placeholders
from .rules.guardrails_checker import check_guardrails_and_escalation
from .rules.tool_call_checker import (
    get_valid_tool_names,
    check_tool_calls,
    check_tool_call_complexity,
)
from .rules.invocation_checker import check_agent_calls, check_subagent_contract
from departments.operations.tools.shared.tool_parser import (
    parse_all as parse_all_tools,
    parse_compositions,
    _norm,
    _matches_any,
)
import re

CALL_TOOL_RE = re.compile(r'<call_tool\s+name="([^"]+)"')


def _load_expanded_tools(
    workspace_dir: Path, tool_calls: list[str]
) -> tuple[list[dict], list[dict]]:
    all_tools = parse_all_tools(workspace_dir / "departments")
    tools_by_key = {}
    for t in all_tools:
        for key in t.get("match_keys", []):
            tools_by_key[key] = t

    compositions = parse_compositions(workspace_dir / "departments", all_tools)
    compositions_by_caller: dict[str, list[dict]] = {}
    for caller_name, callee_name, _subcommand in compositions:
        callee = next((t for t in all_tools if t["name"] == callee_name), None)
        if callee:
            compositions_by_caller.setdefault(caller_name, []).append(callee)

    # Resolve which tools this agent directly calls
    resolved_tools = []
    for t_name in tool_calls:
        tool_obj: dict | None = tools_by_key.get(_norm(t_name))
        if tool_obj:
            resolved_tools.append(tool_obj)

    # Expand the tool tree (linters called by other tools)
    expanded_tools = list(resolved_tools)
    seen_tool_names = {t["name"] for t in resolved_tools}
    queue = list(resolved_tools)
    while queue:
        caller = queue.pop()
        for callee in compositions_by_caller.get(caller["name"], []):
            if callee["name"] not in seen_tool_names:
                seen_tool_names.add(callee["name"])
                expanded_tools.append(callee)
                queue.append(callee)

    producer_tools = [t for t in expanded_tools if t.get("tool_type") != "linter"]
    linter_tools = [t for t in expanded_tools if t.get("tool_type") == "linter"]
    return producer_tools, linter_tools


def _validate_yaml_writes(
    yaml_writes: list[str],
    producer_tools: list[dict],
    linter_tools: list[dict],
    errors: list[LintError],
) -> None:
    for yw in yaml_writes:
        yw = yw.strip()
        # To handle placeholders like {scout_name} which are used as wildcard matches, replace {...} with *
        match_path = re.sub(r"\{[^}]+\}", "*", yw)

        is_tool_output = any(
            _matches_any(match_path, t.get("outputs", [])) for t in producer_tools
        )
        if is_tool_output:
            continue

        is_validated = False
        for linter in linter_tools:
            linter_inputs = list(linter.get("inputs", []))
            for cmd_data in linter.get("commands", {}).values():
                linter_inputs.extend(cmd_data.get("inputs", []))

            if _matches_any(match_path, linter_inputs):
                is_validated = True
                break
        if not is_validated:
            errors.append(
                LintError(
                    rule="YAML Validation",
                    message=f"YAML file '{yw}' is written but no called tool (or composed tool) validates it.",
                )
            )


def _check_yaml_validation(
    workflow_block: str,
    tool_calls: list[str],
    path: Path,
    workspace_dir: Path,
    errors: list[LintError],
) -> None:
    yaml_writes = [
        p for _, p in WRITE_RE.findall(workflow_block) if p.strip().endswith(".yaml")
    ]
    if not yaml_writes or path.name == "agent_template.md":
        return

    producer_tools, linter_tools = _load_expanded_tools(workspace_dir, tool_calls)
    _validate_yaml_writes(yaml_writes, producer_tools, linter_tools, errors)


def validate_file(path: Path) -> LintResult:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return LintResult(
            file_path=str(path),
            status="error",
            errors=[LintError(rule="File Read", message=str(e))],
        )

    try:
        frontmatter, body = split_zones(text)
    except ValueError as e:
        return LintResult(
            file_path=str(path),
            status="error",
            errors=[LintError(rule="Format", message=str(e))],
        )

    is_subagent = "subagents" in path.parts

    errors = []

    # 1. Frontmatter
    errors.extend(check_frontmatter(frontmatter))

    # 2. XML Sections
    errors.extend(check_xml_sections(body, is_subagent))

    workflow_block = extract_xml_block(body, "workflow")
    invocation_contract = extract_xml_block(body, "invocation_contract")
    guardrails_block = extract_xml_block(body, "guardrails")
    escalation_block = extract_xml_block(body, "escalation_protocol")

    # 3. Workflow Tags
    errors.extend(check_workflow_tags(workflow_block, body))

    # Extract all reads and writes for placeholder checking
    reads_and_writes = []
    for _, p in READ_RE.findall(workflow_block):
        reads_and_writes.append(p.strip())
    for _, p in WRITE_RE.findall(workflow_block):
        reads_and_writes.append(p.strip())

    # 4. Placeholders
    errors.extend(
        check_placeholders(workflow_block, invocation_contract, reads_and_writes)
    )

    # 5. Guardrails & Escalation
    errors.extend(check_guardrails_and_escalation(guardrails_block, escalation_block))

    # 5.5 Agent Invocations
    errors.extend(check_agent_calls(workflow_block))
    errors.extend(check_subagent_contract(invocation_contract, is_subagent, path.name))

    # 6. Tool Calls
    # Find workspace dir by going up until we find "departments"
    workspace_dir = path
    while workspace_dir.name != "departments" and workspace_dir.parent != workspace_dir:
        workspace_dir = workspace_dir.parent
    workspace_dir = (
        workspace_dir.parent
    )  # Go up one more to reach the root containing "departments"

    valid_tools = get_valid_tool_names(workspace_dir)
    tool_calls = CALL_TOOL_RE.findall(workflow_block)
    errors.extend(check_tool_calls(tool_calls, valid_tools))
    errors.extend(check_tool_call_complexity(workflow_block))

    # 7. YAML validation check
    _check_yaml_validation(workflow_block, tool_calls, path, workspace_dir, errors)

    status: Literal["error", "ok"] = "error" if errors else "ok"
    return LintResult(file_path=str(path), status=status, errors=errors)
