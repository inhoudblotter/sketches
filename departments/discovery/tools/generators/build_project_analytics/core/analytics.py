import warnings
from collections import Counter
from ..utils.common import extract_float, load_strategy_yaml


def gather_strategy_metrics(strategy_dir):
    compliance_flags = []
    infra_usd_per_month = 0.0
    platform_count = 0

    if strategy_dir.exists():
        compliance_flags = load_strategy_yaml(
            strategy_dir / "tech_constraints.yaml"
        ).get("compliance_flags", [])

        ue_data = load_strategy_yaml(strategy_dir / "unit_economics_model.yaml")
        fixed_monthly = (ue_data.get("cogs_per_user_usd") or {}).get(
            "fixed_monthly_usd"
        ) or {}
        infra_usd_per_month += extract_float(fixed_monthly.get("compute", 0))
        infra_usd_per_month += extract_float(fixed_monthly.get("database", 0))
        infra_usd_per_month += extract_float(fixed_monthly.get("p2p_infrastructure", 0))

        platform_count = len(
            load_strategy_yaml(strategy_dir / "platform_strategy.yaml").get(
                "platforms", []
            )
        )

    return compliance_flags, infra_usd_per_month, platform_count


def gather_observability_metrics(strategy_dir):
    """North Star Metric + KPI/event counts declared by the strategist in
    business_observability.yaml — the actual customer-facing success measures,
    not the raw MVP acceptance-metric tally (story.metrics), for the pitch deck's
    Risk & Impact slide.
    """
    if not strategy_dir.exists():
        return None
    obs_data = load_strategy_yaml(strategy_dir / "business_observability.yaml")
    if not obs_data:
        return None
    return {
        "north_star_metric": obs_data.get("north_star_metric", ""),
        "kpi_count": len(obs_data.get("kpi", []) or []),
        "critical_events_count": len(
            obs_data.get("critical_business_events", []) or []
        ),
    }


_MVP_PHASES = ("mvp_mandatory", "mvp_nice_to_have")
TOP_FEATURES_COUNT = 3


def _new_story_accumulator():
    return {
        "pain_distribution": {"High": 0, "Medium": 0, "Low": 0},
        "sp_by_epic": {},
        "sp_by_domain": {},
        "epic_domain": {},
        "high_risk_stories_count": 0,
        "high_risk_sp": 0,
        "flags_breakdown": Counter(),
        "total_metrics_count": 0,
        "processed_story_ids": set(),
    }


def _accumulate_story(story: dict, sp: int, acc: dict) -> None:
    epic = story.get("_epic", "Unknown")
    domain = story.get("_domain", "Unknown")
    acc["sp_by_epic"][epic] = acc["sp_by_epic"].get(epic, 0) + sp
    acc["sp_by_domain"][domain] = acc["sp_by_domain"].get(domain, 0) + sp
    acc["epic_domain"][epic] = domain

    flags = story.get("flags", []) or []
    if flags:
        acc["high_risk_stories_count"] += 1
        acc["high_risk_sp"] += sp
        acc["flags_breakdown"].update(flags)

    pain = story.get("pain_level", "Unknown")
    if pain in acc["pain_distribution"]:
        acc["pain_distribution"][pain] += 1

    acc["total_metrics_count"] += len(story.get("metrics", []))


def _process_feature_stories(
    feature: dict, phase, story_by_id: dict, acc: dict
) -> tuple[int, int]:
    """Returns (feature_sp, dedup_sp).

    feature_sp is the raw sum of story points linked to this feature, used for
    per-feature views (feature_costs/top_features) where double-counting a
    shared story across features is expected and desired.

    dedup_sp is the sum of story points for stories seen for the FIRST time
    across the whole project (gated by acc["processed_story_ids"], the same
    set used by sp_by_epic/sp_by_domain) — it is what sp_by_phase/total_mvp_sp
    must use so that a story shared across multiple MVP features/phases is
    only counted once, matching sp_by_epic/sp_by_domain semantics.
    """
    feature_sp = 0
    dedup_sp = 0
    for sid in feature.get("linked_job_stories", []):
        story = story_by_id.get(sid)
        if not story:
            continue
        if "story_points" not in story:
            warnings.warn(
                f"Warning: story '{sid}' (feature '{feature.get('id', feature.get('name', 'Unknown'))}') "
                "is missing story_points; defaulting to 0.",
                stacklevel=2,
            )
        sp = int(story.get("story_points", 0))
        feature_sp += sp

        if phase in _MVP_PHASES and sid not in acc["processed_story_ids"]:
            acc["processed_story_ids"].add(sid)
            _accumulate_story(story, sp, acc)
            dedup_sp += sp

    return feature_sp, dedup_sp


