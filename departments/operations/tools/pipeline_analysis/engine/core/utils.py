from pathlib import Path
from departments.operations.tools.shared.tool_parser import _norm


def _resolve_tool(tool_name: str, tools_by_key: dict) -> dict | None:
    return tools_by_key.get(_norm(tool_name))


def _invocation_subcommand(invocation: str, tool: dict) -> str | None:
    tokens = invocation.split()
    cli_names = set(tool.get("match_keys", []))
    for i, tok in enumerate(tokens):
        if _norm(tok) in cli_names:
            for nxt in tokens[i + 1 :]:
                if not nxt.startswith("-"):
                    return nxt
            return None
    return None


def _artifact_attrs(path_str: str, workspace_dir: Path) -> dict:
    p = Path(path_str)
    if not p.is_absolute():
        p = Path.cwd() / path_str
    exists = p.exists()
    size_kb = round(p.stat().st_size / 1024, 2) if exists else 0.0
    return {
        "node_type": "artifact",
        "exists": exists,
        "size_kb": size_kb,
        "path": path_str,
    }


def _skill_size_kb(skill_path: str, base_dir: Path) -> float:
    p = Path(skill_path)
    if not p.is_absolute():
        p = base_dir / skill_path
    return round(p.stat().st_size / 1024, 2) if p.exists() else 0.0
