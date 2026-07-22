"""Measure the actual context cost of <call_tool> invocations by running them
against the real workspace and sizing stdout — a <read> tag's cost is the file's
size on disk, but a <call_tool> (e.g. query_discovery) has no file to size, so
static analysis alone always reports it as free. This closes that gap for the
subset of invocations we can safely and deterministically re-run.

Mirrors the exact rule logic.py's _calculate_file_list_kb already applies to
templated <read> paths:
  - Inside a <for_each> loop, every iteration's output actually lands in the
    same context — measured as "full": one unfiltered call (all domains/epics
    in a single shot, since query_discovery's --domain/--epic default to None
    = no filter) stands in for the cumulative total, without re-running once
    per real domain/epic.
  - Outside a loop, only one representative call happens — measured as the
    90th percentile size across real per-domain (or per-domain-per-epic) runs,
    same as a templated <read>'s p90 over its glob matches.
  - No placeholders at all — "single": just run it once, as-is.
"""

from __future__ import annotations
import re
import shlex
import subprocess
from pathlib import Path

from departments.operations.tools.shared.tool_parser import _norm
from ..core.utils import _invocation_subcommand

TIMEOUT_SECONDS = 20.0
MAX_SAMPLES = 25  # bound worst-case subprocess fan-out for domain x epic products

PLACEHOLDER_RE = re.compile(r"\{([^}]+)\}")
FLAG_PLACEHOLDER_RE = re.compile(r"--\S+\s+\{(domain|epic_name)\}")
SUPPORTED_PLACEHOLDERS = {"domain", "epic_name"}


def _domain_candidates(workspace_dir: Path) -> list[str]:
    domains_dir = workspace_dir / "domains"
    if not domains_dir.is_dir():
        return []
    return sorted(p.name for p in domains_dir.iterdir() if p.is_dir())


def _epic_candidates(workspace_dir: Path, domain: str) -> list[str]:
    epics_dir = workspace_dir / "domains" / domain / "epics"
    if not epics_dir.is_dir():
        return []
    return sorted(p.name for p in epics_dir.iterdir() if p.is_dir())


def _unfilter(invocation: str) -> str | None:
    """Strips "--flag {placeholder}" pairs for supported placeholders, giving
    the same command's full unfiltered invocation. None if an unsupported
    placeholder remains (never run it)."""
    stripped = FLAG_PLACEHOLDER_RE.sub("", invocation)
    if PLACEHOLDER_RE.search(stripped):
        return None
    return re.sub(r"\s+", " ", stripped).strip()


def _expand_samples(invocation: str, workspace_dir: Path) -> list[str]:
    """Concrete per-domain/per-epic invocation strings for p90 sampling."""
    placeholders = set(PLACEHOLDER_RE.findall(invocation))
    if not placeholders <= SUPPORTED_PLACEHOLDERS:
        return []
    domains = _domain_candidates(workspace_dir)
    if not domains:
        return []
    samples: list[str] = []
    if "epic_name" in placeholders:
        for d in domains:
            for e in _epic_candidates(workspace_dir, d):
                samples.append(
                    invocation.replace("{domain}", d).replace("{epic_name}", e)
                )
                if len(samples) >= MAX_SAMPLES:
                    return samples
    else:
        for d in domains:
            samples.append(invocation.replace("{domain}", d))
    return samples


def _existing_output_kb(patterns: list[str], project_root: Path) -> float | None:
    """Sizes the real on-disk file(s) a tool's declared `outputs:` point to —
    only for literal (non-glob) paths, where "the output" is one deterministic
    file (e.g. generate_pitch_deck's pitch_deck.html), never a glob spanning
    unrelated data (that's the situational-mutation case tool_type "write"
    already guards against without measuring). None if nothing exists yet
    (tool hasn't run in this workspace) — same as a <write> tag not yet
    produced, no contract-template fallback needed here since this only
    triggers as a real regeneration, not a partial-context estimate."""
    total = 0.0
    found = False
    for pattern in patterns:
        if pattern == "stdout" or "*" in pattern or "?" in pattern:
            continue
        p = project_root / pattern
        if p.is_file():
            total += p.stat().st_size / 1024
            found = True
    return total if found else None


