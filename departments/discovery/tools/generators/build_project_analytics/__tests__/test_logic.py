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


def test_data_sourcing_reaches_detail_tech_but_not_compact_summary(tmp_path: Path):
    """data_sourcing is pitch-deck-only rendering data (like growth_path/maintainability) —
    it must land in project_analytics_detail.yaml's `tech`, but compact_tech must keep
    excluding it from the compact tech_summary the discovery-pitcher's audit reads."""
    discovery_dir = tmp_path / "discovery"
    (discovery_dir / "domains").mkdir(parents=True)
    strategy_dir = discovery_dir / "strategy"
    strategy_dir.mkdir()

    (strategy_dir / "tech_constraints.yaml").write_text(
        yaml.dump(
            {
                "technology_stack": {"backend": "Go"},
                "data_sourcing": [
                    {
                        "domain": "billing",
                        "feature_id": "card_payment",
                        "feature_name": "Card Payment",
                        "automation_verdict": "manual-required",
                        "moderation_signal": "~50 записей/день, ручная проверка",
                        "legal_flags": [
                            "Лицензия запрещает коммерческое использование"
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = run_build_project_analytics(
        BuildProjectAnalyticsInput(workspace_path=discovery_dir)
    )

    detail_data = yaml.safe_load(Path(result.detail_path).read_text(encoding="utf-8"))
    assert detail_data["tech"]["data_sourcing"] == [
        {
            "domain": "billing",
            "feature_id": "card_payment",
            "feature_name": "Card Payment",
            "automation_verdict": "manual-required",
            "moderation_signal": "~50 записей/день, ручная проверка",
            "legal_flags": ["Лицензия запрещает коммерческое использование"],
        }
    ]

    index_data = yaml.safe_load(Path(result.index_path).read_text(encoding="utf-8"))
    assert "data_sourcing" not in index_data["tech_summary"]


def test_data_sourcing_absent_when_tech_constraints_has_none(tmp_path: Path):
    discovery_dir = tmp_path / "discovery"
    (discovery_dir / "domains").mkdir(parents=True)
    strategy_dir = discovery_dir / "strategy"
    strategy_dir.mkdir()

    (strategy_dir / "tech_constraints.yaml").write_text(
        yaml.dump({"technology_stack": {"backend": "Go"}}), encoding="utf-8"
    )

    result = run_build_project_analytics(
        BuildProjectAnalyticsInput(workspace_path=discovery_dir)
    )

    detail_data = yaml.safe_load(Path(result.detail_path).read_text(encoding="utf-8"))
    assert detail_data["tech"]["data_sourcing"] == []
