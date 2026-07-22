"""validate-git-coverage: static checker for the git-safety guardrails in
departments/operations/contracts/agent_template.md (Scoped Commit / No
Autonomous Commit / No Parallel Git Ops / No Destructive Recovery / Parallel
Batch Cap) and PIT-15, PIT-16 (skill-agentic-pitfalls.md).

Given a `departments/<dept>/staff` directory, parses every orchestrator and
sub-agent .md file and reports five finding categories:

  MISSING_COMMIT                   — an artifact (<write> or artifact-producing
                                      <call_tool>) is never covered by a `git add`
                                      (in its own file or a directly-called
                                      sub-agent) before the file's own
                                      `git checkout <branch> && git merge` step.
  PATH_MISMATCH                    — a `git add` path doesn't match any known
                                      write/tool-output path (typo/stale-rename).
  STILL_SELF_COMMITS_BUT_PARALLEL  — a sub-agent self-commits but is invoked
                                      from a parallel context by some orchestrator.
  DESTRUCTIVE_GIT_OP               — git add -A/., git reset --hard, git clean,
                                      or a bare `git checkout <path>`.
  BATCH_CAP_EXCEEDED               — a <for_each execution="parallel"> is missing
                                      the mandatory `max_concurrent` attribute, or
                                      its value exceeds 5 (PIT-16).

Design note: built as a standalone sibling tool (matching validate_agent's
structure) rather than folding into pipeline_analysis. pipeline_analysis
builds a whole-repo dependency graph/analytics report (ARTIFACTS.md, metrics,
contract drift) — a different audience (humans browsing the pipeline) and a
different failure mode (informational, not exit-code-gated per file). This
tool is a fast, single-purpose CI gate in the validate_agent/validate_revenue_model
mold: one exit code, one file-by-file report, no graph construction needed.
It does reuse agent_parser and tool_parser (the same shared parsing layer
pipeline_analysis's graph_builder uses) so the two tools never disagree about
what an agent's writes/tool-outputs/delegations are.
"""

from __future__ import annotations
import re
from pathlib import Path

from departments.operations.tools.shared import agent_parser, tool_parser
from departments.operations.tools.shared.parsers import split_zones, extract_xml_block

from .schemas import Finding, GitCoverageResult
from .rules.artifacts import (
    build_tool_index,
    extract_artifact_producers,
    path_is_covered,
)
from .rules.git_actions import (
    extract_git_actions,
    is_merge_command,
    is_add_command,
    extract_add_paths,
)
from .rules.destructive import find_destructive_ops
from .rules.parallel import find_parallel_invoked_names, find_batch_cap_violations

COMMIT_RE = re.compile(r"\bgit\s+commit\b")


def _project_root(staff_dir: Path) -> Path:
    """Walk up from a staff/ dir to the repo root (the parent of departments/)."""
    p = staff_dir.resolve()
    while p.name != "departments" and p.parent != p:
        p = p.parent
    return p.parent


