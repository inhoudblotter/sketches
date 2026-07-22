"""Dead-asset detection (unused playbooks/tools/contracts, dangling contract
refs), split out of logic.run()."""

from __future__ import annotations
from collections import defaultdict
from pathlib import Path

from departments.operations.tools.shared.tool_parser import _norm
from ...schemas import LegacyAnalytics


def build_legacy(
    raw_agents: list[dict],
    raw_tools: list[dict],
    compositions: list[tuple],
    used_playbooks: set[str],
    department_root: Path,
) -> LegacyAnalytics:
    # Legacy analytics: assets on disk that the pipeline never actually
    # touches (playbooks nobody requires or references, tools nobody calls,
    # contract templates nobody's `contracts:` list points at).
    playbooks_dir = department_root / "playbooks"
    unused_playbooks = sorted(
        str(f)
        for f in (playbooks_dir.glob("*") if playbooks_dir.is_dir() else [])
        if f.is_file() and str(f) not in used_playbooks
    )

    # Linters are deliberately excluded from the graph (they validate, they
    # don't produce/mediate files), so graph node membership alone misses
    # them even when an agent explicitly <call_tool>s one. Resolve every
    # agent's raw tool-call names the same way graph_builder does, and also
    # follow tool-to-tool composition (a generator invoking its own linter).
    #
    # `unused_tools` must only ever report tools that belong to the department
    # being analyzed (meta.yaml `department:`) — tool_parser scans the whole
    # `departments/` tree, so cross-department infrastructure (e.g. an
    # operations-owned linter) would otherwise be flagged as "unused" simply
    # because no agent in *this* department's workflow calls it.
    department_name = department_root.name
    scoped_tools = [
        t
        for t in raw_tools
        if t.get("department") == department_name
        and t.get("entrypoint", "agent") != "manual"
    ]
    tools_by_key = {}
    for t in raw_tools:
        for key in t.get("match_keys", []) or [_norm(t["name"])]:
            tools_by_key[key] = t
    compositions_by_caller: dict[str, list[str]] = defaultdict(list)
    for caller_name, callee_name, _subcommand in compositions:
        compositions_by_caller[caller_name].append(callee_name)

    called_tool_names: set[str] = set()
    queue = []
    for a in raw_agents:
        for tool_name in a.get("uses_tools", []):
            tool = tools_by_key.get(_norm(tool_name))
            if tool:
                queue.append(tool["name"])
    while queue:
        curr = queue.pop()
        if curr in called_tool_names:
            continue
        called_tool_names.add(curr)
        queue.extend(compositions_by_caller.get(curr, []))

    unused_tools = sorted(
        t["name"] for t in scoped_tools if t["name"] not in called_tool_names
    )

    used_contracts = {c for a in raw_agents for c in a.get("contracts", [])}
    # Tools that write a file no agent's <write contract=...> ever declares
    # (e.g. extract_bounded_contexts) can still document that file's schema
    # via meta.yaml `contract:` — credit it the same as an agent write, but
    # only for tools actually reachable from the agent graph.
    used_contracts |= {
        t["contract"]
        for t in raw_tools
        if t.get("contract") and t["name"] in called_tool_names
    }
    contracts_dir = department_root / "contracts"
    unused_contracts = sorted(
        str(f)
        for f in (contracts_dir.glob("*") if contracts_dir.is_dir() else [])
        if f.is_file() and str(f) not in used_contracts
    )

    # A tool's meta.yaml `contract:` pointing at a file that no longer exists
    # (renamed/deleted template) is exactly the drift this field exists to
    # catch — check every declared contract, not just reachable tools, since
    # a dangling reference on an unused tool is still worth surfacing.
    dangling_contract_refs = sorted(
        {
            f"{t['name']}: {t['contract']}"
            for t in raw_tools
            if t.get("contract") and not Path(t["contract"]).is_file()
        }
    )

    return LegacyAnalytics(
        unused_playbooks=unused_playbooks,
        unused_tools=unused_tools,
        unused_contracts=unused_contracts,
        dangling_contract_refs=dangling_contract_refs,
    )
