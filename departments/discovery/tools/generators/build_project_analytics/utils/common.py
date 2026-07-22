import re
from pathlib import Path
from departments.discovery.tools.shared.file_utils import load_yaml


def load_strategy_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return load_yaml(path)
    except Exception as e:
        print(f"Warning: failed to read {path.name}: {e}")
        return {}


def extract_float(val, default=0.0):
    try:
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            return float(val.replace(",", "."))
        match = re.search(r"-?\d+(?:\.\d+)?", str(val))
        if match:
            return float(match.group(0))
    except (ValueError, TypeError):
        pass
    return default


def _sum_nested_floats(data):
    total = 0.0
    if isinstance(data, dict):
        for v in data.values():
            total += _sum_nested_floats(v)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "cost" in item:
                total += extract_float(item.get("cost", 0))
            else:
                total += _sum_nested_floats(item)
    else:
        total += extract_float(data)
    return total
