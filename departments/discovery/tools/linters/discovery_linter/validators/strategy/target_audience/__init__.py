from departments.discovery.tools.linters.discovery_linter.validators.shared.validation_utils import (
    validate_yaml_file,
)
from pydantic import BaseModel, Field
from typing import List
import yaml
from pathlib import Path
from typing import Any, Dict


class Persona(BaseModel):
    id: str
    name: str
    description: str
    pain_points: List[str]
    jtbd_motivations: List[str]
    subculture_and_lifestyle: List[str] = Field(default_factory=list)
    magnet_features: List[str] = Field(default_factory=list)
    cultural_tension: List[str] = Field(default_factory=list)
    behavioral_shift: List[str] = Field(default_factory=list)


class MachinePersona(BaseModel):
    id: str
    name: str
    consumption_method: str
    data_requirements: List[str]


class TargetAudienceSchema(BaseModel):
    author_agent: str
    personas: List[Persona]
    machine_personas: List[MachinePersona] = Field(default_factory=list)


LIST_FIELDS = (
    "pain_points",
    "jtbd_motivations",
    "subculture_and_lifestyle",
    "magnet_features",
    "cultural_tension",
    "behavioral_shift",
)


def format_audience_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize common formatting issues so the contract validates cleanly."""
    if not isinstance(data, dict):
        return data

    for persona in data.get("personas") or []:
        if not isinstance(persona, dict):
            continue
        for field in LIST_FIELDS:
            value = persona.get(field)
            if value is None:
                persona[field] = []
            elif isinstance(value, str):
                persona[field] = [value]

    if data.get("machine_personas") is None:
        data["machine_personas"] = []

    return data


def run_validation(file_path: Path, fix: bool = True) -> TargetAudienceSchema:
    model = validate_yaml_file(file_path, TargetAudienceSchema)

    if fix:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        data = format_audience_data(data)
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    return model
