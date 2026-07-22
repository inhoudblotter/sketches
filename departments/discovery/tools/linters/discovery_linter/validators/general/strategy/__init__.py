from pathlib import Path
from departments.discovery.tools.linters.discovery_linter.validators.strategy.platform_strategy import (
    run_validation as run_validate_platform_strategy,
)
from departments.discovery.tools.linters.discovery_linter.validators.strategy.target_audience import (
    run_validation as run_validate_target_audience,
)
from departments.discovery.tools.linters.discovery_linter.validators.domain.domains_manifest import (
    run_validation as run_validate_domains_manifest,
)
from departments.discovery.tools.linters.discovery_linter.validators.strategy.platform_coverage import (
    run_validate_platform_coverage,
)
from departments.discovery.tools.linters.discovery_linter.validators.strategy.platform_coverage import (
    ValidatePlatformCoverageInput,
)


def _validate_platform_coverage(plat_file: Path, man_file: Path) -> list[str]:
    errors = []
    try:
        coverage_result = run_validate_platform_coverage(
            ValidatePlatformCoverageInput(
                platform_strategy_path=plat_file,
                domains_manifest_path=man_file,
            )
        )
        if not coverage_result.is_valid:
            details = []
            if coverage_result.unknown_domains:
                details.append(
                    f"supported_domains reference unknown domain ids: {', '.join(coverage_result.unknown_domains)}"
                )
            if coverage_result.uncovered_domains:
                details.append(
                    f"domains not covered by any platform: {', '.join(coverage_result.uncovered_domains)}"
                )
            errors.append(
                "platform_strategy.yaml <-> domains_manifest.yaml:\n"
                + "\n".join(details)
            )
    except Exception as e:
        errors.append(f"platform_strategy.yaml <-> domains_manifest.yaml: {e}")
    return errors


def run_validate_strategy(workspace_dir: Path):
    errors = []

    strategy_dir = workspace_dir / "discovery" / "strategy"
    meta_dir = workspace_dir / "discovery" / "meta"

    plat_file = strategy_dir / "platform_strategy.yaml"
    if plat_file.exists():
        try:
            run_validate_platform_strategy(plat_file)
        except Exception as e:
            errors.append(f"platform_strategy.yaml: {e}")

    ta_file = strategy_dir / "target_audience.yaml"
    if ta_file.exists():
        try:
            run_validate_target_audience(ta_file)
        except Exception as e:
            errors.append(f"target_audience.yaml: {e}")

    man_file = meta_dir / "domains_manifest.yaml"
    if man_file.exists():
        try:
            run_validate_domains_manifest(man_file)
        except Exception as e:
            errors.append(f"domains_manifest.yaml: {e}")

    if plat_file.exists() and man_file.exists():
        errors.extend(_validate_platform_coverage(plat_file, man_file))

    if errors:
        raise ValueError("\n\n---\n\n".join(errors))
    return True
