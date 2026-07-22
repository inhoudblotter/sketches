from pydantic import BaseModel
from typing import List, Optional, Tuple
import yaml
import sys
from pathlib import Path

ROUNDING_TOLERANCE_USD = 0.01
MIN_GROSS_MARGIN_PERCENT = 30
STRESS_ARPU_FACTOR = 0.8
STRESS_COGS_FACTOR = 1.4


class RevenueStream(BaseModel):
    id: str
    type: str
    target_audience: str
    arpu_monthly_usd: Optional[float] = None
    expected_share_percent: float


class RevenueModel(BaseModel):
    target_mau: Optional[float] = None
    revenue_streams: List[RevenueStream]
    blended_arpu_usd: float
    budget_constraint_usd: float
    strategic_insight: str = ""


class ExternalApiCost(BaseModel):
    provider: str
    cost: float


class OperationalCost(BaseModel):
    maintenance_and_support: float
    payment_gateway_fees: float


class FixedMonthly(BaseModel):
    compute: float
    database: float
    p2p_infrastructure: Optional[float] = None


class VariablePerUser(BaseModel):
    egress_traffic: float
    tokenomics_costs: Optional[float] = None
    external_apis: List[ExternalApiCost]
    operational: OperationalCost


class CogsPerUser(BaseModel):
    fixed_monthly_usd: Optional[FixedMonthly] = None
    variable_per_user_usd: Optional[VariablePerUser] = None


class UnitEconomicsModel(BaseModel):
    author_agent: str
    cogs_per_user_usd: CogsPerUser
    total_cogs_per_user_usd: float
    rationale: str = ""


def _load_models(file_path: Path) -> Tuple[RevenueModel, UnitEconomicsModel]:
    revenue_file = file_path.parent / "revenue_model.yaml"
    if not revenue_file.exists():
        raise FileNotFoundError(f"Revenue model file not found: {revenue_file}")
    if not file_path.exists():
        raise FileNotFoundError(f"Unit economics model file not found: {file_path}")

    with open(revenue_file, "r", encoding="utf-8") as f:
        rev_data = yaml.safe_load(f)
    with open(file_path, "r", encoding="utf-8") as f:
        cogs_data = yaml.safe_load(f)

    return RevenueModel(**rev_data), UnitEconomicsModel(**cogs_data)


def _validate_blended_arpu(rev_model: RevenueModel) -> None:
    calculated_blended = sum(
        (s.arpu_monthly_usd or 0.0) * (s.expected_share_percent / 100.0)
        for s in rev_model.revenue_streams
    )
    if abs(calculated_blended - rev_model.blended_arpu_usd) > ROUNDING_TOLERANCE_USD:
        raise ValueError(
            f"Blended ARPU mismatch. Calculated: {calculated_blended}, Stated: {rev_model.blended_arpu_usd}"
        )


def _calculate_cogs(
    rev_model: RevenueModel, cogs_per_user: CogsPerUser
) -> Tuple[float, float]:
    """Returns (calculated_total_cogs, total_variable_cogs)."""
    if not (cogs_per_user.fixed_monthly_usd and cogs_per_user.variable_per_user_usd):
        raise ValueError(
            "Invalid COGS structure. Must provide fixed_monthly_usd and variable_per_user_usd."
        )

    target_mau = (
        rev_model.target_mau
        if rev_model.target_mau and rev_model.target_mau > 0
        else 1.0
    )

    fixed = cogs_per_user.fixed_monthly_usd
    fixed_sum = fixed.compute + fixed.database
    if fixed.p2p_infrastructure:
        fixed_sum += fixed.p2p_infrastructure

    var = cogs_per_user.variable_per_user_usd
    var_sum = var.egress_traffic
    if var.tokenomics_costs:
        var_sum += var.tokenomics_costs
    var_sum += sum(api.cost for api in var.external_apis)
    var_sum += (
        var.operational.maintenance_and_support + var.operational.payment_gateway_fees
    )

    calculated_cogs = (fixed_sum / target_mau) + var_sum
    return calculated_cogs, var_sum


def _validate_cogs_total(
    calculated_cogs: float, cogs_model: UnitEconomicsModel
) -> None:
    if (
        abs(calculated_cogs - cogs_model.total_cogs_per_user_usd)
        > ROUNDING_TOLERANCE_USD
    ):
        raise ValueError(
            f"Total COGS mismatch. Calculated: {calculated_cogs}, Stated: {cogs_model.total_cogs_per_user_usd}"
        )


def _validate_gross_margin(
    rev_model: RevenueModel, cogs_model: UnitEconomicsModel
) -> None:
    gross_margin_usd = rev_model.blended_arpu_usd - cogs_model.total_cogs_per_user_usd
    gross_margin_percent = (
        (gross_margin_usd / rev_model.blended_arpu_usd) * 100
        if rev_model.blended_arpu_usd > 0
        else 0
    )

    if gross_margin_percent < MIN_GROSS_MARGIN_PERCENT:
        raise ValueError(
            f"Gross Margin is too low: {gross_margin_percent:.2f}% (Limit is {MIN_GROSS_MARGIN_PERCENT}%). "
            f"COGS: ${cogs_model.total_cogs_per_user_usd}, ARPU: ${rev_model.blended_arpu_usd}. "
            f"Rejecting architecture."
        )

    if cogs_model.total_cogs_per_user_usd > rev_model.budget_constraint_usd:
        raise ValueError(
            f"COGS (${cogs_model.total_cogs_per_user_usd}) exceeds the Budget Constraint (${rev_model.budget_constraint_usd})."
        )


def _run_stress_test(rev_model: RevenueModel, cogs_model: UnitEconomicsModel) -> None:
    stress_arpu = rev_model.blended_arpu_usd * STRESS_ARPU_FACTOR
    stress_cogs = cogs_model.total_cogs_per_user_usd * STRESS_COGS_FACTOR
    if (stress_arpu - stress_cogs) < 0:
        print(
            "Economics Stress Test failed: resulting margin falls below zero.",
            file=sys.stderr,
        )
        sys.exit(1)


def run_validation(file_path: Path, fix: bool = False) -> UnitEconomicsModel:
    rev_model, cogs_model = _load_models(file_path)

    _validate_blended_arpu(rev_model)

    calculated_cogs, _total_var = _calculate_cogs(
        rev_model, cogs_model.cogs_per_user_usd
    )
    _validate_cogs_total(calculated_cogs, cogs_model)
    _validate_gross_margin(rev_model, cogs_model)
    _run_stress_test(rev_model, cogs_model)

    return cogs_model
