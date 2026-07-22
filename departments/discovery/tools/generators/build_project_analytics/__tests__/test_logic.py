import yaml
from pathlib import Path
from ..schemas import BuildProjectAnalyticsInput
from ..logic import run_build_project_analytics


def test_infra_cost_read_from_unit_economics_model(tmp_path: Path):
    discovery_dir = tmp_path / "discovery"
    domains_dir = discovery_dir / "domains"
    domains_dir.mkdir(parents=True)
    strategy_dir = discovery_dir / "strategy"
    strategy_dir.mkdir()

    (strategy_dir / "unit_economics_model.yaml").write_text(
        yaml.dump(
            {
                "cogs_per_user_usd": {
                    "fixed_monthly_usd": {
                        "compute": 20.0,
                        "database": 25.0,
                        "p2p_infrastructure": 5.0,
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    result = run_build_project_analytics(
        BuildProjectAnalyticsInput(workspace_path=discovery_dir)
    )

    assert result.infrastructure_usd_per_month == 50.0  # noqa: PLR2004


def test_infra_cost_defaults_to_zero_without_unit_economics_model(tmp_path: Path):
    discovery_dir = tmp_path / "discovery"
    (discovery_dir / "domains").mkdir(parents=True)

    result = run_build_project_analytics(
        BuildProjectAnalyticsInput(workspace_path=discovery_dir)
    )

    assert result.infrastructure_usd_per_month == 0.0
