from pathlib import Path
from typing import Iterator, Optional, Tuple

from departments.discovery.tools.shared.file_utils import load_yaml_safe


def iter_domain_dirs(domains_dir: Path, domain: Optional[str] = None) -> Iterator[Path]:
    """Yields each domain's directory under domains_dir, skipping non-directories.

    If `domain` is given, yields at most that one directory (still checking
    it's actually a directory) — every caller that supports an optional
    single-domain filter re-implements this same `iterdir` + `is_dir` +
    name-match loop.
    """
    if not domains_dir.is_dir():
        return
    for domain_dir in sorted(domains_dir.iterdir()):
        if not domain_dir.is_dir():
            continue
        if domain and domain_dir.name != domain:
            continue
        yield domain_dir


def iter_epic_dirs(domain_dir: Path) -> Iterator[Path]:
    """Yields each epic's directory under domain_dir/epics, skipping non-directories."""
    epics_dir = domain_dir / "epics"
    if not epics_dir.is_dir():
        return
    for epic_dir in sorted(epics_dir.iterdir()):
        if epic_dir.is_dir():
            yield epic_dir


def iter_epic_feature_files(domain_dir: Path) -> Iterator[Tuple[Path, dict]]:
    """Yields (features_file, data) for every epics/*/features.yaml under a domain,
    skipping epics that have none. `data` is {} if the file is empty/unparseable
    (features.yaml lives per-epic, not once per domain — every tool that needs a
    domain-wide feature view has to walk this same glob)."""
    epics_dir = domain_dir / "epics"
    if not epics_dir.exists():
        return
    for features_file in sorted(epics_dir.glob("*/features.yaml")):
        yield features_file, load_yaml_safe(features_file, default={})
