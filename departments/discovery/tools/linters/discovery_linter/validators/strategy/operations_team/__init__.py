from pathlib import Path
from typing import List, Literal, Union

from pydantic import BaseModel

from departments.discovery.tools.linters.discovery_linter.validators.shared.validation_utils import (
    validate_yaml_file,
)


class Role(BaseModel):
    id: str
    title: str
    type: Literal["fte", "retainer"] = "fte"
    headcount_formula: str
    estimated_headcount: int
    salary_usd: Union[int, float]
    responsibilities: List[str]


class OperationsTeamSchema(BaseModel):
    author_agent: str
    roles: List[Role]
    total_monthly_payroll_usd: Union[int, float]


def run_validation(file_path: Path) -> OperationsTeamSchema:
    model = validate_yaml_file(file_path, OperationsTeamSchema)

    computed_payroll = sum(r.estimated_headcount * r.salary_usd for r in model.roles)
    if model.roles and round(computed_payroll) != round(
        model.total_monthly_payroll_usd
    ):
        raise ValueError(
            f"total_monthly_payroll_usd ({model.total_monthly_payroll_usd}) не совпадает с "
            f"суммой estimated_headcount*salary_usd по ролям ({computed_payroll})"
        )

    return model
