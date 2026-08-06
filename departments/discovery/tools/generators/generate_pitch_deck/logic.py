import warnings
import markdown
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from .schemas import GeneratePitchDeckInput, GeneratePitchDeckOutput
from departments.discovery.tools.shared.text_utils import (
    clean_links,
    clean_list,
    format_compact_number,
)
from departments.discovery.tools.shared.file_utils import load_yaml

NARRATIVE_SLIDES_BEFORE_ACTORS = [
    ("problem", "Проблема (The Problem)"),
    ("solution", "Решение (The Solution)"),
    ("market_and_competition", "Рынок и Конкуренты (Market & Competition)"),
]
NARRATIVE_SLIDES_AFTER_ACTORS = [
    ("go_to_market", "Go-to-Market Стратегия"),
]

# Scope (incl. Size), Epics (by Domain), Pain, Observability, Flags, Data Model,
# Architecture slides.
SCOPE_ANALYTICS_SLIDES = 7
SCOPE_ANALYTICS_SLIDES_WITH_COMPLIANCE = SCOPE_ANALYTICS_SLIDES + 1


def _count_tech_slides(tech: dict | None) -> int:
    """Tech Stack slide (1) plus Data Dependency & Integrity slide (1, only when
    `tech.data_sourcing` is non-empty — see build_tech/compact_tech)."""
    if not tech:
        return 0
    return 1 + bool(tech.get("data_sourcing"))


def _load_optional_yaml(path, label: str) -> dict:
    if not (path and path.exists()):
        return {}
    try:
        return load_yaml(path)
    except Exception as e:
        warnings.warn(f"Warning: Failed to load {label}: {e}", stacklevel=2)
        return {}


def _build_narrative_slide(
    mandatory: dict, key: str, display_title: str
) -> dict | None:
    slide_data = mandatory.get(key, {})
    content = slide_data.get("content", "")
    if not content.strip():
        return None
    clean_content = clean_links(content.strip())
    return {
        "title": display_title,
        "content_html": markdown.markdown(clean_content),
    }


def _build_narrative_slides(
    mandatory: dict, slide_specs: list[tuple[str, str]]
) -> list[dict]:
    narrative_slides = []
    for key, display_title in slide_specs:
        slide = _build_narrative_slide(mandatory, key, display_title)
        if slide:
            narrative_slides.append(slide)
    return narrative_slides


def _build_narrative_section(pitch_data: dict) -> tuple[list[dict], list[dict], int]:
    mandatory = pitch_data.get("mandatory_slides", {})

    slides_before_actors = _build_narrative_slides(
        mandatory, NARRATIVE_SLIDES_BEFORE_ACTORS
    )
    slides_after_actors = _build_narrative_slides(
        mandatory, NARRATIVE_SLIDES_AFTER_ACTORS
    )

    # 3.5 Optional Web3 Slides — appended after Go-to-Market, still part of the
    # opening pitch narrative.
    optional = pitch_data.get("optional_slides", {})
    if "network_effects_and_decentralization" in optional:
        opt_content = optional["network_effects_and_decentralization"].get(
            "content", ""
        )
        if opt_content.strip():
            clean_opt_content = clean_links(opt_content.strip())
            slides_after_actors.append(
                {
                    "title": "Сетевые Эффекты и Децентрализация",
                    "content_html": markdown.markdown(clean_opt_content),
                }
            )

    slides_count = len(slides_before_actors) + len(slides_after_actors)
    return slides_before_actors, slides_after_actors, slides_count


def _build_actors(analytics_data: dict, detail_data: dict) -> dict | None:
    return detail_data.get("actors") or analytics_data.get("project_analytics", {}).get(
        "actors_summary"
    )


def _build_scope_analytics(analytics_data: dict, detail_data: dict) -> dict:
    # 6. Analytics Slides — compact project_analytics plus the detail-only fields
    # the deck's Epic/Domain Complexity, Risk and Architecture slides need
    # (sp_by_epic/epics_by_domain, top_features, pain_distribution,
    # total_metrics_count, data_model_metrics, full domain_coupling).
    return {
        **analytics_data.get("project_analytics", {}),
        **{
            k: v
            for k, v in {
                "sp_by_epic": detail_data.get("sp_by_epic"),
                "epics_by_domain": detail_data.get("epics_by_domain"),
                "top_features": detail_data.get("top_features"),
                "pain_distribution": detail_data.get("pain_distribution"),
                "total_metrics_count": detail_data.get("total_metrics_count"),
                "data_model_metrics": detail_data.get("data_model_metrics"),
                "domain_coupling": detail_data.get("domain_coupling"),
                # compliance_flags come straight from tech_constraints.yaml with
                # inline traceability citations — fine for the audit trail in
                # project_analytics.yaml, but the deck is investor-facing.
                "compliance_flags": clean_list(
                    analytics_data.get("project_analytics", {}).get("compliance_flags")
                ),
            }.items()
            if v is not None
        },
    }


