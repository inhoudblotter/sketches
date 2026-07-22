from pydantic import BaseModel
from typing import List
import yaml
from pathlib import Path
from .. import RevenueModel, UnitEconomicsModel


class ScenarioResult(BaseModel):
    name: str
    description: str
    original_margin_percent: float
    new_margin_percent: float
    is_critical_risk: bool


class StressTestOutput(BaseModel):
    scenarios: List[ScenarioResult]
    overall_status: str
    message: str


def calculate_margin(rev: float, cogs: float) -> float:
    if rev <= 0:
        return 0.0
    return ((rev - cogs) / rev) * 100.0


def run_stress_test(revenue_file: Path, economics_file: Path) -> StressTestOutput:
    if not revenue_file.exists():
        raise FileNotFoundError(f"Revenue model file not found: {revenue_file}")
    if not economics_file.exists():
        raise FileNotFoundError(
            f"Unit economics model file not found: {economics_file}"
        )

    with open(revenue_file, "r", encoding="utf-8") as f:
        rev_data = yaml.safe_load(f)
    with open(economics_file, "r", encoding="utf-8") as f:
        cogs_data = yaml.safe_load(f)

    rev_model = RevenueModel(**rev_data)
    cogs_model = UnitEconomicsModel(**cogs_data)

    orig_rev = rev_model.blended_arpu_usd
    orig_cogs = cogs_model.total_cogs_per_user_usd
    orig_margin = calculate_margin(orig_rev, orig_cogs)

    scenarios = []

    # Сценарий 1: Падение конверсии/ARPU на 20%
    s1_rev = orig_rev * 0.8
    s1_margin = calculate_margin(s1_rev, orig_cogs)
    s1_risk = s1_margin < 0
    scenarios.append(
        ScenarioResult(
            name="ARPU Drop 20%",
            description="Падение конверсии/ARPU на 20%",
            original_margin_percent=orig_margin,
            new_margin_percent=s1_margin,
            is_critical_risk=s1_risk,
        )
    )

    # Сценарий 2: Рост инфраструктурных/API костов на 40%
    target_mau = rev_model.target_mau or 1
    fixed = cogs_model.cogs_per_user_usd.fixed_monthly_usd
    var = cogs_model.cogs_per_user_usd.variable_per_user_usd

    fixed_per_user: float = 0.0
    if fixed is not None:
        fixed_per_user = (
            fixed.compute + fixed.database + (fixed.p2p_infrastructure or 0)
        ) / target_mau

    var_egress = var.egress_traffic if var else 0
    var_apis = (
        sum(api.cost for api in var.external_apis) if var and var.external_apis else 0
    )

    infra_api = fixed_per_user + var_egress + var_apis
    operational = (
        (var.operational.maintenance_and_support + var.operational.payment_gateway_fees)
        if var and var.operational
        else 0
    )

    s2_cogs = (infra_api * 1.4) + operational
    s2_margin = calculate_margin(orig_rev, s2_cogs)
    s2_risk = s2_margin < 0
    scenarios.append(
        ScenarioResult(
            name="COGS Spike 40%",
            description="Рост инфраструктурных/API костов на 40%",
            original_margin_percent=orig_margin,
            new_margin_percent=s2_margin,
            is_critical_risk=s2_risk,
        )
    )

    has_critical_risk = any(s.is_critical_risk for s in scenarios)
    status = "CRITICAL_RISK" if has_critical_risk else "SUCCESS"
    message = (
        "Проект становится убыточным при шоковых сценариях!"
        if has_critical_risk
        else "Проект имеет достаточный запас прочности."
    )

    return StressTestOutput(scenarios=scenarios, overall_status=status, message=message)
