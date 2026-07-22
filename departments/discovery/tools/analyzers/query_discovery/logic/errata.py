import yaml
from pathlib import Path
from typing import Optional, Dict, Any

from departments.discovery.tools.shared.file_utils import load_yaml


def _iter_epic_errata_files(domain_dir: Path):
    # Epic-level errata sits inside its epic folder as errata.yaml.
    # Producer: ux-flow-architect-sub.
    # The two need genuinely different basenames (not just different directories)
    # because the glob matcher (fnmatch) doesn't treat `/` as a segment boundary
    # — "domains/*/errata.yaml" would still match a deeper
    # ".../epics/{epic}/errata.yaml" path, wrongly conflating po-strategist-sub's
    # and ux-flow-architect-sub's errata as the same producer.
    epics_dir = domain_dir / "epics"
    if not epics_dir.is_dir():
        return
    for epic_dir in sorted(epics_dir.iterdir()):
        f = epic_dir / "errata.yaml"
        if f.is_file():
            yield domain_dir.name, epic_dir.name, f


def _iter_errata_files_scoped(workspace_dir: Path, scope: str = "domain"):
    """Yield (domain_name, source_key, file_path) for errata files.

    scope:
      'domain'  — only domain_errata.yaml  (producer: po-strategist-sub)
      'epic'    — only epics/*/errata.yaml  (producer: ux-flow-architect-sub)
      'global'  — both levels              (for aggregation phase only)
    """
    if scope == "global":
        critical_errata = (
            workspace_dir / "discovery" / "errata" / "critical_errata.yaml"
        )
        if critical_errata.is_file():
            yield "global", "critical_errata", critical_errata

    domains_dir = workspace_dir / "discovery" / "domains"
    if not domains_dir.is_dir():
        return
    for domain_dir in sorted(domains_dir.iterdir()):
        if not domain_dir.is_dir():
            continue

        if scope in ("domain", "global"):
            # Domain-level errata (fixed categories not tied to an epic, e.g. domain
            # strategy conflicts) sits directly under the domain as domain_errata.yaml.
            # Producer: po-strategist-sub.
            domain_errata = domain_dir / "domain_errata.yaml"
            if domain_errata.is_file():
                yield domain_dir.name, "domain_strategy", domain_errata

        if scope in ("epic", "global"):
            yield from _iter_epic_errata_files(domain_dir)


# Backward-compatible alias used internally (e.g. by patches.get_patch_errata).
_iter_errata_files = _iter_errata_files_scoped


def get_errata(
    workspace_dir: Path, status: str = "open", scope: str = "domain"
) -> dict:
    """Return errata grouped by domain → source, filtered by status.

    scope:
      'domain'  — errata-domain subcommand (po-strategist zone)
      'epic'    — errata-epic subcommand   (ux-flow-architect zone)
      'global'  — errata-global subcommand (aggregation only)
    """
    res: Dict[str, Any] = {}
    for domain, source, f in _iter_errata_files_scoped(workspace_dir, scope):
        items = load_yaml(f)
        if not isinstance(items, list):
            continue
        matched = [
            item for item in items if status == "all" or item.get("status") == status
        ]
        if matched:
            res.setdefault(domain, {})[source] = matched
    return res


def _get_errata_candidates(domain_dir: Path, source: Optional[str]) -> list:
    epics_dir = domain_dir / "epics"
    domain_errata = domain_dir / "domain_errata.yaml"

    if source == "domain_strategy":
        return [domain_errata]
    if source:
        return [epics_dir / source / "errata.yaml"]

    return ([domain_errata] if domain_errata.is_file() else []) + (
        sorted(epics_dir.glob("*/errata.yaml")) if epics_dir.is_dir() else []
    )


def _resolve_item_in_file(f: Path, errata_id: str, resolution: str) -> Optional[list]:
    if not f.exists():
        return None
    items = load_yaml(f)
    if not isinstance(items, list):
        return None

    for item in items:
        if item.get("id") == errata_id:
            if item.get("status") == "resolved":
                return []
            item["status"] = "resolved"
            item["resolution"] = resolution
            new_content = yaml.dump(items, allow_unicode=True, sort_keys=False)
            return [(f, new_content)]
    return None


def resolve_errata(
    workspace_dir: Path,
    domain: str,
    errata_id: str,
    resolution: str,
    source: Optional[str] = None,
) -> list:
    domain_dir = workspace_dir / "discovery" / "domains" / domain
    candidates = _get_errata_candidates(domain_dir, source)

    if not candidates:
        raise FileNotFoundError(f"No errata files for domain {domain}")

    for f in candidates:
        result = _resolve_item_in_file(f, errata_id, resolution)
        if result is not None:
            return result

    if source:
        raise ValueError(f"Errata ID {errata_id} not found in {candidates[0]}")
    raise ValueError(
        f"Errata ID {errata_id} not found in any errata file for domain {domain}"
    )
