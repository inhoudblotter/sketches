import math
from pathlib import Path
from ...utils.common import load_strategy_yaml, extract_float, _sum_nested_floats
from departments.discovery.tools.shared.text_utils import (
    clean_links,
    format_compact_number,
)


def _build_scenarios(scenario_bands: dict, cogs: float) -> list | None:
    """Worst/Base/Best MRR & margin, reusing the same COGS (scenario_bands only re-forecasts
    market-side MAU/ARPU per business-synthesizer's Scenario Drivers, not the cost side).
    """
    result = []
    for name in ("worst", "base", "best"):
        band = scenario_bands.get(name)
        if not isinstance(band, dict):
            continue
        arpu = extract_float(band.get("blended_arpu_usd", 0))
        mau = extract_float(band.get("target_mau", 0))
        # MAGIC NUMBERS FIX: PLR2004
        PERCENT_MULTIPLIER = 100
        margin_pct = ((arpu - cogs) / arpu * PERCENT_MULTIPLIER) if arpu > 0 else 0
        result.append(
            {
                "name": name,
                "driver_ref": clean_links(str(band.get("driver_ref", ""))),
                "arpu": arpu,
                "mau": mau,
                "mrr": arpu * mau,
                "margin_pct": margin_pct,
            }
        )
    return result or None


def build_dashboard(strategy_dir: Path) -> dict | None:
    """Financial dashboard for the pitch deck: margin/MRR/break-even, sourced from
    revenue_model.yaml + unit_economics_model.yaml (revenue-scout / cogs-scout outputs).
    """
    rev_path = strategy_dir / "revenue_model.yaml"
    unit_path = strategy_dir / "unit_economics_model.yaml"
    if not rev_path.exists() or not unit_path.exists():
        return None

    rev_data = load_strategy_yaml(rev_path)
    unit_data = load_strategy_yaml(unit_path)

    arpu = extract_float(rev_data.get("blended_arpu_usd", 0))
    mau = extract_float(rev_data.get("target_mau", 0))
    budget_limit = extract_float(rev_data.get("budget_constraint_usd", 0))

    # Dashboard top streams reflect committed revenue only — proposed/deferred/rejected
    # streams carry no share weight and belong in speculative_scenario, not this MRR breakdown.
    streams = rev_data.get("revenue_streams", [])
    committed_streams = [
        s for s in streams if s.get("commitment_status", "proposed") == "committed"
    ] or streams

    # MAGIC NUMBERS FIX: PLR2004
    TOP_STREAMS_COUNT = 3
    streams_list = [
        {
            "share": extract_float(s.get("expected_share_percent", 0)),
            "name": str(s.get("id", "Unknown")).upper(),
        }
        for s in committed_streams[:TOP_STREAMS_COUNT]
    ]

    cogs_dict = unit_data.get("cogs_per_user_usd", {})
    cogs = extract_float(unit_data.get("total_cogs_per_user_usd", 0))
    fixed_monthly_dict = cogs_dict.get("fixed_monthly_usd", {})
    operations_payroll_monthly = extract_float(
        fixed_monthly_dict.get("operations_payroll", 0)
    )
    fixed_monthly = _sum_nested_floats(fixed_monthly_dict)
    infra_fixed_monthly = fixed_monthly - operations_payroll_monthly

    var_per_user = cogs_dict.get("variable_per_user_usd", {})
    tokenomics_costs = (
        var_per_user.get("tokenomics_costs", 0) if isinstance(var_per_user, dict) else 0
    )
    if cogs == 0 and tokenomics_costs:
        cogs = extract_float(tokenomics_costs)

    gross_margin = arpu - cogs
    # MAGIC NUMBERS FIX: PLR2004
    PERCENT_MULTIPLIER = 100
    margin_pct = (gross_margin / arpu * PERCENT_MULTIPLIER) if arpu > 0 else 0
    mrr = arpu * mau
    bep_users = (fixed_monthly / gross_margin) if gross_margin > 0 else float("inf")

    scenario_bands = rev_data.get("scenario_bands") or {}
    scenarios = _build_scenarios(scenario_bands, cogs) if scenario_bands else None

    speculative = rev_data.get("speculative_scenario") or None
    speculative_upside = None
    if speculative:
        speculative_upside = {
            "combined_confidence": speculative.get("combined_confidence", "low"),
            "projected_uplift_arpu_usd": extract_float(
                speculative.get("projected_uplift_arpu_usd", 0)
            ),
            "blended_arpu_with_speculative_usd": extract_float(
                speculative.get("blended_arpu_with_speculative_usd", 0)
            ),
        }

    # Grant runway is informational only — never blended into arpu/margin above.
    grant_runway = None
    non_arpu_funding = rev_data.get("non_arpu_funding") or []
    if non_arpu_funding:
        awarded = [
            f for f in non_arpu_funding if f.get("application_status") == "awarded"
        ]
        pipeline = [
            f
            for f in non_arpu_funding
            if f.get("application_status") in ("candidate", "applied")
        ]
        awarded_total_usd = sum(
            extract_float(f.get("total_amount_usd", 0)) for f in awarded
        )
        awarded_monthly_offset_usd = sum(
            extract_float(f.get("monthly_runway_offset_usd", 0)) for f in awarded
        )
        grant_runway = {
            "awarded_total_usd": awarded_total_usd,
            "awarded_monthly_offset_usd": awarded_monthly_offset_usd,
            "awarded_runway_months": (
                (awarded_total_usd / awarded_monthly_offset_usd)
                if awarded_monthly_offset_usd > 0
                else 0
            ),
            "pipeline_total_usd": sum(
                extract_float(f.get("total_amount_usd", 0)) for f in pipeline
            ),
            "pipeline_count": len(pipeline),
        }

    # MAGIC NUMBERS FIX: PLR2004
    MARGIN_GREEN_THRESHOLD = 50
    MARGIN_RED_THRESHOLD = 20

    return {
        "margin_pct": margin_pct,
        "margin_color": (
            "text-green"
            if margin_pct >= MARGIN_GREEN_THRESHOLD
            else ("text-red" if margin_pct < MARGIN_RED_THRESHOLD else "text-white")
        ),
        "arpu": arpu,
        "cogs": cogs,
        "budget_color": ("text-red" if (cogs > budget_limit > 0) else "text-green"),
        "bep_display": (
            f"{format_compact_number(math.ceil(bep_users))} Users"
            if bep_users != float("inf")
            else "Negative Margin"
        ),
        "fixed_monthly": fixed_monthly,
        "infra_fixed_monthly": infra_fixed_monthly,
        "operations_payroll_monthly": operations_payroll_monthly,
        "mrr": mrr,
        "mau": mau,
        "streams": streams_list,
        "scenarios": scenarios,
        "speculative_upside": speculative_upside,
        "grant_runway": grant_runway,
    }
