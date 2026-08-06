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


def test_dashboard_surfaces_hardware_amortization_as_own_line(tmp_path: Path):
    """hardware_amortization_usd (cogs-scout's per-user device amortization) must
    reach the dashboard as its own monthly figure — same treatment as
    operations_payroll, not silently folded into the aggregate COGS number."""
    discovery_dir = tmp_path / "discovery"
    (discovery_dir / "domains").mkdir(parents=True)
    strategy_dir = discovery_dir / "strategy"
    strategy_dir.mkdir()

    (strategy_dir / "revenue_model.yaml").write_text(
        yaml.dump(
            {
                "target_mau": 1000,
                "blended_arpu_usd": 10.0,
                "budget_constraint_usd": 5.0,
                "revenue_streams": [
                    {
                        "id": "sub",
                        "commitment_status": "committed",
                        "expected_share_percent": 100,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (strategy_dir / "unit_economics_model.yaml").write_text(
        yaml.dump(
            {
                "cogs_per_user_usd": {
                    "fixed_monthly_usd": {"compute": 20.0, "database": 25.0},
                    "variable_per_user_usd": {
                        "egress_traffic": 0.1,
                        "hardware_amortization_usd": 2.5,
                    },
                },
                "total_cogs_per_user_usd": 2.65,
            }
        ),
        encoding="utf-8",
    )

    result = run_build_project_analytics(
        BuildProjectAnalyticsInput(workspace_path=discovery_dir)
    )

    index_data = yaml.safe_load(Path(result.index_path).read_text(encoding="utf-8"))
    dashboard = index_data["dashboard"]
    assert dashboard["hardware_amortization_usd_per_user"] == 2.5  # noqa: PLR2004
    assert dashboard["hardware_amortization_monthly"] == 2500.0  # noqa: PLR2004


def test_dashboard_hardware_amortization_zero_without_hardware_devices(tmp_path: Path):
    discovery_dir = tmp_path / "discovery"
    (discovery_dir / "domains").mkdir(parents=True)
    strategy_dir = discovery_dir / "strategy"
    strategy_dir.mkdir()

    (strategy_dir / "revenue_model.yaml").write_text(
        yaml.dump(
            {
                "target_mau": 1000,
                "blended_arpu_usd": 10.0,
                "budget_constraint_usd": 5.0,
                "revenue_streams": [
                    {
                        "id": "sub",
                        "commitment_status": "committed",
                        "expected_share_percent": 100,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (strategy_dir / "unit_economics_model.yaml").write_text(
        yaml.dump(
            {
                "cogs_per_user_usd": {
                    "fixed_monthly_usd": {"compute": 20.0, "database": 25.0},
                    "variable_per_user_usd": {"egress_traffic": 0.1},
                },
                "total_cogs_per_user_usd": 0.15,
            }
        ),
        encoding="utf-8",
    )

    result = run_build_project_analytics(
        BuildProjectAnalyticsInput(workspace_path=discovery_dir)
    )

    index_data = yaml.safe_load(Path(result.index_path).read_text(encoding="utf-8"))
    assert index_data["dashboard"]["hardware_amortization_monthly"] == 0.0


def test_hardware_devices_reaches_detail_tech_but_not_compact_summary(tmp_path: Path):
    """hardware_devices is pitch-deck-only rendering data, same as data_sourcing —
    it must land in project_analytics_detail.yaml's `tech`, but compact_tech must
    keep excluding it from the compact tech_summary the discovery-pitcher's audit reads.
    """
    discovery_dir = tmp_path / "discovery"
    (discovery_dir / "domains").mkdir(parents=True)
    strategy_dir = discovery_dir / "strategy"
    strategy_dir.mkdir()

    (strategy_dir / "tech_constraints.yaml").write_text(
        yaml.dump(
            {
                "technology_stack": {"backend": "Go"},
                "hardware_devices": [
                    {
                        "device_id": "offline_scan_kiosk",
                        "device_name": "Kiosk Terminal",
                        "device_branch": "target-runtime",
                        "linked_features": [
                            {"domain": "billing", "feature_id": "card_payment"},
                            {"domain": "inventory", "feature_id": "stock_deduction"},
                        ],
                        "unit_cost_usd": 45.0,
                        "sourcing_risk": "multi-sourced",
                        "field_support_signal": "OTA возможен",
                        "regulatory_flags": ["CE required in EU"],
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
    assert detail_data["tech"]["hardware_devices"] == [
        {
            "device_id": "offline_scan_kiosk",
            "device_name": "Kiosk Terminal",
            "device_branch": "target-runtime",
            "linked_features": [
                {"domain": "billing", "feature_id": "card_payment"},
                {"domain": "inventory", "feature_id": "stock_deduction"},
            ],
            "unit_cost_usd": 45.0,
            "sourcing_risk": "multi-sourced",
            "field_support_signal": "OTA возможен",
            "regulatory_flags": ["CE required in EU"],
        }
    ]

    index_data = yaml.safe_load(Path(result.index_path).read_text(encoding="utf-8"))
    assert "hardware_devices" not in index_data["tech_summary"]
