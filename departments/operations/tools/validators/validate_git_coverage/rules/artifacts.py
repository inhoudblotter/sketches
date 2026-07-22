"""Resolves every artifact-producing action in a <workflow> block — both
<write> tags and <call_tool> invocations of tools with a declared `outputs:`
in their meta.yaml (e.g. build_project_analytics, extract_bounded_contexts) —
into an ordered list of (path, position) pairs, so the coverage checker can
ask "was this path git-added before the merge step further down the file?"
"""

from __future__ import annotations
import re

from departments.operations.tools.shared.tool_parser import _norm, _matches_any

WRITE_RE = re.compile(r'<write(?:\s+[\w-]+="[^"]*")*\s*>\s*([^<]+?)\s*</write>')
CALL_TOOL_FULL_RE = re.compile(r'<call_tool\s+name="([^"]+)"\s*>([^<]*)</call_tool>')


def build_tool_index(all_tools: list[dict]) -> dict:
    """match_key -> tool dict, for tools that declare outputs."""
    idx = {}
    for t in all_tools:
        if not t.get("outputs"):
            continue
        for key in t.get("match_keys", []):
            idx[key] = t
    return idx


def extract_artifact_producers(workflow_block: str, tool_index: dict) -> list[dict]:
    """Ordered (by position in the raw workflow text) list of
    {"path": str, "start": int, "source": "write" | "tool:<tool-name>"}."""
    producers = []

    for m in WRITE_RE.finditer(workflow_block):
        producers.append(
            {"path": m.group(1).strip(), "start": m.start(), "source": "write"}
        )

    for m in CALL_TOOL_FULL_RE.finditer(workflow_block):
        name = m.group(1)
        if name == "git":
            continue
        tool = tool_index.get(_norm(name))
        if not tool:
            continue
        for out in tool.get("outputs", []):
            if out == "stdout" or "*" in out:
                continue
            producers.append(
                {"path": out, "start": m.start(), "source": f"tool:{name}"}
            )

    producers.sort(key=lambda p: p["start"])
    return producers


def normalize_placeholder(path: str) -> str:
    """{scout_name}/{domain}/etc → * so it can be fnmatch'd against a concrete
    git-add path, mirroring validate_agent's YAML-validation check."""
    return re.sub(r"\{[^}]+\}", "*", path)


def path_is_covered(path: str, add_paths: list[str]) -> bool:
    """Is `path` (possibly containing {placeholder} tokens) covered by any of
    the concrete/glob/directory-prefix tokens passed to `git add`?

    Both sides are placeholder-normalized ({domain}/{epic_name}/{domain_1}/...
    all collapse to `*`) before comparison — a git-add path like
    `workspace/discovery/domains/{domain}/` must match a write path like
    `workspace/discovery/domains/{domain}/epics/{epic_name}/stories.yaml`
    even though the two files may use different placeholder *names* for the
    same position (`{domain}` vs `{domain_1}`)."""
    pattern = normalize_placeholder(path).rstrip("/")
    for add_path in add_paths:
        add_path = normalize_placeholder(add_path).rstrip("/")
        if add_path == pattern:
            return True
        if _matches_any(pattern, [add_path]):
            return True
        if _matches_any(pattern, [add_path + "/*"]):
            return True
        # directory-prefix add (e.g. `workspace/discovery/domains/*/`) covering
        # a deeper concrete/templated write path underneath it.
        if pattern.startswith(add_path + "/"):
            return True
        if add_path.endswith("*") and pattern.startswith(add_path[:-1]):
            return True
    return False
