import pydantic
from pathlib import Path
from typing import List


class BuildProjectAnalyticsInput(pydantic.BaseModel):
    workspace_path: Path


class BuildProjectAnalyticsOutput(pydantic.BaseModel):
    index_path: str
    detail_path: str
    total_mvp_sp: int
    mvp_size_bucket: str
    high_risk_stories_count: int
    compliance_flags: List[str]
    infrastructure_usd_per_month: float
