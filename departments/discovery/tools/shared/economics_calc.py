from typing import Optional

MIN_GROSS_MARGIN_PERCENT = 30
STRESS_ARPU_FACTOR = 0.8
STRESS_COGS_FACTOR = 1.4


def calc_fixed_sum(
    compute: float,
    database: float,
    p2p_infrastructure: Optional[float] = None,
    operations_payroll: Optional[float] = None,
) -> float:
    total = compute + database
    if p2p_infrastructure:
        total += p2p_infrastructure
    if operations_payroll:
        total += operations_payroll
    return total


def calc_variable_sum(
    egress_traffic: float,
    external_apis_cost: float,
    maintenance_and_support: float,
    payment_gateway_fees: float,
    tokenomics_costs: Optional[float] = None,
    hardware_amortization_usd: Optional[float] = None,
) -> float:
    total = egress_traffic
    if tokenomics_costs:
        total += tokenomics_costs
    if hardware_amortization_usd:
        total += hardware_amortization_usd
    total += external_apis_cost
    total += maintenance_and_support + payment_gateway_fees
    return total


def calc_total_cogs(
    fixed_sum: float, var_sum: float, target_mau: Optional[float]
) -> float:
    mau = target_mau if target_mau and target_mau > 0 else 1.0
    return (fixed_sum / mau) + var_sum


def calc_gross_margin_percent(
    blended_arpu_usd: float, total_cogs_per_user_usd: float
) -> float:
    if blended_arpu_usd <= 0:
        return 0.0
    return ((blended_arpu_usd - total_cogs_per_user_usd) / blended_arpu_usd) * 100
