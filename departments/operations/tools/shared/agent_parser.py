from __future__ import annotations
import re
import sys
from pathlib import Path


from departments.operations.tools.shared.parsers import split_zones, extract_xml_block


def extract_required_skills(block: str) -> list[str]:
    paths = []
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        content = line[2:].strip()
        path = re.split(r"[\s(]", content)[0]
        path = path.lstrip("./")
        if path.endswith(".md") or path.endswith(".yaml"):
            paths.append(path)
    return paths


HANDOFF_RE = re.compile(r"workspace/discovery/handoff/[\w-]+\.md")


def extract_handoff(body: str) -> str | None:
    escl_block = extract_xml_block(body, "escalation_protocol")
    match = HANDOFF_RE.search(escl_block)
    if match:
        return match.group(0)
    guard_block = extract_xml_block(body, "guardrails")
    match = HANDOFF_RE.search(guard_block)
    return match.group(0) if match else None


CALL_AGENT_RE = re.compile(r'<call_agent((?:\s+[\w-]+="[^"]*")*)\s*>')
CALL_TOOL_RE = re.compile(r'<call_tool\s+name="([^"]+)"')
CALL_TOOL_FULL_RE = re.compile(r'<call_tool\s+name="([^"]+)"\s*>([^<]*)</call_tool>')

READ_RE = re.compile(r'<read((?:\s+[\w-]+="[^"]*")*)\s*>\s*([^<]+?)\s*</read>')
WRITE_RE = re.compile(r'<write((?:\s+[\w-]+="[^"]*")*)\s*>\s*([^<]+?)\s*</write>')
FOR_EACH_RE = re.compile(
    r"<for_each\b([^>]*)>",
    re.DOTALL,
)
_FE_ATTR_RE = re.compile(r'(\w[\w-]*)="([^"]*)"')

ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')


def _parse_attrs(attr_str: str) -> dict:
    return dict(ATTR_RE.findall(attr_str or ""))


def extract_delegations(workflow_block: str) -> dict:
    """Scan <call_agent> tags for their `name` (and `optional`) attributes,
    order-agnostic (mirrors READ_RE/WRITE_RE parsing above — attributes like
    `optional="true"` or `condition="..."` may precede `name`). A subagent can
    be called from multiple workflow sites (base delegation, retries, gap-fix
    branches); dedup by name so each distinct target is one edge/row, while
    tracking whether *every* site that calls it is optional — a subagent only
    ever invoked from conditional branches is itself conditional overall."""
    names: list[str] = []
    optional_by_name: dict[str, bool] = {}
    for attr_str in CALL_AGENT_RE.findall(workflow_block):
        attrs = _parse_attrs(attr_str)
        name = attrs.get("name")
        if not name:
            continue
        is_optional = attrs.get("optional") == "true"
        if name not in optional_by_name:
            names.append(name)
            optional_by_name[name] = is_optional
        else:
            optional_by_name[name] = optional_by_name[name] and is_optional
    return {
        "delegates_to": names,
        "optional_delegates": [n for n in names if optional_by_name[n]],
    }


def extract_tool_calls(workflow_block: str) -> list[str]:
    return CALL_TOOL_RE.findall(workflow_block)


def extract_tool_invocations(workflow_block: str) -> list[dict]:
    """Pairs each <call_tool name="X">cli invocation text</call_tool> with its
    raw invocation string, so callers can resolve which subcommand of a
    multi-command tool (e.g. query_discovery) was actually invoked — the
    name="" attribute alone only identifies the tool, not the operation.
    Also flags whether the call sits inside a <for_each> loop (same distinction
    extract_reads_writes already makes for <read> tags): a looped call's cost
    accumulates once per iteration, a non-looped call is a single representative
    run, which matters for how its context cost should be aggregated."""
    looped: set[tuple[str, str]] = set()
    for match in re.finditer(r"<for_each.*?</for_each>", workflow_block, re.DOTALL):
        for name, text in CALL_TOOL_FULL_RE.findall(match.group(0)):
            looped.add((name, text.strip()))

    result = []
    for name, text in CALL_TOOL_FULL_RE.findall(workflow_block):
        inv = text.strip()
        result.append(
            {"tool": name, "invocation": inv, "looped": (name, inv) in looped}
        )
    return result


def extract_for_each(workflow_block: str) -> list[dict]:
    result = []
    for m in FOR_EACH_RE.finditer(workflow_block):
        attrs = dict(_FE_ATTR_RE.findall(m.group(1)))
        mc_raw = attrs.get("max_concurrent")
        result.append(
            {
                "collection": attrs.get("collection", ""),
                "item": attrs.get("item", ""),
                "execution": attrs.get("execution", ""),
                "max_concurrent": int(mc_raw) if mc_raw is not None else None,
            }
        )
    return result


