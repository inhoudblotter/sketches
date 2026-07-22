from typing import Optional
from pydantic import BaseModel, Field
from pathlib import Path


class GeneratePitchDeckInput(BaseModel):
    yaml_path: Path = Field(..., description="Path to input pitch_deck.yaml")
    out_path: Path = Field(..., description="Path to output HTML file")
    analytics_path: Optional[Path] = Field(
        None,
        description="Path to meta/project_analytics.yaml (compact: dashboard/tech_summary/errata/scope_analytics, pre-aggregated by build-project-analytics)",
    )
    detail_path: Optional[Path] = Field(
        None,
        description="Path to meta/project_analytics_detail.yaml (verbose: full tech, roadmap, sp_by_epic/epics_by_domain, data_model_metrics — pitch-deck-only rendering data)",
    )


class GeneratePitchDeckOutput(BaseModel):
    html_path: str
    slides_count: int
    dashboard_included: bool
