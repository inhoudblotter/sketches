from typing import List, Any


def filter_ui_noise(data: List[Any]) -> List[Any]:
    """Drops trivial UI complaints (fonts, colors, buttons, padding, etc.)."""
    # Using simple substring checks based on the problem description
    ui_keywords = ["font", "color", "button", "padding", "margin", "ui", "ux"]

    filtered = []
    for item in data:
        if isinstance(item, dict) and "description" in item:
            desc = str(item.get("description", "")).lower()
            if any(kw in desc for kw in ui_keywords):
                continue
        filtered.append(item)
    return filtered
