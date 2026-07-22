from pathlib import Path
import re
import yaml
import sys


def _norm(s: str) -> str:
    """Normalize a tool identifier for matching: lowercase, strip -/_ separators."""
    return re.sub(r"[-_\s]+", "", s or "").lower()


def _matches_pattern(path_str: str, pattern: str) -> bool:
    # Convert glob pattern to regex pattern
    regex_pattern = pattern
    # Escape dots
    regex_pattern = regex_pattern.replace(".", r"\.")
    # Replace ** with .*
    regex_pattern = regex_pattern.replace("**", ".*")
    # Replace * with [^/]* (but ignore * we just placed for **)
    # It's safer to build it token by token
    tokens = []
    i = 0
    while i < len(pattern):
        if pattern[i : i + 2] == "**":
            tokens.append(".*")
            i += 2
        elif pattern[i] == "*":
            tokens.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            tokens.append("[^/]")
            i += 1
        elif pattern[i] in ".+^$()|[]{}":
            tokens.append("\\" + pattern[i])
            i += 1
        else:
            tokens.append(pattern[i])
            i += 1

    import re

    # Match the end of the string
    regex = "^" + "".join(tokens) + "$"

    if re.match(regex, path_str):
        return True

    if not pattern.startswith("*"):
        # Match as if it starts with */
        regex_anywhere = "^.*/" + "".join(tokens) + "$"
        if re.match(regex_anywhere, path_str):
            return True

    # Match against the filename only
    filename = Path(path_str).name
    return bool(re.match(regex, filename))


def _matches_any(path_str: str, patterns: list[str]) -> bool:
    return any(_matches_pattern(path_str, p) for p in patterns if p and p != "stdout")


def _parse_meta_file(
    meta_file: Path, root_tools_by_dir: dict, tools: list[dict]
) -> None:
    try:
        with open(meta_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        name = data.get("name")
        if not name:
            name = meta_file.parent.name

        parent_tool = None
        for root_dir, root_tool in root_tools_by_dir.items():
            if (
                meta_file.is_relative_to(root_dir)
                and meta_file != root_dir / "meta.yaml"
            ):
                parent_tool = root_tool
                break

        if parent_tool:
            calls_t = data.get("calls_tools", []) or []
            if isinstance(calls_t, str):
                calls_t = [calls_t]
            commands = parent_tool.setdefault("commands", {})
            commands[name] = {
                "inputs": data.get("inputs", []),
                "outputs": data.get("outputs", []),
                "contract": data.get("contract", ""),
                "contract_schema": data.get("contract_schema", ""),
                "description": data.get("description", ""),
                "entrypoint": data.get("entrypoint", ""),
                "calls_tools": calls_t,
            }
            return

        cli_name = data.get("cli_name", "")
        cli_aliases = data.get("cli_aliases", []) or []
        if isinstance(cli_aliases, str):
            cli_aliases = [cli_aliases]

        calls_tools = data.get("calls_tools", []) or []
        if isinstance(calls_tools, str):
            calls_tools = [calls_tools]

        match_candidates = {name, cli_name, meta_file.parent.name, *cli_aliases}
        match_keys = {_norm(c) for c in match_candidates if c}

        commands = data.get("commands", {}) or {}

        tool = {
            "name": name,
            "tool_type": data.get("type", "unknown"),
            "description": data.get("description", ""),
            "department": data.get("department", ""),
            "inputs": data.get("inputs", []),
            "outputs": data.get("outputs", []),
            "calls_tools": calls_tools,
            "match_keys": sorted(match_keys),
            "commands": commands,
            "entrypoint": data.get("entrypoint", "agent"),
            "contract": data.get("contract", ""),
            "contract_schema": data.get("contract_schema", ""),
            "is_root_tool": data.get("is_root_tool", False),
        }

        if tool["is_root_tool"]:
            root_tools_by_dir[meta_file.parent] = tool

        tools.append(tool)
    except Exception as exc:
        print(f"[WARN] Failed to parse {meta_file}: {exc}", file=sys.stderr)


def parse_all(tools_dir: Path) -> list[dict]:
    tools: list[dict] = []
    if not tools_dir.exists():
        return tools

    # Sort by path length so parents are processed before children
    meta_files = sorted(tools_dir.rglob("meta.yaml"), key=lambda p: len(p.parts))

    root_tools_by_dir: dict[Path, dict] = {}

    for meta_file in meta_files:
        _parse_meta_file(meta_file, root_tools_by_dir, tools)

    return tools


def parse_compositions(
    tools_dir: Path, tools: list[dict]
) -> list[tuple[str, str, str | None]]:
    """Tools that call other tools directly (e.g. a generator that runs a linter
    before writing its output, or an aggregator that imports a multi-command
    analyzer's Python API) declare this in their own meta.yaml via
    `calls_tools: [...]`.

    An entry can be:
      - `tool-name` — whole-tool composition (rare: the caller genuinely uses
        the entire callee, e.g. a linter with a flat inputs/outputs pair).
      - `tool-name::subcommand` — scoped composition, required for any
        multi-command tool (one declaring `commands:` in its own meta.yaml,
        e.g. query_discovery). Without the subcommand, every caller would
        wire against the *whole* tool node — which for a swiss-army-knife
        analyzer means "reads every file in the department" instead of the
        handful of files the specific subcommand actually touches.

    Returns resolved (caller_name, callee_name, subcommand_or_None) triples.
    """
    by_key: dict[str, str] = {}
    for t in tools:
        for key in t.get("match_keys", []):
            by_key[key] = t["name"]

    triples: list[tuple[str, str, str | None]] = []
    seen: set[tuple[str, str, str | None]] = set()

    for t in tools:
        caller_name = t["name"]
        for callee_ref in t.get("calls_tools", []):
            base_ref, sep, subcommand = callee_ref.partition("::")
            subcommand = subcommand or None
            callee_name = by_key.get(_norm(base_ref))
            if callee_name and callee_name != caller_name:
                triple = (caller_name, callee_name, subcommand)
                if triple not in seen:
                    seen.add(triple)
                    triples.append(triple)

    return triples
