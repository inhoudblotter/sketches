from pathlib import Path
from departments.discovery.tools.linters.discovery_linter.validators.domain.domain_dictionary import (
    run_validation as run_validate_domain_dictionary,
)
from departments.discovery.tools.linters.discovery_linter.validators.domain.domain_summary import (
    run_validation as run_validate_domain_summary,
)
from departments.discovery.tools.linters.discovery_linter.validators.epic.features import (
    run_validation as run_validate_features,
)
from departments.discovery.tools.linters.discovery_linter.validators.epic.job_stories import (
    run_validation as run_validate_job_stories,
)
from departments.discovery.tools.linters.discovery_linter.validators.epic.job_stories_content import (
    run_lint_job_stories_content,
)
from departments.discovery.tools.linters.discovery_linter.validators.domain.domain_orphans import (
    run_check_domain_orphans,
)
from departments.discovery.tools.linters.discovery_linter.validators.epic.errata import (
    run_validation as run_validate_errata,
)
from departments.discovery.tools.shared.epic_utils import iter_epic_dirs


def _validate_dictionary(domain_dir: Path, fix: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    dictionary_file = domain_dir / "dictionary.yaml"
    if not dictionary_file.exists():
        if fix:
            warnings.append("[WARN] dictionary.yaml missing — skipped in --fix mode")
        return errors, warnings
    try:
        run_validate_domain_dictionary(dictionary_file)
    except Exception as e:
        errors.append(f"dictionary.yaml: {e}")
    return errors, warnings


def _validate_summary(domain_dir: Path, fix: bool):
    errors: list[str] = []
    warnings: list[str] = []
    summary_file = domain_dir / "summary.yaml"
    summary_schema = None
    if not summary_file.exists():
        if fix:
            warnings.append("[WARN] summary.yaml missing — skipped in --fix mode")
        return errors, warnings, summary_schema
    try:
        summary_schema = run_validate_domain_summary(summary_file)
    except Exception as e:
        errors.append(f"summary.yaml: {e}")
    return errors, warnings, summary_schema


def _validate_epics(epics_dir: Path, fix: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for js_file in sorted(epics_dir.glob("*/stories.yaml")):
        try:
            run_validate_job_stories(js_file)
        except Exception as e:
            errors.append(f"epics/{js_file.parent.name}/{js_file.name}: {e}")

    feature_files = sorted(epics_dir.glob("*/features.yaml"))
    if not feature_files and fix:
        warnings.append("[WARN] no epics/*/features.yaml found — skipped in --fix mode")
    for feat_file in feature_files:
        try:
            run_validate_features(feat_file)
        except Exception as e:
            errors.append(f"epics/{feat_file.parent.name}/{feat_file.name}: {e}")

    return errors, warnings


def _validate_domain_dir_lints(domain_dir: Path) -> list[str]:
    errors = []
    try:
        run_lint_job_stories_content(domain_dir)
    except Exception as e:
        errors.append(str(e))

    try:
        run_check_domain_orphans(domain_dir)
    except Exception as e:
        errors.append(str(e))

    return errors


def _validate_summary_consistency(summary_schema, domain_dir: Path) -> list[str]:
    errors = []
    epics_dir = domain_dir / "epics"
    summary_epic_ids = {epic.epic_id for epic in summary_schema.epics}

    for epic_dir in iter_epic_dirs(domain_dir):
        if epic_dir.name not in summary_epic_ids:
            errors.append(
                f"Directory epics/{epic_dir.name} exists on disk, but epic '{epic_dir.name}' is missing from summary.yaml"
            )

    for epic in summary_schema.epics:
        epic_dir = epics_dir / epic.epic_id
        if not (epic_dir / "stories.yaml").exists():
            errors.append(
                f"summary.yaml lists epic '{epic.epic_id}' but epics/{epic.epic_id}/stories.yaml is missing "
                "(partial write: summary.yaml was written before the epic loop finished, or the epic failed mid-write)"
            )
        if not (epic_dir / "features.yaml").exists():
            errors.append(
                f"summary.yaml lists epic '{epic.epic_id}' but epics/{epic.epic_id}/features.yaml is missing"
            )

    return errors


def _validate_errata(domain_dir: Path, epics_dir: Path, fix: bool) -> list[str]:
    errors = []

    domain_errata_file = domain_dir / "domain_errata.yaml"
    if domain_errata_file.exists():
        try:
            res = run_validate_errata(domain_errata_file, fix=fix)
            if not res.is_valid:
                errors.extend([f"domain_errata.yaml: {err}" for err in res.errors])
        except Exception as e:
            errors.append(f"domain_errata.yaml: {e}")

    if epics_dir.exists() and epics_dir.is_dir():
        for errata_file in sorted(epics_dir.glob("*/errata.yaml")):
            try:
                res = run_validate_errata(errata_file, fix=fix)
                if not res.is_valid:
                    errors.extend(
                        [
                            f"epics/{errata_file.parent.name}/errata.yaml: {err}"
                            for err in res.errors
                        ]
                    )
            except Exception as e:
                errors.append(f"epics/{errata_file.parent.name}/errata.yaml: {e}")

    return errors


def run_validate_domain(domain_dir: Path, fix: bool = True):
    errors = []
    warnings = []
    epics_dir = domain_dir / "epics"

    dict_errors, dict_warnings = _validate_dictionary(domain_dir, fix)
    errors.extend(dict_errors)
    warnings.extend(dict_warnings)

    summary_errors, summary_warnings, summary_schema = _validate_summary(
        domain_dir, fix
    )
    errors.extend(summary_errors)
    warnings.extend(summary_warnings)

    if epics_dir.exists() and epics_dir.is_dir():
        epics_errors, epics_warnings = _validate_epics(epics_dir, fix)
        errors.extend(epics_errors)
        warnings.extend(epics_warnings)
        errors.extend(_validate_domain_dir_lints(domain_dir))

    if summary_schema is not None:
        errors.extend(_validate_summary_consistency(summary_schema, domain_dir))

    errors.extend(_validate_errata(domain_dir, epics_dir, fix))

    if warnings:
        print("\n".join(warnings))

    if errors:
        raise ValueError("\n\n---\n\n".join(errors))
    return True