def run_generate_pitch_deck(
    input_data: GeneratePitchDeckInput,
) -> GeneratePitchDeckOutput:
    if not input_data.yaml_path.exists():
        raise FileNotFoundError(f"YAML file not found: {input_data.yaml_path}")

    try:
        pitch_data = load_yaml(input_data.yaml_path)
    except Exception as e:
        raise ValueError(
            f"Failed to parse YAML file {input_data.yaml_path}: {e}"
        ) from e

    # All aggregated analytics are pre-computed by build_project_analytics — this tool
    # only renders them, it never reads strategy_dir/errata/domains directly.
    # project_analytics.yaml is the compact file (dashboard/tech_summary/errata/
    # scope_analytics) the discovery-pitcher reads for its audit; project_analytics_
    # detail.yaml carries the verbose, pitch-deck-only rendering data (full tech,
    # roadmap, sp_by_epic/epics_by_domain, data_model_metrics, full domain_coupling).
    analytics_data = _load_optional_yaml(input_data.analytics_path, "project analytics")
    detail_data = _load_optional_yaml(
        input_data.detail_path, "project analytics detail"
    )

    context = {}
    slides_count = 1  # Title slide

    # 1. Title Slide
    title_data = pitch_data.get("title_slide", {})
    context["pitch_title"] = title_data.get("title", "Pitch Deck")
    context["subtitle"] = title_data.get("subtitle", "")

    # 2. Automated Financial Dashboard
    context["dashboard"] = analytics_data.get("dashboard")
    dashboard_included = bool(context["dashboard"])
    if dashboard_included:
        slides_count += 3 if context["dashboard"].get("scenarios") else 2

    # 3. Mandatory Narrative Slides, split around the Actors slide (placed right
    # after Market & Competition — who we serve, concretely, before GTM).
    mandatory = pitch_data.get("mandatory_slides", {})
    slides_before_actors, slides_after_actors, narrative_slides_count = (
        _build_narrative_section(pitch_data)
    )
    context["narrative_slides_before_actors"] = slides_before_actors
    context["narrative_slides_after_actors"] = slides_after_actors
    slides_count += narrative_slides_count

    # 3.1 Actors Slide (personas, machine personas, operational actors/coverage)
    context["actors"] = _build_actors(analytics_data, detail_data)
    slides_count += bool(context["actors"])

    # Risks is a narrative slide too, but placed at the end of the deck (right
    # before financials) rather than in the opening pitch — see storytelling
    # order in pitch_deck.html.j2.
    context["risks_slide"] = _build_narrative_slide(
        mandatory, "risks", "Ключевые риски (Key Risks)"
    )
    if context["risks_slide"]:
        slides_count += 1

    # 3.2 Final Verdict Slide
    context["final_verdict_slide"] = _build_narrative_slide(
        mandatory, "final_verdict", "Инвестиционный тезис (Investment Thesis)"
    )
    if context["final_verdict_slide"]:
        slides_count += 1

    # 4. Tech Slide (full stack detail lives in project_analytics_detail.yaml;
    # fall back to the compact tech_summary if detail wasn't generated/passed) + 4.1
    # Data Dependency & Integrity Slide (detail-only, part of `tech.data_sourcing`;
    # tech_summary never carries it — see compact_tech — so that one only fires with detail_data)
    context["tech"] = detail_data.get("tech") or analytics_data.get("tech_summary")
    slides_count += _count_tech_slides(context["tech"])

    # 4.5 Roadmap Slide (detail-only)
    context["roadmap"] = detail_data.get("roadmap")
    if context["roadmap"]:
        slides_count += 1

    # 5. Errata Slide — only worth a slide when there's an actual blocker to show;
    # "no blockers found" isn't investor-facing content, and Red Team findings now
    # live in the hand-authored mandatory_slides.risks slide instead.
    context["errata_data"] = analytics_data.get("errata_data")
    if context["errata_data"] and context["errata_data"].get("blockers"):
        slides_count += 1

    context["scope_analytics"] = _build_scope_analytics(analytics_data, detail_data)
    if context["scope_analytics"]:
        slides_count += (
            SCOPE_ANALYTICS_SLIDES_WITH_COMPLIANCE
            if context["scope_analytics"].get("compliance_flags")
            else SCOPE_ANALYTICS_SLIDES
        )

    # Render Jinja Template
    templates_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    env.filters["compact"] = format_compact_number
    env.filters["commas"] = lambda value, decimals=0: f"{float(value):,.{decimals}f}"
    template = env.get_template("pitch_deck.html.j2")

    final_html = template.render(**context)

    input_data.out_path.parent.mkdir(parents=True, exist_ok=True)
    input_data.out_path.write_text(final_html, encoding="utf-8")

    return GeneratePitchDeckOutput(
        html_path=str(input_data.out_path),
        slides_count=slides_count,
        dashboard_included=dashboard_included,
    )
