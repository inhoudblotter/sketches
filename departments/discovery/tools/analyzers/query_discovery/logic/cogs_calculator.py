from pathlib import Path
from typing import Any, Dict

import yaml

from departments.discovery.tools.shared.economics_calc import (
    MIN_GROSS_MARGIN_PERCENT,
    calc_fixed_sum,
    calc_gross_margin_percent,
    calc_total_cogs,
    calc_variable_sum,
)


def calculate_cogs(draft_path: Path) -> dict:
    """Pure-arithmetic pre-write helper for cogs-scout: given a draft
    `cogs_per_user_usd` (compute/database/p2p_infrastructure/operations_payroll
    + egress/tokenomics/external_apis/operational) sitting next to
    revenue_model.yaml, computes the same totals the `economics` linter will
    independently verify at write time — so the agent gets the right number
    before writing `total_cogs_per_user_usd`, instead of hand-computing it and
    risking a "Total COGS mismatch" hard-fail.

    This is advisory, not a gate: it doesn't validate the draft's shape
    strictly (missing fields default to 0) and never raises on business
    thresholds — it only reports margin_ok/budget_ok for the agent to act on.
    The actual hard gate remains `discovery-linter economics`.
    """
    draft = yaml.safe_load(draft_path.read_text(encoding="utf-8")) or {}
    revenue_path = draft_path.parent / "revenue_model.yaml"
    if not revenue_path.exists():
        return {"error": f"revenue_model.yaml не найден рядом с {draft_path}"}
    revenue = yaml.safe_load(revenue_path.read_text(encoding="utf-8")) or {}

    cogs = draft.get("cogs_per_user_usd", {}) or {}
    fixed = cogs.get("fixed_monthly_usd", {}) or {}
    var = cogs.get("variable_per_user_usd", {}) or {}
    operational = var.get("operational", {}) or {}

    fixed_sum = calc_fixed_sum(
        fixed.get("compute", 0),
        fixed.get("database", 0),
        fixed.get("p2p_infrastructure"),
        fixed.get("operations_payroll"),
    )
    var_sum = calc_variable_sum(
        var.get("egress_traffic", 0),
        sum(a.get("cost", 0) for a in var.get("external_apis", []) or []),
        operational.get("maintenance_and_support", 0),
        operational.get("payment_gateway_fees", 0),
        var.get("tokenomics_costs"),
    )

    target_mau = revenue.get("target_mau")
    total = calc_total_cogs(fixed_sum, var_sum, target_mau)
    blended_arpu = revenue.get("blended_arpu_usd", 0)
    budget = revenue.get("budget_constraint_usd", 0)
    margin_percent = calc_gross_margin_percent(blended_arpu, total)

    result: Dict[str, Any] = {
        "fixed_sum_usd": round(fixed_sum, 4),
        "variable_sum_per_user_usd": round(var_sum, 4),
        "total_cogs_per_user_usd": round(total, 4),
        "gross_margin_percent": round(margin_percent, 2),
        "margin_ok": margin_percent >= MIN_GROSS_MARGIN_PERCENT,
        "budget_ok": total <= budget,
    }
    return result
