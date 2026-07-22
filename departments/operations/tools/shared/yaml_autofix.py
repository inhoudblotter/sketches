import re
from typing import Callable, List, Tuple

import yaml

Fixer = Callable[[str], str]


def yaml_error(text: str) -> str:
    """Returns the parse error message, or "" if `text` is valid YAML."""
    try:
        yaml.safe_load(text)
        return ""
    except Exception as e:
        return str(e)


def autofix_yaml_text(text: str, fixers: List[Fixer]) -> Tuple[str, str, str]:
    """Runs `fixers` in order against invalid YAML text until it re-parses.

    Returns (fixed_text, error_before, error_after):
      - error_before == "": text was already valid, fixed_text == text.
      - error_after == "" and fixed_text != text: fix succeeded.
      - error_after != "": fixers ran but the result still doesn't parse
        (or no fixer matched, in which case fixed_text == text).
    """
    error_before = yaml_error(text)
    if not error_before:
        return text, "", ""

    fixed = text
    for fixer in fixers:
        fixed = fixer(fixed)

    error_after = yaml_error(fixed)
    return fixed, error_before, error_after


# --- Common regex fixers for recurring LLM YAML-quoting mistakes ---
# These target scalar-quoting bugs, not structural/indentation errors —
# keep additions narrow enough that a fixer can't turn valid-but-unusual
# YAML into something semantically different.


def fix_backslash_escaped_quote(text: str) -> str:
    """Backslash-escaping an apostrophe inside a single-quoted scalar is
    invalid YAML — single-quoted scalars escape ' by doubling it: ''."""
    return re.sub(r"\\'", "''", text)


def fix_mismatched_quote_close(text: str) -> str:
    """Opening a scalar with ' and closing it with " (or vice versa), usually
    because an internal apostrophe confused the author mid-string."""
    return re.sub(
        r"(?<!')'([^'\"\n]*?)\"(?=[,\]\n])", lambda m: "'" + m.group(1) + "'", text
    )


def fix_tab_indentation(text: str) -> str:
    """YAML forbids tabs as indentation ("found character '\\t' that cannot
    start any token"). Only touches leading whitespace at the start of a
    line — tabs elsewhere (inside a quoted scalar, mid-content) are left
    alone since rewriting those could change the string's actual content."""
    return re.sub(r"(?m)^([ \t]*)", lambda m: m.group(1).replace("\t", "  "), text)


# Deliberately NOT auto-fixed: an unescaped `: ` inside an unquoted scalar
# (e.g. `title: Note: important thing` -> "mapping values are not allowed
# here"). A regex can't tell which colon was the intended key/value split
# without guessing at the author's meaning, and a wrong guess would silently
# corrupt data rather than fail loudly. This must stay a hard validation
# error telling the author to quote the string, never a silent rewrite.

DEFAULT_QUOTE_FIXERS: List[Fixer] = [
    fix_backslash_escaped_quote,
    fix_mismatched_quote_close,
]
DEFAULT_FIXERS: List[Fixer] = [fix_tab_indentation] + DEFAULT_QUOTE_FIXERS


def load_yaml_text(text: str):
    """Parses YAML text, self-healing known LLM YAML mistakes on failure.

    This is the base, always-on autofix path: any tool loading YAML written by
    an LLM agent should go through here (or `shared.file_utils.load_yaml`,
    which calls this) instead of a bare `yaml.safe_load`, so the recurring
    mistakes above never surface as a hard parse failure. If the fixers
    don't resolve it, the original parse error is raised — callers should not
    silently swallow a still-broken file.
    """
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError:
        fixed, _error_before, error_after = autofix_yaml_text(text, DEFAULT_FIXERS)
        if error_after:
            raise
        return yaml.safe_load(fixed)
