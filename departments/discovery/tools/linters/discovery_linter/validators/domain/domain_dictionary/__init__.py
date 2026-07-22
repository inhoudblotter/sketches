from departments.discovery.tools.linters.discovery_linter.validators.shared.validation_utils import (
    validate_yaml_file,
)
from pydantic import BaseModel
from typing import List
from pathlib import Path
import yaml

from .rules.validators import validate_banned_words, validate_no_shared_context


class Attribute(BaseModel):
    name: str
    semantic_type: str
    description: str
    is_required: bool = True


class Relationship(BaseModel):
    type: str
    target: str
    description: str


class Entity(BaseModel):
    name: str
    description: str
    type: str
    attributes: List[Attribute]
    relationships: List[Relationship] = []


class GlossaryItem(BaseModel):
    term: str
    definition: str


class DomainDictionarySchema(BaseModel):
    domain: str
    entities: List[Entity]
    glossary: List[GlossaryItem] = []


def run_validation(file_path: Path) -> DomainDictionarySchema:
    model = validate_yaml_file(file_path, DomainDictionarySchema)

    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    validate_no_shared_context(file_path, data)
    validate_banned_words(data)

    return model
