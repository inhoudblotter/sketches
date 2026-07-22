from pydantic import BaseModel, ConfigDict, field_validator
from pathlib import Path
from typing import Optional
import yaml


class PatchSchema(BaseModel):
    gap_type: str
    authored_by: str
    target_agent: str
    created_at: str
    status: str
    detail: str
    errata_ref: Optional[str] = None
    result_note: Optional[str] = None
    model_config = ConfigDict(extra="allow")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ["pending", "applied", "failed"]:
            raise ValueError("status must be one of: pending, applied, failed")
        return v


def run_validate_patch(file_path: Path, fix: bool = True) -> PatchSchema:
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError("File is empty or invalid YAML")

    status = data.get("status")
    if status in ["applied", "failed"] and not data.get("result_note"):
        raise ValueError("result_note is required when status is 'applied' or 'failed'")

    return PatchSchema.model_validate(data)
