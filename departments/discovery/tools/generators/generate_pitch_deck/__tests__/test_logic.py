import yaml
from pathlib import Path

from ..schemas import GeneratePitchDeckInput
from ..logic import run_generate_pitch_deck

_DATA_SOURCING_ENTRY = {
    "domain": "billing",
    "feature_id": "card_payment",
    "feature_name": "Card Payment",
    "automation_verdict": "manual-required",
    "moderation_signal": "~50 записей/день, ручная проверка",
    "legal_flags": ["Лицензия запрещает коммерческое использование"],
}


def _write_yaml(path: Path, data: dict) -> Path:
    path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return path


def test_data_sourcing_slide_renders_when_present(tmp_path: Path):
    yaml_path = _write_yaml(tmp_path / "pitch_deck.yaml", {})
    detail_path = _write_yaml(
        tmp_path / "project_analytics_detail.yaml",
        {"tech": {"data_sourcing": [_DATA_SOURCING_ENTRY]}},
    )
    out_path = tmp_path / "pitch_deck.html"

    result = run_generate_pitch_deck(
        GeneratePitchDeckInput(
            yaml_path=yaml_path,
            out_path=out_path,
            analytics_path=None,
            detail_path=detail_path,
        )
    )

    html = out_path.read_text(encoding="utf-8")
    assert "Data Dependency" in html
    assert "Card Payment" in html
    assert "billing" in html
    assert "manual-required" in html
    assert "Лицензия запрещает коммерческое использование" in html
    expected_slides = 3  # Title + Tech + Data Dependency slide
    assert result.slides_count == expected_slides


def test_data_sourcing_slide_absent_without_tech(tmp_path: Path):
    yaml_path = _write_yaml(tmp_path / "pitch_deck.yaml", {})
    out_path = tmp_path / "pitch_deck.html"

    result = run_generate_pitch_deck(
        GeneratePitchDeckInput(
            yaml_path=yaml_path,
            out_path=out_path,
            analytics_path=None,
            detail_path=None,
        )
    )

    html = out_path.read_text(encoding="utf-8")
    assert "Data Dependency" not in html
    assert result.slides_count == 1  # Title slide only


def test_dashboard_abbreviates_large_figures(tmp_path: Path):
    yaml_path = _write_yaml(tmp_path / "pitch_deck.yaml", {})
    analytics_path = _write_yaml(
        tmp_path / "project_analytics.yaml",
        {
            "dashboard": {
                "margin_pct": 62.3,
                "margin_color": "text-green",
                "arpu": 12.5,
                "cogs": 4.7,
                "budget_color": "text-green",
                "bep_display": "2.3M Users",
                "fixed_monthly": 5_400_000,
                "infra_fixed_monthly": 3_100_000,
                "operations_payroll_monthly": 2_300_000,
                "mrr": 87_650_000,
                "mau": 7_012_345,
                "streams": [{"share": 100, "name": "SUB"}],
            }
        },
    )
    out_path = tmp_path / "pitch_deck.html"

    run_generate_pitch_deck(
        GeneratePitchDeckInput(
            yaml_path=yaml_path,
            out_path=out_path,
            analytics_path=analytics_path,
            detail_path=None,
        )
    )

    html = out_path.read_text(encoding="utf-8")
    # Big numbers render abbreviated (K/M/B) in the visible metric, not raw digits.
    assert "$87.7M" in html
    assert "$87650000" not in html
    assert "7.0M" in html
    # Exact figures survive as a hover tooltip for precision.
    assert 'title="$87,650,000"' in html
    assert 'title="7,012,345"' in html


def test_data_sourcing_slide_absent_when_tech_has_no_data_sourcing(tmp_path: Path):
    yaml_path = _write_yaml(tmp_path / "pitch_deck.yaml", {})
    detail_path = _write_yaml(
        tmp_path / "project_analytics_detail.yaml",
        {"tech": {"frontend": "React", "data_sourcing": []}},
    )
    out_path = tmp_path / "pitch_deck.html"

    result = run_generate_pitch_deck(
        GeneratePitchDeckInput(
            yaml_path=yaml_path,
            out_path=out_path,
            analytics_path=None,
            detail_path=detail_path,
        )
    )

    html = out_path.read_text(encoding="utf-8")
    assert "Data Dependency" not in html
    expected_slides = 2  # Title slide + Tech slide (no data_sourcing bump)
    assert result.slides_count == expected_slides
