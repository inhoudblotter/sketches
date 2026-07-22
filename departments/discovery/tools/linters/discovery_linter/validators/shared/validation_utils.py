from pathlib import Path
from typing import TypeVar, Type
import yaml
from pydantic import BaseModel

from departments.discovery.tools.linters.discovery_linter.validators.shared.formatters import (
    auto_fix_xml_strings,
)

T = TypeVar("T", bound=BaseModel)


def validate_yaml_file(file_path: Path, schema: Type[T]) -> T:
    """
    Reads a YAML file and validates it against the provided Pydantic schema.
    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is empty or invalid YAML.
        ValidationError: If the parsed data doesn't match the schema.
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    fixed_content = auto_fix_xml_strings(content)
    if content != fixed_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(fixed_content)

    data = yaml.safe_load(fixed_content)

    if data is None:
        raise ValueError(f"File is empty or invalid YAML: {file_path}")

    return schema.model_validate(data)
