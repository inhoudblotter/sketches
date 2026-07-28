import yaml
from .schemas import BuildProjectAnalyticsInput, BuildProjectAnalyticsOutput
from departments.discovery.tools.analyzers.query_discovery.logic.core import (
    mvp_size_bucket_for_points,
)
from departments.discovery.tools.analyzers.query_discovery.logic.queries import (
    get_filtered_stories,
    get_filtered_features,
    get_filtered_flows,
)
from departments.discovery.tools.analyzers.query_discovery.logic.reports import (
    get_dependencies,
    get_data_model_metrics,
    get_domain_metrics,
)
from departments.discovery.tools.analyzers.query_discovery.logic.orphans import (
    get_coverage,
)
from .core.builders import (
    build_dashboard,
    build_tech,
    build_roadmap,
    build_errata,
)
from .core.analytics import (
    gather_strategy_metrics,
    gather_observability_metrics,
    calculate_feature_metrics,
    gather_flow_metrics,
    compact_domain_coupling,
    compact_global_metrics,
    compact_tech,
)
from departments.discovery.tools.shared.text_utils import clean_links


def run_build_project_analytics(
    input_data: BuildProjectAnalyticsInput,
) -> BuildProjectAnalyticsOutput:
    discovery_dir = input_data.workspace_path
    if not discovery_dir or not discovery_dir.exists():
        raise FileNotFoundError(f"Workspace path not found: {discovery_dir}")

    strategy_dir = discovery_dir / "strategy"
    compliance_flags, infra_usd_per_month, platforms = gather_strategy_metrics(
        strategy_dir
    )
    observability = gather_observability_metrics(strategy_dir)
    if observability:
        observability["north_star_metric"] = clean_links(
            observability["north_star_metric"]
        )

    dashboard = build_dashboard(strategy_dir) if strategy_dir.exists() else None
    tech = build_tech(strategy_dir) if strategy_dir.exists() else None
    roadmap = build_roadmap(strategy_dir) if strategy_dir.exists() else None
    errata = build_errata(discovery_dir / "errata" / "critical_errata.yaml")

    domains_dir = discovery_dir / "domains"
    if not domains_dir.exists() or not domains_dir.is_dir():
        raise ValueError(f"Domains directory not found in {discovery_dir}")

    workspace_root = discovery_dir.parent

    story_by_id = {
        s["id"]: s for s in get_filtered_stories(workspace_root) if s.get("id")
    }
    features = get_filtered_features(workspace_root)
    flows = get_filtered_flows(workspace_root)

    feature_metrics = calculate_feature_metrics(features, story_by_id)
    flow_metrics = gather_flow_metrics(flows)

    data_model_metrics = get_data_model_metrics(workspace_root, is_global=True)[
        "global_metrics"
    ]
    domain_coupling = get_dependencies(workspace_root)
    missing_mandatory_epics = get_coverage(workspace_root).get(
        "missing_mandatory_epics", {}
    )
    global_metrics = get_domain_metrics(workspace_root, is_global=True).get(
        "global_metrics", {}
    )

    total_mvp_sp = (
        feature_metrics["sp_by_phase"]["mvp_mandatory"]
        + feature_metrics["sp_by_phase"]["mvp_nice_to_have"]
    )

    mvp_size_bucket, mvp_size_description = mvp_size_bucket_for_points(total_mvp_sp)

    # Compact file: everything the discovery-pitcher's Red Teaming/go-no-go audit
    # actually reads (budget-vs-scope, risk concentration, coverage gaps, KPI
    # cross-check, monolith/refocus check, margin scenarios). Kept small on purpose.
    result_data = {
        "project_analytics": {
            "total_mvp_sp": total_mvp_sp,
            "mvp_size_bucket": mvp_size_bucket,
            "mvp_size_description": mvp_size_description,
            "sp_by_phase": feature_metrics["sp_by_phase"],
            "sp_by_domain": feature_metrics["sp_by_domain"],
            "high_risk_stories_count": feature_metrics["high_risk_stories_count"],
            "high_risk_sp": feature_metrics["high_risk_sp"],
            "flags_breakdown": feature_metrics["flags_breakdown"],
            "features_count_by_phase": feature_metrics["features_count_by_phase"],
            "domain_coupling": compact_domain_coupling(domain_coupling),
            "flow_metrics": flow_metrics,
            "compliance_flags": compliance_flags,
            "infrastructure_usd_per_month": infra_usd_per_month,
            "platforms": platforms,
            "platform_count": len(platforms) if platforms else 0,
            "missing_mandatory_epics": missing_mandatory_epics,
            "global_metrics": compact_global_metrics(global_metrics),
            "observability": observability,
        },
        "dashboard": dashboard,
        "tech_summary": compact_tech(tech),
        "errata_data": errata,
    }

    # Detail file: pitch-deck-only rendering data (Epic/Domain Complexity, Tech,
    # Roadmap, Architecture slides) — not needed for the investment memo audit,
    # queried on demand by generate-pitch-deck via --detail.
    detail_data = {
        "sp_by_epic": feature_metrics["sp_by_epic"],
        "epics_by_domain": feature_metrics["epics_by_domain"],
        "top_features": feature_metrics["top_features"],
        "pain_distribution": feature_metrics["pain_distribution"],
        "total_metrics_count": feature_metrics["total_metrics_count"],
        "data_model_metrics": data_model_metrics,
        "domain_coupling": domain_coupling,
        "global_metrics": global_metrics,
        "tech": tech,
        "roadmap": roadmap,
    }

    meta_dir = discovery_dir / "meta"
    meta_dir.mkdir(exist_ok=True, parents=True)
    out_file = meta_dir / "project_analytics.yaml"
    detail_file = meta_dir / "project_analytics_detail.yaml"

    with open(out_file, "w", encoding="utf-8") as f:
        yaml.dump(result_data, f, sort_keys=False, allow_unicode=True)

    with open(detail_file, "w", encoding="utf-8") as f:
        yaml.dump(detail_data, f, sort_keys=False, allow_unicode=True)

    return BuildProjectAnalyticsOutput(
        index_path=str(out_file),
        detail_path=str(detail_file),
        total_mvp_sp=total_mvp_sp,
        mvp_size_bucket=mvp_size_bucket,
        high_risk_stories_count=feature_metrics["high_risk_stories_count"],
        compliance_flags=compliance_flags,
        infrastructure_usd_per_month=infra_usd_per_month,
    )
