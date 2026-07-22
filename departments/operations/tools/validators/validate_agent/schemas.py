from pydantic import BaseModel
from typing import Literal


class LintError(BaseModel):
    rule: str
    message: str
    line: int | None = None


class LintResult(BaseModel):
    file_path: str
    status: Literal["ok", "error"]
    errors: list[LintError]
