# ruff: noqa: C901, PLR0912, PLR0915, PLR2004
import pytest
import yaml
from .. import run_stress_test


@pytest.fixture
def mock_files(tmp_path):
    rev = tmp_path / "rev.yaml"
    with open(rev, "w") as f:
        yaml.dump(
            {
                "revenue_streams": [],
                "blended_arpu_usd": 100.0,
                "budget_constraint_usd": 50.0,
            },
            f,
        )

    cogs = tmp_path / "cogs.yaml"
    with open(cogs, "w") as f:
        yaml.dump(
            {
                "author_agent": "cogs-scout",
                "cogs_per_user_usd": {
                    "fixed_monthly_usd": {
                        "compute": 10,
                        "database": 5,
                        "p2p_infrastructure": 0,
                    },
                    "variable_per_user_usd": {
                        "egress_traffic": 5,
                        "external_apis": [{"provider": "openai", "cost": 10}],
                        "operational": {
                            "maintenance_and_support": 5,
                            "payment_gateway_fees": 5,
                        },
                    },
                },
                "total_cogs_per_user_usd": 40.0,
            },
            f,
        )

    return rev, cogs


def test_stress_test_success(mock_files):  # noqa: PLR2004
    rev, cogs = mock_files
    result = run_stress_test(rev, cogs)

    assert result.overall_status == "SUCCESS"
    assert len(result.scenarios) == 2

    s1 = result.scenarios[0]
    assert s1.new_margin_percent == 50.0

    s2 = result.scenarios[1]
    assert s2.new_margin_percent == 48.0
