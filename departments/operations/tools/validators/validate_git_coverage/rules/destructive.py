"""DESTRUCTIVE_GIT_OP detector: flags git commands that discard working-tree
state, per the 'No Destructive Recovery' guardrail (agent_template.md) and
PIT-15 (skill-agentic-pitfalls.md) — these must never appear in an agent
prompt regardless of parallel/sequential context, since the only sanctioned
response to a git error is [ESCALATE]."""

from __future__ import annotations
import re

# Branch-like tokens: "develop", "discovery/tech-synthesizer", "-B <branch> <base>".
# A bare `git checkout <path>` where <path> looks like a file (has an extension,
# or is explicitly preceded by `--`) is destructive; `git checkout <branch>` or
# `git checkout -B <branch> <base>` is a safe branch switch/creation.
_EXT_RE = re.compile(r"\.[A-Za-z0-9]{1,5}$")


def find_destructive_ops(cmd: str) -> str | None:
    """Returns a human-readable reason string if `cmd` (a single 'git ...'
    invocation) is destructive, else None."""
    c = cmd.strip()
    reason = None

    if re.search(r"\bgit\s+add\s+(-A\b|\.(?:\s|$))", c):
        reason = "git add -A / git add . stages the entire working tree, including files unrelated to this agent's own writes (Scoped Commit guardrail)"
    elif re.search(r"\bgit\s+reset\s+--hard\b", c):
        reason = "git reset --hard discards uncommitted work (No Destructive Recovery guardrail)"
    elif re.search(r"\bgit\s+clean\b", c):
        reason = "git clean deletes untracked files, including artifacts other parallel agents may still be writing (PIT-15)"
    else:
        checkout_m = re.search(r"\bgit\s+checkout\s+(.*)", c)
        if checkout_m:
            rest = checkout_m.group(1).strip()
            if rest.startswith("--"):
                reason = "git checkout -- <path> discards local modifications to a path (No Destructive Recovery guardrail)"
            elif not (rest.startswith("-B") or rest.startswith("-b")):
                first_token = rest.split()[0] if rest.split() else ""
                if _EXT_RE.search(first_token) or first_token.startswith("workspace/"):
                    reason = "git checkout <path> (bare, not <branch>) silently discards local edits to that path (No Destructive Recovery guardrail)"

    return reason
