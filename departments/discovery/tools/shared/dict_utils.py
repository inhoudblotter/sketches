from typing import Any, Iterator, Tuple


def walk_strings(data: Any, path: str = "") -> Iterator[Tuple[str, str]]:
    """
    Recursively walks a data structure (dicts, lists) and yields all string values
    along with their json-like path.
    Yields: (path, string_value)
    """
    if isinstance(data, dict):
        for key, value in data.items():
            new_path = f"{path}.{key}" if path else str(key)
            # Also yield the key if we need to check keys for banned words
            yield f"{new_path} (key)", str(key)
            yield from walk_strings(value, new_path)
    elif isinstance(data, list):
        for index, item in enumerate(data):
            new_path = f"{path}[{index}]"
            yield from walk_strings(item, new_path)
    elif isinstance(data, str):
        yield path, data