def _build_epics_by_domain(
    sp_by_epic: dict, sp_by_domain: dict, epic_domain: dict
) -> dict:
    epics_by_domain: dict[str, list] = {}
    for epic, sp in sp_by_epic.items():
        domain = epic_domain.get(epic, "Unknown")
        epics_by_domain.setdefault(domain, []).append({"epic": epic, "sp": sp})
    return {domain: epics_by_domain[domain] for domain in sp_by_domain}


def calculate_feature_metrics(features, story_by_id):
    sp_by_phase = {"mvp_mandatory": 0, "mvp_nice_to_have": 0, "future_features": 0}
    features_count_by_phase = {
        "mvp_mandatory": 0,
        "mvp_nice_to_have": 0,
        "future_features": 0,
    }
    feature_costs = []
    acc = _new_story_accumulator()

    for feature in features:
        phase = feature.get("_priority")
        feature_name = feature.get("name", feature.get("id", "Unknown"))
        feature_sp, dedup_sp = _process_feature_stories(
            feature, phase, story_by_id, acc
        )

        if phase in features_count_by_phase:
            features_count_by_phase[phase] += 1
            # MVP phases must use the same story-level dedup as sp_by_epic/sp_by_domain
            # (a story linked to multiple MVP features/phases is only counted once
            # towards total_mvp_sp); non-MVP phases keep the raw per-feature sum.
            sp_by_phase[phase] += dedup_sp if phase in _MVP_PHASES else feature_sp

            if phase in _MVP_PHASES:
                feature_costs.append({"name": feature_name, "sp": feature_sp})

    feature_costs.sort(key=lambda x: x["sp"], reverse=True)
    top_features = feature_costs[:TOP_FEATURES_COUNT]

    sp_by_epic = dict(
        sorted(acc["sp_by_epic"].items(), key=lambda item: item[1], reverse=True)
    )
    sp_by_domain = dict(
        sorted(acc["sp_by_domain"].items(), key=lambda item: item[1], reverse=True)
    )
    epics_by_domain = _build_epics_by_domain(
        sp_by_epic, sp_by_domain, acc["epic_domain"]
    )

    return {
        "sp_by_phase": sp_by_phase,
        "features_count_by_phase": features_count_by_phase,
        "pain_distribution": acc["pain_distribution"],
        "sp_by_epic": sp_by_epic,
        "sp_by_domain": sp_by_domain,
        "epics_by_domain": epics_by_domain,
        "high_risk_stories_count": acc["high_risk_stories_count"],
        "high_risk_sp": acc["high_risk_sp"],
        "flags_breakdown": dict(acc["flags_breakdown"].most_common()),
        "total_metrics_count": acc["total_metrics_count"],
        "top_features": top_features,
    }


def compact_domain_coupling(domain_coupling: dict) -> dict:
    """Counts only (depends_on/used_by entity totals per domain) — enough to spot
    monolithic overload/refocus risk without carrying every entity name; the full
    entity-level breakdown lives in project_analytics_detail.yaml.
    """
    return {
        domain: {
            "depends_on_count": sum(
                len(v) for v in (data.get("depends_on") or {}).values()
            ),
            "used_by_count": sum(len(v) for v in (data.get("used_by") or {}).values()),
        }
        for domain, data in domain_coupling.items()
    }


def compact_global_metrics(global_metrics: dict) -> dict:
    """Names only — enough to cross-check against business_observability.yaml's
    declared KPIs/events; full descriptions live in project_analytics_detail.yaml.
    """
    kpis = global_metrics.get("kpis", []) or []
    events = global_metrics.get("critical_events", []) or []
    return {
        "kpi_names": [k.get("name") for k in kpis],
        "critical_event_names": [e.get("event_name") for e in events],
    }


def compact_tech(tech: dict | None) -> dict | None:
    """Stack summary only — insight/growth_path/maintainability are pitch-deck detail,
    not needed to judge whether the tech budget is realistic.
    """
    if not tech:
        return None
    return {
        "frontend": tech.get("frontend"),
        "backend": tech.get("backend"),
        "database": tech.get("database"),
        "infra": tech.get("infra"),
        "p2p": tech.get("p2p"),
    }


def gather_flow_metrics(flows):
    flow_metrics = {
        "total_flows": len(flows),
        "total_states": 0,
        "total_shared_error_states": 0,
        "total_sla_constraints": 0,
    }
    for flow in flows:
        flow_metrics["total_states"] += len(flow.get("states", {}))
        flow_metrics["total_shared_error_states"] += len(flow.get("shared_states", {}))
        sla = flow.get("sla", {})
        if sla:
            flow_metrics["total_sla_constraints"] += sum(
                1 for v in sla.values() if v is not None
            )
    return flow_metrics
