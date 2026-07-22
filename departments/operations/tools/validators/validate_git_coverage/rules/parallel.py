"""Parallel-context safety detectors.

PIT-15 / 'No Parallel Git Ops': a sub-agent is only allowed to self-commit
(`git add`/`git commit` inside its own <workflow>) if every orchestrator that
calls it always does so outside a parallel context — i.e. never inside a
`<for_each execution="parallel">` and never alongside another `<call_agent>`
in the same action block.

PIT-16 / 'Parallel Batch Cap': no more than 5 sub-agents may run concurrently
in a single batch. For <for_each execution="parallel"> this is enforced via the
mandatory `max_concurrent="N"` attribute (N ≤ 5). For explicit multi-agent
<action> blocks, the distinct call_agent count must not exceed 5.
"""

from __future__ import annotations
import re

CALL_AGENT_RE = re.compile(r'<call_agent\s+name="([^"]+)"')
FOR_EACH_BLOCK_RE = re.compile(r"<for_each\b([^>]*)>(.*?)</for_each>", re.DOTALL)
ACTION_BLOCK_RE = re.compile(r"<action\b[^>]*>(.*?)</action>", re.DOTALL)
_FE_ATTR_RE = re.compile(r'(\w[\w-]*)="([^"]*)"')

MAX_CONCURRENT_CAP = 5


def find_parallel_invoked_names(workflow_block: str) -> set[str]:
    """Returns the set of sub-agent names invoked in a parallel context
    somewhere in this orchestrator's workflow."""
    names: set[str] = set()

    for m in FOR_EACH_BLOCK_RE.finditer(workflow_block):
        names.update(CALL_AGENT_RE.findall(m.group(2)))

    # Also catch nested <for_each execution="parallel"> whose body contains
    # another <for_each> around the <call_agent> (e.g. ux-flow-architect.md's
    # domain x epic double loop) — FOR_EACH_BLOCK_RE with DOTALL already
    # captures the full nested body via group(2), so nested call_agents are
    # included above. Additionally: a single <action> block invoking more than
    # one distinct sub-agent name is a simultaneous batch even without
    # <for_each execution="parallel">.
    for m in ACTION_BLOCK_RE.finditer(workflow_block):
        block_names = CALL_AGENT_RE.findall(m.group(1))
        if len(set(block_names)) > 1:
            names.update(block_names)

    return names


def find_batch_cap_violations(workflow_block: str) -> list[dict]:
    """Returns a list of violation dicts for PIT-16 / Parallel Batch Cap.

    Each dict has:
      'kind'          — 'for_each_missing_cap' | 'for_each_cap_exceeded' | 'action_cap_exceeded'
      'max_concurrent' — the parsed value (int) or None if attribute is absent
      'agent_count'   — number of distinct agents in the batch (for action blocks)
    """
    violations: list[dict] = []

    for m in FOR_EACH_BLOCK_RE.finditer(workflow_block):
        attr_str = m.group(1)
        attrs = dict(_FE_ATTR_RE.findall(attr_str))
        if attrs.get("execution") != "parallel":
            continue
        mc_raw = attrs.get("max_concurrent")
        if mc_raw is None:
            violations.append(
                {
                    "kind": "for_each_missing_cap",
                    "max_concurrent": None,
                    "agent_count": None,
                }
            )
        else:
            try:
                mc = int(mc_raw)
            except ValueError:
                violations.append(
                    {
                        "kind": "for_each_missing_cap",
                        "max_concurrent": None,
                        "agent_count": None,
                    }
                )
                continue
            if mc > MAX_CONCURRENT_CAP:
                violations.append(
                    {
                        "kind": "for_each_cap_exceeded",
                        "max_concurrent": mc,
                        "agent_count": None,
                    }
                )

    for m in ACTION_BLOCK_RE.finditer(workflow_block):
        block_names = CALL_AGENT_RE.findall(m.group(1))
        distinct = len(set(block_names))
        if distinct > MAX_CONCURRENT_CAP:
            violations.append(
                {
                    "kind": "action_cap_exceeded",
                    "max_concurrent": None,
                    "agent_count": distinct,
                }
            )

    return violations
