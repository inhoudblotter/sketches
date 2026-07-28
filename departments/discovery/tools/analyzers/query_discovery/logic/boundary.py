import sys
from pathlib import Path
from typing import Dict

from departments.discovery.tools.shared.file_utils import load_yaml


def check_boundaries(domains_dir: Path) -> dict:
    if not domains_dir.exists():
        print(
            f"warning: {domains_dir} does not exist "
            f"(pass --domain the discovery/domains path of a valid workspace)",
            file=sys.stderr,
        )
        return {}
    entities: Dict[str, list] = {}
    duplicates = {}
    for domain_dir in domains_dir.iterdir():
        if not domain_dir.is_dir():
            continue
        dict_file = domain_dir / "manifest.yaml"
        if dict_file.exists():
            data = load_yaml(dict_file)
            for ent in data.get("entities", []):
                name = ent.get("name")
                if name:
                    entities.setdefault(name, []).append(domain_dir.name)
    for name, domains in entities.items():
        if len(domains) > 1:
            duplicates[name] = domains
    return duplicates
