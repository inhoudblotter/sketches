import yaml
from pathlib import Path

import pytest

from .. import run_validation

_BASE_CONFIG = {
    "technology_stack": {"backend": "Go"},
    "resource_quotas_per_user": {
        "storage_gb": 0.5,
        "database_reads_per_month": 100,
        "database_writes_per_month": 10,
        "egress_bandwidth_gb": 1.0,
        "external_api_calls": [],
    },
    "compliance_flags": [],
    "growth_path": [],
    "maintainability_notes": "n/a",
    "strategic_insight": "n/a",
}


def _write_tech_constraints(strategy_dir: Path, data_sourcing: list) -> Path:
    strategy_dir.mkdir(parents=True, exist_ok=True)
    file_path = strategy_dir / "tech_constraints.yaml"
    file_path.write_text(
        yaml.dump({**_BASE_CONFIG, "data_sourcing": data_sourcing}, allow_unicode=True),
        encoding="utf-8",
    )
    return file_path


def _write_feature(domains_dir: Path, domain: str, epic: str, feature_id: str) -> None:
    epic_dir = domains_dir / domain / "epics" / epic
    epic_dir.mkdir(parents=True, exist_ok=True)
    (epic_dir / "features.yaml").write_text(
        yaml.dump(
            {
                "features": {
                    "mvp_mandatory": [
                        {"id": feature_id, "name": feature_id, "linked_job_stories": []}
                    ]
                }
            }
        ),
        encoding="utf-8",
    )


def _entry(domain: str, feature_id: str) -> dict:
    return {
        "domain": domain,
        "feature_id": feature_id,
        "feature_name": "Card Payment",
        "automation_verdict": "manual-required",
        "moderation_signal": "~50 записей/день",
        "legal_flags": [],
    }


def test_valid_domain_feature_id_pair_passes(tmp_path: Path):
    domains_dir = tmp_path / "domains"
    _write_feature(domains_dir, "billing", "invoicing", "card_payment")
    file_path = _write_tech_constraints(
        tmp_path / "strategy", [_entry("billing", "card_payment")]
    )

    config = run_validation(file_path, fix=False)

    assert config.data_sourcing[0].feature_id == "card_payment"


def test_hallucinated_feature_id_fails(tmp_path: Path):
    domains_dir = tmp_path / "domains"
    _write_feature(domains_dir, "billing", "invoicing", "card_payment")
    file_path = _write_tech_constraints(
        tmp_path / "strategy", [_entry("billing", "nonexistent_feature")]
    )

    with pytest.raises(ValueError, match="not found in any features.yaml"):
        run_validation(file_path, fix=False)


def test_unknown_domain_fails(tmp_path: Path):
    domains_dir = tmp_path / "domains"
    _write_feature(domains_dir, "billing", "invoicing", "card_payment")
    file_path = _write_tech_constraints(
        tmp_path / "strategy", [_entry("ghost_domain", "card_payment")]
    )

    with pytest.raises(ValueError, match="does not exist"):
        run_validation(file_path, fix=False)


def test_empty_data_sourcing_skips_cross_reference_check(tmp_path: Path):
    # No domains/ directory at all next to strategy/ — must not be required
    # when there is nothing in data_sourcing to resolve.
    file_path = _write_tech_constraints(tmp_path / "strategy", [])

    config = run_validation(file_path, fix=False)

    assert config.data_sourcing == []


def test_feature_id_unique_across_epics_in_same_domain(tmp_path: Path):
    """query-discovery's own `features` command merges feature ids across every
    epic of a domain (no epic key) — this check mirrors that same aggregation,
    so a match in ANY epic of the stated domain must pass."""
    domains_dir = tmp_path / "domains"
    _write_feature(domains_dir, "billing", "refunds", "card_payment")
    file_path = _write_tech_constraints(
        tmp_path / "strategy", [_entry("billing", "card_payment")]
    )

    config = run_validation(file_path, fix=False)

    assert config.data_sourcing[0].domain == "billing"
