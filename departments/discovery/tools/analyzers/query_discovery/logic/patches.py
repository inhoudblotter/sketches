from pathlib import Path
from typing import Optional, Dict, Any

from departments.discovery.tools.shared.file_utils import load_yaml


def _iter_patch_files(workspace_dir: Path, domain: Optional[str] = None):
    """Yield (domain_name, patch_filename, patch_data) for all patch files."""
    domains_dir = workspace_dir / "discovery" / "domains"
    if domains_dir.is_dir():
        for domain_dir in sorted(domains_dir.iterdir()):
            if not domain_dir.is_dir():
                continue
            if domain and domain_dir.name != domain:
                continue
            patches_dir = domain_dir / "patches"
            if not patches_dir.is_dir():
                continue
            for patch_file in sorted(patches_dir.glob("*.yaml")):
                data = load_yaml(patch_file)
                yield domain_dir.name, patch_file.name, data

    if domain and domain != "strategy":
        return
    strategy_patches_dir = workspace_dir / "discovery" / "strategy" / "patches"
    if strategy_patches_dir.is_dir():
        for patch_file in sorted(strategy_patches_dir.glob("*.yaml")):
            data = load_yaml(patch_file)
            yield "strategy", patch_file.name, data


def get_patches(
    workspace_dir: Path, domain: Optional[str] = None, status: str = "pending"
) -> dict:
    """Return patches grouped by domain, filtered by status.

    status: 'pending' | 'applied' | 'failed' | 'all'
    """
    res: Dict[str, Any] = {}
    for domain_name, filename, data in _iter_patch_files(workspace_dir, domain):
        patch_status = data.get("status", "pending")
        if status not in ("all", patch_status):
            continue
        entry = {
            "file": filename,
            "gap_type": data.get("gap_type"),
            "authored_by": data.get("authored_by"),
            "target_agent": data.get("target_agent"),
            "created_at": data.get("created_at"),
            "status": patch_status,
            "detail": data.get("detail"),
            "errata_ref": data.get("errata_ref"),
            "result_note": data.get("result_note"),
        }
        res.setdefault(domain_name, []).append(entry)
    return res


def get_patch_errata(workspace_dir: Path, patch_filename: str) -> dict:
    """Return all errata records (domain + epic level) linked to a given patch file.

    Matches records where errata_ref == patch_filename.
    """
    from .errata import _iter_errata_files_scoped

    res: Dict[str, Any] = {}
    for domain, source, f in _iter_errata_files_scoped(workspace_dir, scope="global"):
        items = load_yaml(f)
        if not isinstance(items, list):
            continue
        # Errata entries link forward to a patch via `patch_ref` (patch filename;
        # see errata_template.yaml). There is no `errata_ref` field on errata
        # entries — that name is only used on the patch side, pointing back to
        # an errata *id* (see patch_template.yaml), which is a different value
        # entirely and cannot be compared against a patch filename.
        linked = [item for item in items if item.get("patch_ref") == patch_filename]
        if linked:
            res.setdefault(domain, {})[source] = linked
    return res
