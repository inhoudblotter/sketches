from pydantic import BaseModel
from typing import Literal

Category = Literal[
    "MISSING_COMMIT",
    "PATH_MISMATCH",
    "STILL_SELF_COMMITS_BUT_PARALLEL",
    "DESTRUCTIVE_GIT_OP",
    "BATCH_CAP_EXCEEDED",
]


class Finding(BaseModel):
    category: Category
    file_path: str
    message: str
    detail: str | None = None


class GitCoverageResult(BaseModel):
    files_checked: list[str]
    findings: list[Finding]

    @property
    def is_clean(self) -> bool:
        return len(self.findings) == 0
