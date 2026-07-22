import os
from pathlib import Path
from typing import List, Tuple

from departments.discovery.tools.linters.discovery_linter.validators.general.strategy import (
    run_validate_strategy,
)
from departments.discovery.tools.linters.discovery_linter.validators.domain.domain import (
    run_validate_domain,
)
from departments.discovery.tools.linters.discovery_linter.validators.strategy.business_observability import (
    run_validation as run_validate_business_observability,
)
from departments.discovery.tools.linters.discovery_linter.validators.tech.entity_graph import (
    run_validate_entity_graph,
    ValidateEntityGraphInput,
)
from departments.discovery.tools.linters.discovery_linter.validators.markdown.markdown_links import (
    run_validation as run_validate_markdown_links,
    ValidateMarkdownLinksInput,
)
from departments.discovery.tools.linters.discovery_linter.validators.epic.errata import (
    run_validation as run_validate_errata,
)
from departments.discovery.tools.linters.discovery_linter.validators.epic.estimation import (
    run_validation as run_validate_estimation,
)
from departments.discovery.tools.linters.discovery_linter.validators.tech.tech_synthesis import (
    run_validation as run_validate_tech_synthesis,
    ValidateTechSynthesisInput,
)
from departments.discovery.tools.linters.discovery_linter.validators.strategy.revenue_model import (
    run_validation as run_validate_revenue_model,
)
from departments.discovery.tools.linters.discovery_linter.validators.strategy.economics import (
    run_validation as validate_economics,
)
from departments.discovery.tools.linters.discovery_linter.validators.strategy.pitch_deck import (
    run_validation as run_validate_pitch_deck,
)
from departments.discovery.tools.linters.discovery_linter.validators.strategy.launch_roadmap import (
    run_validation as run_validate_launch_roadmap,
)
from departments.discovery.tools.linters.discovery_linter.validators.tech.tech_market_brief import (
    run_validation as run_validate_tech_market_brief,
)

from departments.discovery.tools.linters.discovery_linter.validators.general.workspace.models import (
    WorkspaceValidationResult,
    DomainResult,
)
from departments.discovery.tools.linters.discovery_linter.validators.general.workspace.cross_domain import (
    build_domain_index,
    check_cross_domain_refs,
    check_platforms,
)


def _validate_tech_market_brief(strategy_dir: Path) -> List[str]:
    tmb_file = strategy_dir / "tech_market_brief.yaml"
    if not tmb_file.exists():
        return []
    try:
        run_validate_tech_market_brief(tmb_file)
        return []
    except Exception as e:
        return ["tech_market_brief.yaml:\n" + str(e)]


def _validate_tech_synthesis(strategy_dir: Path, fix: bool) -> List[str]:
    try:
        synth_result = run_validate_tech_synthesis(
            ValidateTechSynthesisInput(strategy_dir=str(strategy_dir)), fix=fix
        )
        return [] if synth_result.is_valid else list(synth_result.errors)
    except Exception as e:
        return [f"Tech Synthesis Validation Error: {e}"]


def _validate_revenue_and_economics(strategy_dir: Path, fix: bool) -> List[str]:
    errors = []
    rm_file = strategy_dir / "revenue_model.yaml"
    if rm_file.exists():
        try:
            run_validate_revenue_model(rm_file)
        except Exception as e:
            errors.append(f"revenue_model.yaml: {e}")

    ue_file = strategy_dir / "unit_economics.yaml"
    if rm_file.exists() and ue_file.exists():
        try:
            validate_economics(ue_file, fix=fix)
        except Exception as e:
            errors.append(f"Economics Validation: {e}")

    return errors


def _validate_pitch_deck_file(workspace_dir: Path, fix: bool) -> List[str]:
    handoff_dir = workspace_dir / "discovery" / "handoff"
    pd_file = handoff_dir / "pitch_deck.html"
    if pd_file.exists():
        try:
            run_validate_pitch_deck(pd_file, fix=fix)
        except Exception as e:
            return [f"pitch_deck.html: {e}"]
        return []

    pd_yaml = handoff_dir / "pitch_deck.yaml"
    if pd_yaml.exists():
        try:
            run_validate_pitch_deck(pd_yaml, fix=fix)
        except Exception as e:
            return [f"pitch_deck.yaml: {e}"]

    return []


def _validate_launch_roadmap(strategy_dir: Path) -> List[str]:
    lr_file = strategy_dir / "launch_roadmap.yaml"
    if not lr_file.exists():
        return []
    try:
        run_validate_launch_roadmap(lr_file)
        return []
    except Exception as e:
        return ["launch_roadmap.yaml:\n" + str(e)]


def _validate_strategy_files(
    workspace_dir: Path, discovery_dir: Path, fix: bool
) -> List[str]:
    strategy_dir = discovery_dir / "strategy"
    strategy_errors = []

    try:
        run_validate_strategy(workspace_dir)
    except Exception as e:
        strategy_errors.extend(str(e).split("\n\n---\n\n"))

    strategy_errors.extend(_validate_tech_market_brief(strategy_dir))
    strategy_errors.extend(_validate_tech_synthesis(strategy_dir, fix))
    strategy_errors.extend(_validate_revenue_and_economics(strategy_dir, fix))
    strategy_errors.extend(_validate_pitch_deck_file(workspace_dir, fix))
    strategy_errors.extend(_validate_launch_roadmap(strategy_dir))

    return strategy_errors


