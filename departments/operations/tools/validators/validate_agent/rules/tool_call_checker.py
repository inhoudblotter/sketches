import re
from pathlib import Path
import yaml
from ..schemas import LintError

CALL_TOOL_FULL_RE = re.compile(
    r'<call_tool\s+name="([^"]+)">(.*?)</call_tool>', re.DOTALL
)
FLAG_RE = re.compile(r"(?<!\S)-{1,2}[A-Za-z][\w-]*")

# System binaries that will never have a departments/*/tools/ meta.yaml but are
# legitimate <call_tool> targets (see skill-agent-crafting.md, "Системные
# исключения в <call_tool>"). Keep this list to the Git Sync convention's own
# operations — not a general shell escape hatch.
SYSTEM_TOOL_NAMES = {"git", "EnterWorktree"}

# Calibrated against actual usage at the time this check was added: the longest
# real <call_tool> body was 143 chars with at most 1 flag. These give headroom
# over that ceiling while still catching calls that have grown unwieldy for an
# LLM to compose reliably (see "Convention over Flags" in tooling-architect.md).
MAX_CALL_LENGTH = 160
MAX_FLAGS = 3


def get_valid_tool_names(workspace_dir: Path) -> set[str]:
    valid_names: set[str] = set()
    departments_dir = workspace_dir / "departments"
    if not departments_dir.exists():
        return valid_names

    for meta_file in departments_dir.rglob("meta.yaml"):
        # The default tool name is the directory name
        dir_name = meta_file.parent.name
        valid_names.add(dir_name)

        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                if "cli_name" in data:
                    valid_names.add(data["cli_name"])
        except Exception:
            pass

    return valid_names


def check_tool_calls(
    tool_calls: list[str], valid_tool_names: set[str]
) -> list[LintError]:
    errors = []
    for tool_name in tool_calls:
        if tool_name.startswith("[") and tool_name.endswith("]"):
            continue
        if tool_name in SYSTEM_TOOL_NAMES:
            continue
        if tool_name not in valid_tool_names:
            errors.append(
                LintError(
                    rule="Tool Existence",
                    message=f"Tool '{tool_name}' called but does not exist in any departments/*/tools/ as a directory or cli_name",
                )
            )
    return errors


def check_tool_call_complexity(workflow_block: str) -> list[LintError]:
    """A <call_tool> invocation the LLM has to compose from scratch each run
    should stay short and low on flags — see 'Convention over Flags' in
    tooling-architect.md's guardrails: variable-but-rare flags are fine,
    but a call needing many of them is a sign the tool should default them
    instead of pushing the complexity into every caller's prompt."""
    errors = []
    for tool_name, raw_body in CALL_TOOL_FULL_RE.findall(workflow_block):
        # git add/commit bodies are mechanical enumerations of the exact paths
        # already declared in this step's <write> tags (the "Scoped Commit"
        # convention) — their length grows with artifact count, not with
        # LLM-composed flag complexity, so the git binary is exempt here too
        # (see SYSTEM_TOOL_NAMES / check_tool_calls above).
        if tool_name in SYSTEM_TOOL_NAMES:
            continue
        body = " ".join(raw_body.split())
        if len(body) > MAX_CALL_LENGTH:
            errors.append(
                LintError(
                    rule="Tool Call Complexity",
                    message=f"<call_tool> body is {len(body)} chars (max {MAX_CALL_LENGTH}): '{body}'. Give the tool sane defaults instead of a long invocation.",
                )
            )
        flag_count = len(FLAG_RE.findall(body))
        if flag_count > MAX_FLAGS:
            errors.append(
                LintError(
                    rule="Tool Call Complexity",
                    message=f"<call_tool> body has {flag_count} flags (max {MAX_FLAGS}): '{body}'. Too many required flags — default the stable ones (see 'Convention over Flags').",
                )
            )
    return errors
