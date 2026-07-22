"""Extraction of literal git command strings from a <workflow> block, in
document order, so callers can answer ordering questions like "does a later
git add step cover this earlier write?".

Git actions in this codebase's agent prompts are always expressed as
`<call_tool name="git">...literal shell text...</call_tool>` (see
departments/discovery/staff/*.md). We deliberately regex directly for
name="git" rather than reusing agent_parser.extract_tool_invocations, because
we need the byte offset (span) of each call within the raw workflow text to
order it against <write> tags and other <call_tool> calls.
"""

from __future__ import annotations
import re

GIT_CALL_RE = re.compile(r'<call_tool\s+name="git"\s*>(.*?)</call_tool>', re.DOTALL)

# Split a compound shell action ("git add X && git commit -m '...' && git push")
# into individual git invocations, keeping order.
GIT_CMD_SPLIT_RE = re.compile(r"\bgit\s+[^&]*")


def extract_git_actions(workflow_block: str) -> list[dict]:
    """Returns ordered list of {"raw": full <call_tool> text, "start": offset,
    "commands": [individual 'git ...' sub-commands, in order]}."""
    actions = []
    for m in GIT_CALL_RE.finditer(workflow_block):
        raw = m.group(1).strip()
        commands = [c.strip() for c in GIT_CMD_SPLIT_RE.findall(raw)]
        actions.append({"raw": raw, "start": m.start(), "commands": commands})
    return actions


def is_merge_command(cmd: str) -> bool:
    return bool(re.search(r"\bgit\s+merge\b", cmd))


def is_add_command(cmd: str) -> bool:
    return bool(re.search(r"\bgit\s+add\b", cmd))


def extract_add_paths(cmd: str) -> list[str]:
    """Pull the path tokens out of a 'git add <path1> <path2> ...' command,
    stopping at the next flag/subcommand (e.g. '&&' has already been split off
    by extract_git_actions)."""
    m = re.match(r"\s*git\s+add\s+(.*)", cmd)
    if not m:
        return []
    rest = m.group(1)
    tokens = [t for t in rest.split() if t and not t.startswith("-")]
    # Prose shorthand like "git add domains/{domain_1}/ domains/{domain_2}/ ..."
    # (literally "..." meaning "and so on for every domain") is not a path.
    return [t for t in tokens if t.strip(".") != ""]
