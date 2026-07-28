from pathlib import Path
from .core import load_domain_snapshot
from departments.discovery.tools.shared.file_utils import domains_dir_or_warn
from typing import Optional, Dict, Any, List


def get_exports(workspace_dir: Path, entity: str) -> dict:
    idx = load_domain_snapshot(workspace_dir)
    res: Dict[str, Any] = {}
    for d_name, d_data in idx.get("domains", {}).items():
        exports = d_data.get("exports", [])
        for exp in exports:
            if exp.get("entity", "").lower() == entity.lower():
                res[d_name] = exp
    return res


_SCOPE_FILES = {
    "dictionary": ["manifest.yaml"],
    "stories": [],
    "features": [],
    "glossary": ["summary.yaml"],
}


def _scoped_files_to_check(domain_dir: Path, scope: str) -> list:
    files_to_check = []
    if scope in ("all", "dictionary"):
        files_to_check.append(domain_dir / "manifest.yaml")
    if scope in ("all", "glossary"):
        files_to_check.append(domain_dir / "summary.yaml")
    if scope in ("all", "stories", "features"):
        epics_dir = domain_dir / "epics"
        if epics_dir.exists():
            for epic_dir in epics_dir.iterdir():
                if not epic_dir.is_dir():
                    continue
                if scope in ("all", "stories"):
                    files_to_check.append(epic_dir / "stories.yaml")
                if scope in ("all", "features"):
                    files_to_check.append(epic_dir / "features.yaml")
    return files_to_check


def _search_file(f: Path, q: str, workspace_dir: Path) -> list:
    if not f.exists():
        return []
    with open(f, "r", encoding="utf-8") as file:
        lines = file.readlines()
    return [
        {
            "file": str(f.relative_to(workspace_dir)),
            "line_number": i + 1,
            "content": line.strip(),
        }
        for i, line in enumerate(lines)
        if q in line.lower()
    ]


def search_index(workspace_dir: Path, query: str, scope: str) -> dict:
    res: Dict[str, Any] = {}
    domains_dir = domains_dir_or_warn(workspace_dir)
    if domains_dir is None:
        return res

    q = query.lower()
    for domain_dir in domains_dir.iterdir():
        if not domain_dir.is_dir():
            continue

        matches = []
        for f in _scoped_files_to_check(domain_dir, scope):
            matches.extend(_search_file(f, q, workspace_dir))

        if matches:
            res[domain_dir.name] = matches

    return res


def get_dependencies(workspace_dir: Path, domain: Optional[str] = None) -> dict:
    idx = load_domain_snapshot(workspace_dir)
    res: Dict[str, Any] = {}

    for d_name, d_data in idx.get("domains", {}).items():
        if domain and d_name != domain:
            continue

        depends_on: Dict[str, List[Any]] = {}
        for imp in d_data.get("imports", []):
            f_domain = imp.get("from_domain", "unknown")
            depends_on.setdefault(f_domain, []).append(imp.get("entity"))

        used_by: Dict[str, List[Any]] = {}
        my_exports = [e.get("entity", "").lower() for e in d_data.get("exports", [])]

        for other_name, other_data in idx.get("domains", {}).items():
            if other_name == d_name:
                continue
            for imp in other_data.get("imports", []):
                if (
                    imp.get("from_domain") == d_name
                    or imp.get("entity", "").lower() in my_exports
                ):
                    used_by.setdefault(other_name, []).append(imp.get("entity"))

        res[d_name] = {"depends_on": depends_on, "used_by": used_by}

    return res


def get_trajectory(workspace_dir: Path, domain: Optional[str] = None) -> dict:
    idx = load_domain_snapshot(workspace_dir)
    res: Dict[str, Any] = {}
    for d_name, d_data in idx.get("domains", {}).items():
        if domain and d_name != domain:
            continue
        traj = d_data.get("strategic_trajectory", "")
        if traj:
            res[d_name] = traj
    return res


def _process_epic_requirements(
    e: dict, platforms: set, events: set, constraints: set, flags: dict
):
    epic_reqs = e.get("requirements", {})
    if epic_reqs:
        platforms.update(epic_reqs.get("platforms", []))
        events.update(epic_reqs.get("events_to_handle", []))
        constraints.update(epic_reqs.get("business_constraints", []))
        if epic_reqs.get("is_headless", False):
            flags["headless"] = True
        if epic_reqs.get("offline_first", False):
            flags["offline"] = True


def _collect_domain_requirements(
    d_data: dict, epic_type: Optional[str]
) -> tuple[set, set, set, dict]:
    platforms: set = set()
    events: set = set()
    constraints: set = set()
    flags = {"headless": False, "offline": False}

    for e in d_data.get("epics", []):
        if epic_type and e.get("epic_type", "core").lower() != epic_type.lower():
            continue
        _process_epic_requirements(e, platforms, events, constraints, flags)

    return platforms, events, constraints, flags


def _shape_requirements(
    platforms: set, events: set, constraints: set, flags: dict, section: Optional[str]
) -> dict:
    res = {
        "platforms": sorted(platforms),
        "is_headless_required": flags["headless"],
        "offline_first_required": flags["offline"],
        "events_to_handle": sorted(events),
        "business_constraints": sorted(constraints),
    }
    if section:
        return {section: res[section]} if section in res else {}
    return res


def get_epic_requirements(
    workspace_dir: Path,
    domain: Optional[str] = None,
    is_global: bool = False,
    section: Optional[str] = None,
    epic_type: Optional[str] = None,
) -> dict:
    idx = load_domain_snapshot(workspace_dir)
    res: Dict[str, Any] = {}
    g_platforms: set = set()
    g_events: set = set()
    g_constraints: set = set()
    g_flags = {"headless": False, "offline": False}

    for d_name, d_data in idx.get("domains", {}).items():
        if not is_global and domain and d_name != domain:
            continue

        platforms, events, constraints, flags = _collect_domain_requirements(
            d_data, epic_type
        )

        if is_global:
            g_platforms.update(platforms)
            g_events.update(events)
            g_constraints.update(constraints)
            g_flags["headless"] = g_flags["headless"] or flags["headless"]
            g_flags["offline"] = g_flags["offline"] or flags["offline"]
        elif (
            platforms or events or constraints or flags["headless"] or flags["offline"]
        ):
            d_res = _shape_requirements(platforms, events, constraints, flags, section)
            if d_res:
                res[d_name] = d_res

    if is_global:
        g_res = _shape_requirements(
            g_platforms, g_events, g_constraints, g_flags, section
        )
        return {"global_requirements": g_res} if g_res else {}
    return res
