from pydantic import BaseModel, Field
from typing import List
from pathlib import Path
import yaml


class ValidateDomainExportsInput(BaseModel):
    domains_dir: Path = Field(..., description="Path to workspace/discovery/domains")


class UnresolvedImport(BaseModel):
    domain: str
    from_domain: str
    entity: str
    reason: str = ""
    # Hint so the fixer (orchestrator or, on retry, the sub-agent) can pick a real
    # entity instead of guessing/inventing one that merely sounds plausible.
    from_domain_known: bool = True
    available_exports: List[str] = []
    known_domains: List[str] = []


class ValidateDomainExportsOutput(BaseModel):
    is_valid: bool
    unresolved_imports: List[UnresolvedImport]


def _load_summaries(domains_dir: Path) -> dict[str, dict]:
    summaries: dict[str, dict] = {}
    if not domains_dir.is_dir():
        return summaries
    for domain_dir in domains_dir.iterdir():
        if not domain_dir.is_dir():
            continue
        summary_file = domain_dir / "summary.yaml"
        if not summary_file.exists():
            continue
        try:
            data = yaml.safe_load(summary_file.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        domain_name = data.get("domain") or domain_dir.name
        summaries[domain_name] = data
    return summaries


def run_validate_domain_exports(
    input_data: ValidateDomainExportsInput,
) -> ValidateDomainExportsOutput:
    if not input_data.domains_dir.is_dir():
        raise FileNotFoundError(
            f"Domains directory not found: {input_data.domains_dir}"
        )

    summaries = _load_summaries(input_data.domains_dir)

    # Sub-agents run in parallel, isolated to their own domain (they never see
    # other domains' summary.yaml), so a claimed `imports.from_domain/entity`
    # is never cross-checked against what that domain actually `exports`.
    # Runs directly against the domain summaries — there is no aggregated
    # index to check against, so this is the earliest point to catch it.
    exports_by_domain: dict[str, set[str]] = {
        domain: {
            str(exp.get("entity"))
            for exp in (data.get("exports") or [])
            if isinstance(exp, dict) and str(exp.get("entity"))
        }
        for domain, data in summaries.items()
    }

    unresolved: list[UnresolvedImport] = []
    for domain, data in summaries.items():
        for imp in data.get("imports") or []:
            if not isinstance(imp, dict):
                continue
            from_domain = imp.get("from_domain")
            entity = imp.get("entity")
            if not from_domain or not entity:
                continue
            exported = exports_by_domain.get(from_domain)
            if exported is None or entity not in exported:
                domain_known = exported is not None
                unresolved.append(
                    UnresolvedImport(
                        domain=domain,
                        from_domain=from_domain,
                        entity=entity,
                        reason=imp.get("reason", ""),
                        from_domain_known=domain_known,
                        available_exports=sorted(exported) if exported else [],
                        known_domains=(
                            [] if domain_known else sorted(exports_by_domain.keys())
                        ),
                    )
                )

    return ValidateDomainExportsOutput(
        is_valid=len(unresolved) == 0,
        unresolved_imports=unresolved,
    )