def _validate_global_files(
    workspace_dir: Path, fix: bool
) -> Tuple[List[str], List[str]]:
    markdown_errors = []
    estimation_errors = []
    for root, _, files in os.walk(workspace_dir):
        # Skip hidden dirs or build dirs if needed, but keeping simple for now
        if ".git" in root or "__pycache__" in root:
            continue
        for file in files:
            file_path = Path(root) / file
            if file.endswith(".md"):
                try:
                    res = run_validate_markdown_links(
                        ValidateMarkdownLinksInput(file_path=str(file_path)), fix=fix
                    )
                    if not res.is_valid:
                        markdown_errors.extend(
                            [f"{file_path.name}: {err}" for err in res.errors]
                        )
                except Exception as e:
                    markdown_errors.append(f"{file_path.name}: {e}")
            elif file == "estimation.yaml":
                try:
                    est_res = run_validate_estimation(file_path, fix=fix)
                    if not est_res.is_valid:
                        estimation_errors.extend(
                            [
                                f"{file_path.parent.name}/{file_path.name}: {err}"
                                for err in est_res.errors
                            ]
                        )
                except Exception as e:
                    estimation_errors.append(
                        f"{file_path.parent.name}/{file_path.name}: {e}"
                    )
    return markdown_errors, estimation_errors


def _validate_domains(domains_dir: Path, fix: bool) -> List[DomainResult]:
    domain_results: List[DomainResult] = []
    if not domains_dir.is_dir():
        return domain_results
    for domain_dir in sorted(d for d in domains_dir.iterdir() if d.is_dir()):
        try:
            run_validate_domain(domain_dir, fix=fix)
            domain_results.append(DomainResult(name=domain_dir.name, passed=True))
        except Exception as e:
            domain_results.append(
                DomainResult(name=domain_dir.name, passed=False, errors=[str(e)])
            )
    return domain_results


def _validate_business_observability(
    discovery_dir: Path, fix: bool
) -> Tuple[bool, List[str]]:
    obs_file = discovery_dir / "strategy" / "business_observability.yaml"
    if not obs_file.exists():
        return fix, [] if fix else ["business_observability.yaml not found"]
    try:
        run_validate_business_observability(obs_file)
        return True, []
    except Exception as e:
        return False, [str(e)]


def _validate_entity_graph(domains_dir: Path) -> List[str]:
    if not domains_dir.is_dir():
        return []
    try:
        run_validate_entity_graph(ValidateEntityGraphInput(domains_dir=domains_dir))
        return []
    except SystemExit:
        return [
            "AST Graph compilation blocked (Service Coupling > 0.3 or Latency Risk)."
        ]
    except Exception as e:
        return [f"validate_entity_graph failed: {e}"]


def _validate_global_errata(discovery_dir: Path, fix: bool) -> List[str]:
    errors: List[str] = []
    global_errata_dir = discovery_dir / "handoff" / "errata"
    if not (global_errata_dir.exists() and global_errata_dir.is_dir()):
        return errors
    for err_file in sorted(global_errata_dir.glob("*.yaml")):
        try:
            res = run_validate_errata(err_file, fix=fix)
            if not res.is_valid:
                errors.extend([f"{err_file.name}: {err}" for err in res.errors])
        except Exception as e:
            errors.append(f"{err_file.name}: {e}")
    return errors


def run_validate_workspace(
    workspace_dir: Path, fix: bool = True
) -> WorkspaceValidationResult:
    discovery_dir = workspace_dir / "discovery"
    domains_dir = discovery_dir / "domains"

    strategy_errors = _validate_strategy_files(workspace_dir, discovery_dir, fix)
    domain_results = _validate_domains(domains_dir, fix)
    obs_passed, obs_errors = _validate_business_observability(discovery_dir, fix)

    domain_index = build_domain_index(domains_dir)
    cross_issues = check_cross_domain_refs(domains_dir, domain_index)

    platform_errors = check_platforms(workspace_dir, domains_dir)
    if platform_errors:
        strategy_errors.extend(platform_errors)

    strategy_passed = len(strategy_errors) == 0

    graph_errors = _validate_entity_graph(domains_dir)
    markdown_errors, estimation_errors = _validate_global_files(workspace_dir, fix)
    global_errata_errors = _validate_global_errata(discovery_dir, fix)

    return WorkspaceValidationResult(
        strategy_passed=strategy_passed,
        strategy_errors=strategy_errors,
        domains=domain_results,
        observability_passed=obs_passed,
        observability_errors=obs_errors,
        cross_domain_issues=cross_issues,
        graph_passed=len(graph_errors) == 0,
        graph_errors=graph_errors,
        markdown_passed=len(markdown_errors) == 0,
        markdown_errors=markdown_errors,
        global_errata_passed=len(global_errata_errors) == 0,
        global_errata_errors=global_errata_errors,
        estimation_passed=len(estimation_errors) == 0,
        estimation_errors=estimation_errors,
    )