def _read_workflow(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    _, body = split_zones(text)
    return extract_xml_block(body, "workflow")


def _path_covers_any(add_path: str, known_paths: list[str]) -> bool:
    """Does this single git-add path/prefix cover at least one known
    artifact-producing path?"""
    return any(path_is_covered(kp, [add_path]) for kp in known_paths)


def _check_destructive_git_op(agents, git_actions_by_name, findings):
    for a in agents:
        for action in git_actions_by_name[a["name"]]:
            for cmd in action["commands"]:
                reason = find_destructive_ops(cmd)
                if reason:
                    findings.append(
                        Finding(
                            category="DESTRUCTIVE_GIT_OP",
                            file_path=a["source_file"],
                            message=f"Destructive git operation: `{cmd}`",
                            detail=reason,
                        )
                    )


def _check_still_self_commits(
    agents,
    git_actions_by_name,
    parallel_targets_by_name,
    all_parallel_invoked,
    findings,
):
    for a in agents:
        if not a["is_subagent"]:
            continue
        name = a["name"]
        self_commit_cmds = [
            c
            for action in git_actions_by_name[name]
            for c in action["commands"]
            if is_add_command(c) or COMMIT_RE.search(c)
        ]
        if not self_commit_cmds or name not in all_parallel_invoked:
            continue
        callers = sorted(
            caller
            for caller, names in parallel_targets_by_name.items()
            if name in names
        )
        findings.append(
            Finding(
                category="STILL_SELF_COMMITS_BUT_PARALLEL",
                file_path=a["source_file"],
                message=(
                    f"Sub-agent '{name}' self-commits ({self_commit_cmds[0]!r}) but is invoked in a "
                    f"parallel context by: {', '.join(callers)}."
                ),
                detail="PIT-15 / No Parallel Git Ops",
            )
        )


def _check_batch_cap(agents, workflow_by_name, findings):
    for a in agents:
        name = a["name"]
        wf = workflow_by_name[name]
        for v in find_batch_cap_violations(wf):
            if v["kind"] == "for_each_missing_cap":
                findings.append(
                    Finding(
                        category="BATCH_CAP_EXCEEDED",
                        file_path=a["source_file"],
                        message=(
                            f"Agent '{name}' has <for_each execution=\"parallel\"> without "
                            f'`max_concurrent` attribute — add `max_concurrent="5"` (or less).'
                        ),
                        detail="PIT-16 / Parallel Batch Cap",
                    )
                )
            elif v["kind"] == "for_each_cap_exceeded":
                findings.append(
                    Finding(
                        category="BATCH_CAP_EXCEEDED",
                        file_path=a["source_file"],
                        message=(
                            f"Agent '{name}' has <for_each execution=\"parallel\"> with "
                            f'`max_concurrent="{v["max_concurrent"]}"` — must be ≤ 5.'
                        ),
                        detail="PIT-16 / Parallel Batch Cap",
                    )
                )
            elif v["kind"] == "action_cap_exceeded":
                findings.append(
                    Finding(
                        category="BATCH_CAP_EXCEEDED",
                        file_path=a["source_file"],
                        message=(
                            f"Agent '{name}' invokes {v['agent_count']} distinct sub-agents "
                            f"concurrently in a single <action> block — max 5 allowed."
                        ),
                        detail="PIT-16 / Parallel Batch Cap",
                    )
                )


def _collect_add_paths(actions, merge_pos):
    own_add_paths: list[str] = []
    for act in actions:
        if act["start"] >= merge_pos:
            continue
        for c in act["commands"]:
            if is_add_command(c):
                own_add_paths.extend(extract_add_paths(c))
    return own_add_paths


def _collect_delegated_info(a, git_actions_by_name, producers_by_name):
    delegated_add_paths: list[str] = []
    delegated_producers = []
    for dep_name in a["delegates_to"]:
        for act in git_actions_by_name.get(dep_name, []):
            for c in act["commands"]:
                if is_add_command(c):
                    delegated_add_paths.extend(extract_add_paths(c))
        delegated_producers.extend(producers_by_name.get(dep_name, []))
    return delegated_add_paths, delegated_producers


def _check_missing_commits(agents, git_actions_by_name, producers_by_name, findings):
    for a in agents:
        name = a["name"]
        actions = git_actions_by_name[name]
        merge_starts = [
            act["start"]
            for act in actions
            if any(is_merge_command(c) for c in act["commands"])
        ]
        if not merge_starts:
            continue  # not an orchestrator that merges back into develop
        merge_pos = min(merge_starts)

        own_add_paths = _collect_add_paths(actions, merge_pos)
        delegated_add_paths, delegated_producers = _collect_delegated_info(
            a, git_actions_by_name, producers_by_name
        )

        all_add_paths = own_add_paths + delegated_add_paths
        own_producers = producers_by_name[name]
        all_producers = own_producers + delegated_producers
        known_paths = [p["path"] for p in all_producers]

        for p in all_producers:
            if not path_is_covered(p["path"], all_add_paths):
                findings.append(
                    Finding(
                        category="MISSING_COMMIT",
                        file_path=a["source_file"],
                        message=(
                            f"Artifact '{p['path']}' (from {p['source']}) is never covered by any "
                            f"`git add` in this file or a called sub-agent before the "
                            f"`git checkout <branch> && git merge` step."
                        ),
                    )
                )

        for add_path in dict.fromkeys(all_add_paths):  # dedupe, keep order
            if not _path_covers_any(add_path, known_paths):
                findings.append(
                    Finding(
                        category="PATH_MISMATCH",
                        file_path=a["source_file"],
                        message=(
                            f"`git add {add_path}` references a path with no matching <write>/tool-output "
                            f"in this file or its called sub-agents (possible typo or stale rename)."
                        ),
                    )
                )


def analyze(staff_dir: Path) -> GitCoverageResult:
    staff_dir = Path(staff_dir)
    project_root = _project_root(staff_dir)

    agents = agent_parser.parse_all(staff_dir)
    if not agents:
        return GitCoverageResult(files_checked=[], findings=[])

    all_tools = tool_parser.parse_all(project_root / "departments")
    tool_index = build_tool_index(all_tools)

    workflow_by_name: dict[str, str] = {}
    files_checked: list[str] = []
    for a in agents:
        workflow_by_name[a["name"]] = _read_workflow(Path(a["source_file"]))
        files_checked.append(a["source_file"])

    git_actions_by_name = {
        name: extract_git_actions(wf) for name, wf in workflow_by_name.items()
    }
    producers_by_name = {
        name: extract_artifact_producers(wf, tool_index)
        for name, wf in workflow_by_name.items()
    }
    parallel_targets_by_name = {
        name: find_parallel_invoked_names(wf) for name, wf in workflow_by_name.items()
    }
    all_parallel_invoked: set[str] = set()
    for names in parallel_targets_by_name.values():
        all_parallel_invoked |= names

    findings: list[Finding] = []

    _check_destructive_git_op(agents, git_actions_by_name, findings)
    _check_still_self_commits(
        agents,
        git_actions_by_name,
        parallel_targets_by_name,
        all_parallel_invoked,
        findings,
    )
    _check_batch_cap(agents, workflow_by_name, findings)
    _check_missing_commits(agents, git_actions_by_name, producers_by_name, findings)

    findings.sort(key=lambda f: (f.file_path, f.category, f.message))
    return GitCoverageResult(files_checked=sorted(files_checked), findings=findings)