def extract_reads_writes(workflow_block: str) -> dict:
    """Scan the whole <workflow> block for <read>/<write> tags (regex-based,
    same style as CALL_AGENT_RE/CALL_TOOL_RE above)."""
    reads: list[str] = []
    optional_reads: list[str] = []
    writes: list[str] = []
    optional_writes: list[str] = []
    write_contracts: dict[str, str] = {}
    write_conditions: dict[str, str] = {}
    looped_reads: list[str] = []
    looped_writes: list[str] = []

    for match in re.finditer(r"<for_each.*?</for_each>", workflow_block, re.DOTALL):
        for _attr_str, path in READ_RE.findall(match.group(0)):
            looped_reads.append(path.strip())
        for _attr_str, path in WRITE_RE.findall(match.group(0)):
            looped_writes.append(path.strip())

    for attr_str, path in READ_RE.findall(workflow_block):
        attrs = _parse_attrs(attr_str)
        path = path.strip()
        reads.append(path)
        if attrs.get("optional") == "true":
            optional_reads.append(path)

    for attr_str, path in WRITE_RE.findall(workflow_block):
        attrs = _parse_attrs(attr_str)
        path = path.strip()
        writes.append(path)
        if attrs.get("optional") == "true":
            optional_writes.append(path)
        if "contract" in attrs:
            write_contracts[path] = attrs["contract"]
        if "condition" in attrs:
            write_conditions[path] = attrs["condition"]

    return {
        "reads": list(dict.fromkeys(reads)),
        "optional_reads": list(dict.fromkeys(optional_reads)),
        "writes": list(dict.fromkeys(writes)),
        "optional_writes": list(dict.fromkeys(optional_writes)),
        "write_contracts": write_contracts,
        "write_conditions": write_conditions,
        "looped_reads": list(dict.fromkeys(looped_reads)),
        "looped_writes": list(dict.fromkeys(looped_writes)),
    }


def parse_agent(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = split_zones(text)

    skills_block = extract_xml_block(body, "required_skills")
    workflow_block = extract_xml_block(body, "workflow")

    io = extract_reads_writes(workflow_block)
    reads, optional_reads = io["reads"], io["optional_reads"]
    writes, optional_writes = io["writes"], io["optional_writes"]
    write_contracts = io["write_contracts"]
    write_conditions = io["write_conditions"]
    looped_reads = io["looped_reads"]
    looped_writes = io["looped_writes"]

    # remove self-loops: agent validates its own output → would create a cycle
    writes_set = set(writes)
    reads = [r for r in reads if r not in writes_set]
    optional_reads = [r for r in optional_reads if r not in writes_set]

    for_each = extract_for_each(workflow_block)

    # <subagents> block removed (redundant with <call_agent> tags in <workflow> —
    # verified 1:1 match across all agents before removal). Delegations now come
    # solely from the dynamic <call_agent> scan below.
    delegations_info = extract_delegations(workflow_block)
    delegations = delegations_info["delegates_to"]
    optional_delegates = delegations_info["optional_delegates"]

    handoff = extract_handoff(body)

    tools_raw = frontmatter.get("tools", [])
    sys_tools = (
        tools_raw if isinstance(tools_raw, list) else ([tools_raw] if tools_raw else [])
    )
    local_tools = extract_tool_calls(workflow_block)
    tool_invocations = extract_tool_invocations(workflow_block)

    return {
        "name": frontmatter["name"],
        "description": str(frontmatter.get("description", "")).strip(),
        "model": str(frontmatter.get("model", "unknown")),
        "temperature": float(frontmatter.get("temperature", 0.5)),
        "tools": [str(t) for t in sys_tools],
        "uses_tools": local_tools,
        "tool_invocations": tool_invocations,
        "source_file": str(path),
        "is_subagent": "subagents" in str(path),
        "required_skills": extract_required_skills(skills_block),
        "contracts": list(dict.fromkeys(write_contracts.values())),
        "write_contracts": write_contracts,
        "write_conditions": write_conditions,
        "reads": reads,
        "writes": writes,
        "optional_reads": optional_reads,
        "optional_writes": optional_writes,
        "looped_reads": looped_reads,
        "looped_writes": looped_writes,
        "delegates_to": delegations,
        "optional_delegates": optional_delegates,
        "escalation_handoff": handoff,
        "for_each": for_each,
    }


def parse_all(agents_dir: Path) -> list[dict]:
    if not agents_dir.is_dir():
        print(f"[ERROR] agents_dir does not exist: {agents_dir}", file=sys.stderr)
        raise FileNotFoundError(agents_dir)
    agents = []
    for md_file in sorted(agents_dir.glob("*.md")):
        try:
            agents.append(parse_agent(md_file))
        except Exception as exc:
            print(f"[WARN] Skipping {md_file.name}: {exc}", file=sys.stderr)
    subagents_dir = agents_dir / "subagents"
    if subagents_dir.is_dir():
        for md_file in sorted(subagents_dir.glob("*.md")):
            try:
                agents.append(parse_agent(md_file))
            except Exception as exc:
                print(
                    f"[WARN] Skipping subagents/{md_file.name}: {exc}", file=sys.stderr
                )
    return agents
