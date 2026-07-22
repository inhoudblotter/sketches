from dataclasses import dataclass, field
from typing import List


@dataclass
class DomainResult:
    name: str
    passed: bool
    errors: List[str] = field(default_factory=list)


@dataclass
class CrossDomainIssue:
    consumer_domain: str
    from_domain: str
    entity: str
    problem: (
        str  # "domain_not_found" | "entity_not_exported" | "entity_not_in_dictionary"
    )


def _icon(ok: bool) -> str:
    return "✓" if ok else "✗"


def _section_lines(
    passed: bool, label: str, errors: List[str], limit: int | None = None
) -> List[str]:
    lines = [f"  {_icon(passed)} {label}"]
    shown = errors[:limit] if limit else errors
    for e in shown:
        lines.append(f"      └─ {e}")
    if limit and len(errors) > limit:
        lines.append(f"      └─ ... and {len(errors) - limit} more")
    return lines


def _issue_message(issue: CrossDomainIssue) -> str:
    if issue.problem == "domain_not_found":
        return f"домен '{issue.from_domain}' не найден в workspace"
    if issue.problem == "entity_not_in_dictionary":
        return f"сущность не найдена в dictionary.yaml домена '{issue.from_domain}'"
    if issue.problem == "entity_not_exported":
        return f"сущность найдена в dictionary.yaml, но не объявлена в exports[] summary.yaml домена '{issue.from_domain}'"
    return issue.problem


@dataclass
class WorkspaceValidationResult:
    strategy_passed: bool
    strategy_errors: List[str]
    domains: List[DomainResult]
    observability_passed: bool
    observability_errors: List[str]
    cross_domain_issues: List[CrossDomainIssue] = field(default_factory=list)
    graph_passed: bool = True
    graph_errors: List[str] = field(default_factory=list)
    markdown_passed: bool = True
    markdown_errors: List[str] = field(default_factory=list)
    global_errata_passed: bool = True
    global_errata_errors: List[str] = field(default_factory=list)
    estimation_passed: bool = True
    estimation_errors: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return (
            self.strategy_passed
            and all(d.passed for d in self.domains)
            and self.observability_passed
            and not self.cross_domain_issues
            and self.graph_passed
            and self.global_errata_passed
            and self.estimation_passed
        )

    def summary(self) -> str:
        MAX_MD_ERRORS = 5
        cross_ok = not self.cross_domain_issues
        cross_domain_lines = [f"  {_icon(cross_ok)} cross-domain references"] + [
            f"      └─ [{issue.consumer_domain}] imports {issue.from_domain}.{issue.entity}: {_issue_message(issue)}"
            for issue in self.cross_domain_issues
        ]

        lines = [f"\n{'─' * 56}"]
        lines += _section_lines(
            self.strategy_passed,
            "strategy  (target_audience, platform_strategy, domains_manifest)",
            self.strategy_errors,
        )
        for d in self.domains:
            lines += _section_lines(d.passed, f"domain:{d.name}", d.errors)
        lines += _section_lines(
            self.observability_passed,
            "business_observability",
            self.observability_errors,
        )
        lines += cross_domain_lines
        lines += _section_lines(
            self.graph_passed, "ast_graph_coupling", self.graph_errors
        )
        lines += _section_lines(
            self.markdown_passed, "markdown_links", self.markdown_errors, MAX_MD_ERRORS
        )
        lines += _section_lines(
            self.global_errata_passed, "global_errata", self.global_errata_errors
        )
        lines += _section_lines(
            self.estimation_passed, "estimation", self.estimation_errors
        )

        lines.append(f"{'─' * 56}")
        total = 7 + len(self.domains)
        passed_count = (
            int(self.strategy_passed)
            + sum(int(d.passed) for d in self.domains)
            + int(self.observability_passed)
            + int(cross_ok)
            + int(self.graph_passed)
            + int(self.markdown_passed)
            + int(self.global_errata_passed)
            + int(self.estimation_passed)
        )
        status = "PASSED" if self.passed else "FAILED"
        lines.append(f"  {status}: {passed_count}/{total} checks passed")
        lines.append(f"{'─' * 56}\n")
        return "\n".join(lines)
