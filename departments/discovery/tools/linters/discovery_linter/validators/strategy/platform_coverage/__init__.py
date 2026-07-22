from pydantic import BaseModel, Field
from typing import List
from pathlib import Path
import yaml


class ValidatePlatformCoverageInput(BaseModel):
    platform_strategy_path: Path = Field(
        ..., description="Path to platform_strategy.yaml"
    )
    domains_manifest_path: Path = Field(
        ..., description="Path to domains_manifest.yaml"
    )


class ValidatePlatformCoverageOutput(BaseModel):
    is_valid: bool
    unknown_domains: List[
        str
    ]  # referenced in supported_domains but not in domains_manifest
    uncovered_domains: List[
        str
    ]  # declared in domains_manifest but not covered by any platform


def run_validate_platform_coverage(
    input_data: ValidatePlatformCoverageInput,
) -> ValidatePlatformCoverageOutput:
    if not input_data.platform_strategy_path.is_file():
        raise FileNotFoundError(f"File not found: {input_data.platform_strategy_path}")
    if not input_data.domains_manifest_path.is_file():
        raise FileNotFoundError(f"File not found: {input_data.domains_manifest_path}")

    platform_data = (
        yaml.safe_load(input_data.platform_strategy_path.read_text(encoding="utf-8"))
        or {}
    )
    manifest_data = (
        yaml.safe_load(input_data.domains_manifest_path.read_text(encoding="utf-8"))
        or {}
    )

    domain_ids = {
        str(d.get("id"))
        for d in (manifest_data.get("domains") or [])
        if isinstance(d, dict) and str(d.get("id"))
    }

    supported_domains: set[str] = set()
    for platform in platform_data.get("platforms") or []:
        if not isinstance(platform, dict):
            continue
        for domain_id in platform.get("supported_domains") or []:
            if domain_id:
                supported_domains.add(domain_id)

    # platform_strategy.yaml and domains_manifest.yaml are both written by
    # po-strategist in the same step (1.2) — nothing else cross-checks that a
    # supported_domains entry actually refers to a real domain, or that every
    # domain has at least one platform. A gap here means po-strategist-sub
    # (step 1.4) has no platform data for its domain and has to guess
    # epic_requirements.platforms.
    unknown_domains = sorted(supported_domains - domain_ids)
    uncovered_domains = sorted(domain_ids - supported_domains)

    return ValidatePlatformCoverageOutput(
        is_valid=len(unknown_domains) == 0 and len(uncovered_domains) == 0,
        unknown_domains=unknown_domains,
        uncovered_domains=uncovered_domains,
    )
