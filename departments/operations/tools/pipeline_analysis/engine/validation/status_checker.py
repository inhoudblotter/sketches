"""Determine per-agent status based on filesystem state."""

from __future__ import annotations
import re
from pathlib import Path

import networkx as nx

from departments.operations.tools.shared.tool_parser import _norm
from ..core.utils import _invocation_subcommand

_TEMPLATE_VAR_RE = re.compile(r"\{[^}]+\}")


def _artifact_exists(path_str: str, project_root: Path) -> bool:
    # Unresolved for_each templates (e.g. "domains/{domain}/dictionary.yaml")
    # never exist as a literal path — they only make sense as a glob over
    # whichever concrete instances (domains, epics, ...) are already on disk.
    # Checking the literal string would permanently BLOCK the agent even when
    # every real instance is present, so glob-match instead.
    if "{" in path_str:
        pattern = _TEMPLATE_VAR_RE.sub("*", path_str)
        return any(
            m.is_file() and m.stat().st_size > 0 for m in project_root.glob(pattern)
        )
    p = Path(path_str)
    if not p.is_absolute():
        p = project_root / path_str
    return p.exists() and p.stat().st_size > 0


def _owning_agent(tool_or_agent_node: str, G: nx.DiGraph) -> str | None:
    """If the node is a tool, resolve it to the agent that calls it."""
    if G.nodes.get(tool_or_agent_node, {}).get("node_type") != "tool":
        return tool_or_agent_node
    for u, _, d in G.in_edges(tool_or_agent_node, data=True):
        if (
            d.get("edge_type") in ("uses_tool", "calls_tool")
            and G.nodes.get(u, {}).get("node_type") == "agent"
        ):
            return u
    return None


def _is_own_subagent_output(agent_name: str, artifact_path: str, G: nx.DiGraph) -> bool:
    """True if `artifact_path` is produced by `agent_name` itself or by one of
    its (possibly nested) subagents. Orchestrators routinely declare a
    <read> for a file their own delegated subagent writes — that's a
    self-contained step of their own execution, not a cross-agent blocker,
    so it shouldn't count as BLOCKED just because the subagent hasn't run yet."""
    if artifact_path not in G:
        return False
    writers = {
        _owning_agent(u, G)
        for u, _, d in G.in_edges(artifact_path, data=True)
        if d.get("edge_type") in ("writes", "produces")
    }
    writers.discard(None)

    for writer in writers:
        if writer == agent_name:
            return True
        seen = {writer}
        queue = [writer]
        while queue:
            curr = queue.pop()
            for u, _, d in G.in_edges(curr, data=True):
                if d.get("edge_type") == "delegates" and u not in seen:
                    if u == agent_name:
                        return True
                    seen.add(u)
                    queue.append(u)
    return False


def _build_write_nodes_by_normalized(G: nx.DiGraph) -> dict[str, list[str]]:
    """Maps a write path's `{var}` -> `*` normalized form to the raw (still-
    templated) path(s) that produce it, so a tool's declared `inputs:` glob
    (already written with literal `*`, e.g. "domains/*/epics/*/flows/*.yaml")
    can be matched back to the <write> tag(s) — and hence the writer agent —
    that produce that same shape of file."""
    by_normalized: dict[str, list[str]] = {}
    for node, data in G.nodes(data=True):
        if data.get("node_type") == "tool":
            continue
        if not any(
            d.get("edge_type") in ("writes", "produces")
            for _, _, d in G.in_edges(node, data=True)
        ):
            continue
        by_normalized.setdefault(_TEMPLATE_VAR_RE.sub("*", node), []).append(node)
    return by_normalized


def _missing_tool_inputs(
    agent: dict,
    name: str,
    tools_by_key: dict[str, dict],
    write_nodes_by_normalized: dict[str, list[str]],
    G: nx.DiGraph,
    project_root: Path,
) -> list[str]:
    """A dependency expressed via `<call_tool>` (e.g. `query-discovery flows
    workspace/`) rather than a `<read>` tag is otherwise invisible to BLOCKED
    detection below — the agent shows READY even though the data it queries
    (e.g. flows/*.yaml, written by a *different* agent's subagent) doesn't
    exist yet. Mirrors the <read> check: a subcommand's declared `inputs:`
    glob with zero real matches counts as missing, unless every file that
    shape would come from is this agent's own (sub)agent's output."""
    missing: list[str] = []
    seen_patterns: set[str] = set()
    for inv in agent.get("tool_invocations", []):
        if _norm(inv["tool"]) == "git":
            continue
        tool = tools_by_key.get(_norm(inv["tool"]))
        if not tool or tool.get("tool_type") == "linter":
            continue
        subcommand = _invocation_subcommand(inv["invocation"], tool)
        cmd_meta = (tool.get("commands") or {}).get(subcommand) if subcommand else None
        for pattern in (cmd_meta or {}).get("inputs", []):
            if pattern == "stdout" or pattern in seen_patterns:
                continue
            seen_patterns.add(pattern)
            if any(
                m.is_file() and m.stat().st_size > 0 for m in project_root.glob(pattern)
            ):
                continue
            writers = write_nodes_by_normalized.get(pattern, [])
            if writers and all(_is_own_subagent_output(name, w, G) for w in writers):
                continue
            missing.append(pattern)
    return missing


def check_all(
    agents: list[dict],
    G: nx.DiGraph,
    workspace_dir: Path,
    tools: list[dict] | None = None,
) -> dict[str, dict]:
    """Return {agent_name: {status, blocked_on}}."""
    project_root = Path.cwd()
    results: dict[str, dict] = {}

    tools_by_key: dict[str, dict] = {}
    for t in tools or []:
        for key in t.get("match_keys", []) or [_norm(t["name"])]:
            tools_by_key[key] = t
    write_nodes_by_normalized = _build_write_nodes_by_normalized(G)

    for agent in agents:
        name = agent["name"]
        handoff = agent.get("escalation_handoff")
        reads = agent.get("reads", [])
        writes = agent.get("writes", [])

        if handoff and _artifact_exists(handoff, project_root):
            results[name] = {"status": "ESCALATED", "blocked_on": []}
            continue

        if not reads and not writes:
            results[name] = {"status": "UNKNOWN", "blocked_on": []}
            continue

        missing_reads = [
            r
            for r in reads
            if not _artifact_exists(r, project_root)
            and r not in agent.get("optional_reads", [])
            and not _is_own_subagent_output(name, r, G)
        ]
        missing_reads += _missing_tool_inputs(
            agent, name, tools_by_key, write_nodes_by_normalized, G, project_root
        )

        if missing_reads:
            results[name] = {"status": "BLOCKED", "blocked_on": missing_reads}
            continue

        required_writes = [
            w for w in writes if w not in agent.get("optional_writes", [])
        ]
        writes_done = [w for w in required_writes if _artifact_exists(w, project_root)]

        # If there are no required writes, assume DONE if it's not blocked. Otherwise check completion of required writes.
        if (not required_writes and writes) or (
            required_writes and len(writes_done) == len(required_writes)
        ):
            results[name] = {"status": "DONE", "blocked_on": []}
        else:
            results[name] = {"status": "READY", "blocked_on": []}

    return results
