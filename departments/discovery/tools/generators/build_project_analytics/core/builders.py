import math
from pathlib import Path
from ..utils.common import load_strategy_yaml, extract_float, _sum_nested_floats
from departments.discovery.tools.shared.text_utils import clean_links, clean_list


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
    fixed_monthly = _sum_nested_floats(cogs_dict.get("fixed_monthly_usd", {}))

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
            f"{math.ceil(bep_users):,} Users"
            if bep_users != float("inf")
            else "Negative Margin"
        ),
        "fixed_monthly": fixed_monthly,
        "mrr": mrr,
        "mau": mau,
        "streams": streams_list,
        "scenarios": scenarios,
        "speculative_upside": speculative_upside,
        "grant_runway": grant_runway,
    }


def build_tech(strategy_dir: Path) -> dict | None:
    tech_path = strategy_dir / "tech_constraints.yaml"
    if not tech_path.exists():
        return None
    tech_data = load_strategy_yaml(tech_path)
    stack = tech_data.get("technology_stack", {})
    growth_path = [
        {
            "component": clean_links(str(entry.get("component", ""))),
            "trigger": clean_links(str(entry.get("trigger", ""))),
            "action": clean_links(str(entry.get("action", ""))),
            "rewrite_cost": clean_links(str(entry.get("rewrite_cost", ""))),
        }
        for entry in (tech_data.get("growth_path") or [])
    ]
    return {
        "frontend": clean_links(stack.get("frontend", "Unknown")),
        "backend": clean_links(stack.get("backend", "Unknown")),
        "database": clean_links(stack.get("database", "Unknown")),
        "infra": clean_links(stack.get("infrastructure", "Unknown")),
        "p2p": clean_links(stack.get("p2p_network_layer", "")),
        "insight": clean_links(tech_data.get("strategic_insight", "N/A")),
        "growth_path": growth_path,
        "maintainability": clean_links(tech_data.get("maintainability_notes", "")),
    }


def build_roadmap(strategy_dir: Path) -> dict | None:
    roadmap_path = strategy_dir / "launch_roadmap.yaml"
    if not roadmap_path.exists():
        return None
    data = load_strategy_yaml(roadmap_path)
    phases = data.get("phases", {})
    parsed_phases = [
        {
            "id": phase_id,
            "description": clean_links(phase_data.get("description", "")),
            "primary_growth_loop": clean_list(
                phase_data.get("primary_growth_loop", [])
            ),
            "cold_start_tactics": clean_list(phase_data.get("cold_start_tactics", [])),
            "friction_management": clean_list(
                phase_data.get("friction_management", [])
            ),
            "ecosystem_symbiosis": clean_list(
                phase_data.get("ecosystem_symbiosis", [])
            ),
            "defensibility_moats": clean_list(
                phase_data.get("defensibility_moats", [])
            ),
            "unit_economics_validation": clean_links(
                phase_data.get("unit_economics_validation", "N/A")
            ),
            "source_ref": phase_data.get("source_ref", ""),
        }
        for phase_id, phase_data in phases.items()
    ]
    return {"phases": parsed_phases}


def build_errata(errata_path: Path) -> dict | None:
    if not errata_path.exists():
        return None
    errata_data = load_strategy_yaml(errata_path)
    blockers: list = []
    if isinstance(errata_data, dict) and "critical_errata" in errata_data:
        errata_node = errata_data["critical_errata"]
        blockers = (
            errata_node.get("actionable_blockers", [])
            if isinstance(errata_node, dict)
            else (errata_node if isinstance(errata_node, list) else [])
        )
    elif isinstance(errata_data, dict) and "actionable_blockers" in errata_data:
        blockers = errata_data.get("actionable_blockers", [])
    elif isinstance(errata_data, list):
        blockers = errata_data

    # MAGIC NUMBERS FIX: PLR2004
    MAX_BLOCKERS = 4
    parsed_blockers = []
    for b in blockers[:MAX_BLOCKERS]:
        source = b.get("source") or b.get("domain") or "Unknown"
        issue = b.get("issue") or b.get("description") or str(b)
        parsed_blockers.append(
            {
                "source": clean_links(str(source)),
                "issue": clean_links(str(issue)),
            }
        )
    return {"blockers": parsed_blockers}
