import sys
from pathlib import Path
from typing import Dict, Any, Optional

import yaml

from departments.operations.tools.shared.yaml_autofix import load_yaml_text


def load_yaml(file_path: str | Path) -> Dict[str, Any]:
    """Loads a YAML file and returns a dictionary.

    Self-heals the known recurring LLM YAML-quoting mistakes (see
    departments/operations/tools/shared/yaml_autofix.py) before falling back
    to a hard parse error — always on, no opt-in required.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = load_yaml_text(f.read())
        return data if data is not None else {}


def load_yaml_safe(path: Path, default=None):
    """load_yaml, but returns `default` instead of raising on a missing or unparseable file.
    For call sites that treat "file absent/corrupt" as "no data" rather than a hard error.
    """
    if not path.exists():
        return default
    try:
        return load_yaml(path)
    except Exception:
        return default


def domains_dir_or_warn(workspace_dir: Path) -> Optional[Path]:
    """Resolve `workspace_dir/discovery/domains`, or print a clear warning to
    stderr and return None if it doesn't exist.

    Query-side commands built around this dispatch to a `for domain_dir in
    domains_dir.iterdir()` loop, which silently yields nothing when the
    directory is absent — usually because `workspace_dir` was mistyped or
    points at the wrong path. Without this, that mistake looks identical to
    "workspace exists but genuinely has no domains yet", both rendering as an
    empty `{}`/`[]`. Callers still get an empty result back (results stay a
    read-only query, not a hard failure), but now with a printed reason.
    """
    domains_dir = workspace_dir / "discovery" / "domains"
    if not domains_dir.exists():
        print(
            f"warning: {domains_dir} does not exist "
            f"(is '{workspace_dir}' a valid discovery workspace path?)",
            file=sys.stderr,
        )
        return None
    return domains_dir


def scaffold_if_missing(path: Path, default_content: dict) -> None:
    """Writes `default_content` as YAML to `path`, which must not already exist.
    Used by --fix linters to seed a placeholder file instead of hard-failing
    when an upstream agent hasn't produced it yet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(default_content, f, allow_unicode=True, sort_keys=False)
