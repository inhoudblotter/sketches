import yaml
from pathlib import Path
from typing import Optional
from functools import lru_cache

from departments.discovery.tools.linters.discovery_linter.validators.shared.formatters import (
    auto_fix_xml_strings,
)


@lru_cache(maxsize=1024)
def _load_yaml_cached(path_str: str) -> Optional[dict]:
    path = Path(path_str)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        fixed_content = auto_fix_xml_strings(content)
        if content != fixed_content:
            with open(path, "w", encoding="utf-8") as f:
                f.write(fixed_content)
        return yaml.safe_load(fixed_content)
    except Exception:
        # Re-raising or printing could be done here.
        # For backward compatibility, we return None but log a simple message.
        # print(f"Warning: Failed to parse YAML {path}: {e}")
        return None


def load_yaml(path: Path) -> Optional[dict]:
    """Loads a YAML file with caching to avoid reading the same file multiple times."""
    return _load_yaml_cached(str(path))