def _run_kb(invocation: str, project_root: Path) -> float | None:
    try:
        tokens = shlex.split(invocation)
        result = subprocess.run(
            tokens,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        return len(result.stdout.encode("utf-8")) / 1024
    except Exception:
        return None


def _expand_calls_tools(
    calls_list: list[str] | None, tools_by_key: dict, records: list[dict]
) -> None:
    if not calls_list:
        return
    for callee_ref in calls_list:
        base_ref, sep, callee_sub = callee_ref.partition("::")
        actual_sub: str | None = callee_sub if callee_sub else None
        callee_tool = tools_by_key.get(_norm(base_ref))
        if callee_tool and actual_sub:
            records.append(
                {
                    "tool": callee_tool["name"],
                    "subcommand": actual_sub,
                    "invocation": f"__internal__ {callee_tool['name']} {actual_sub}",
                    "mode": "skipped",
                    "runs": 0,
                    "kb": 0.0,
                }
            )


def _handle_analyzer_invocation(
    invocation: str,
    inv: dict,
    project_root: Path,
    workspace_dir: Path,
    record: dict,
    records: list[dict],
) -> None:
    placeholders = set(PLACEHOLDER_RE.findall(invocation))

    if not placeholders:
        kb = _run_kb(invocation, project_root)
        if kb is not None:
            record.update(mode="single", runs=1, kb=round(kb, 2))
        records.append(record)
        return

    if inv.get("looped"):
        unfiltered = _unfilter(invocation)
        kb = _run_kb(unfiltered, project_root) if unfiltered else None
        if kb is not None:
            record.update(mode="full", runs=1, kb=round(kb, 2))
        records.append(record)
        return

    samples = _expand_samples(invocation, workspace_dir)
    sizes = [kb for kb in (_run_kb(s, project_root) for s in samples) if kb is not None]
    if sizes:
        sizes.sort()
        p90_idx = int(len(sizes) * 0.9) if len(sizes) > 1 else 0
        p90_kb = sizes[min(p90_idx, len(sizes) - 1)]
        record.update(mode="p90", runs=len(sizes), kb=round(p90_kb, 2))
    records.append(record)


def _process_invocation(
    inv: dict,
    tools_by_key: dict,
    project_root: Path,
    workspace_dir: Path,
    records: list[dict],
) -> None:
    if _norm(inv["tool"]) == "git":
        return
    tool = tools_by_key.get(_norm(inv["tool"]))

    invocation = inv["invocation"]
    raw_subcommand = _invocation_subcommand(invocation, tool) if tool else None
    subcommand = (
        raw_subcommand
        if tool and raw_subcommand in (tool.get("commands") or {})
        else None
    )
    record = {
        "tool": tool["name"] if tool else inv["tool"],
        "subcommand": subcommand,
        "invocation": invocation,
        "mode": "skipped",
        "runs": 0,
        "kb": 0.0,
    }
    if not tool:
        records.append(record)
        return

    cmd_meta = (tool.get("commands") or {}).get(subcommand) if subcommand else None

    if cmd_meta:
        _expand_calls_tools(cmd_meta.get("calls_tools"), tools_by_key, records)
    _expand_calls_tools(tool.get("calls_tools"), tools_by_key, records)

    if tool.get("tool_type") == "linter":
        records.append(record)
        return

    if cmd_meta and cmd_meta.get("outputs"):
        record.update(mode="write")
        records.append(record)
        return

    if tool.get("tool_type") != "analyzer":
        if not subcommand:
            kb = _existing_output_kb(tool.get("outputs", []), project_root)
            if kb is not None:
                record.update(mode="write", kb=round(kb, 2))
        records.append(record)
        return

    _handle_analyzer_invocation(
        invocation, inv, project_root, workspace_dir, record, records
    )


def measure_agent_tool_costs(
    agent: dict, tools_by_key: dict, project_root: Path, workspace_dir: Path
) -> list[dict]:
    """Returns one record per <call_tool> invocation: {tool, subcommand,
    invocation, mode, runs, kb}. `mode` is "single" (no placeholders, one
    call), "p90" (representative single call sampled across real entries),
    "full" (looped — cumulative total via one unfiltered call), "write" (the
    tool is never executed here — either a mutation subcommand, e.g.
    `rename-entity`, whose real output is situational and never sized; or a
    single-purpose generator/preprocessor/aggregator, e.g. generate_pitch_deck,
    whose one deterministic output file is sized directly off disk if it
    already exists — `kb` is 0.0 for the former, real for the latter), or
    "skipped"."""
    records: list[dict] = []
    for inv in agent.get("tool_invocations", []):
        _process_invocation(inv, tools_by_key, project_root, workspace_dir, records)
    return records
