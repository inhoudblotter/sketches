import re
from pathlib import Path
from typing import Optional, Dict, Any
from typing import Set

from departments.discovery.tools.shared.file_utils import load_yaml, domains_dir_or_warn

_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")
_WORD_RE = re.compile(r"[A-ZА-ЯЁ][a-zа-яё]*|[a-zа-яё]+")


def _is_cyrillic(name: str) -> bool:
    return bool(_CYRILLIC_RE.search(name))


def _split_words(name: str) -> list:
    """Split a PascalCase/camelCase identifier into its constituent words."""
    words = _WORD_RE.findall(name)
    return words or [name]


def _stem(word: str, min_len: int = 3, strip: int = 2) -> str:
    """Trim trailing characters to absorb common Russian noun-case endings
    (e.g. Полигон -> полигон/полигона/полигонов, Роль -> роли/ролей)."""
    if len(word) <= min_len:
        return word
    cut = max(min_len, len(word) - strip)
    return word[:cut]


def _entity_referenced(entity: str, story_text: str, story_text_lower: str) -> bool:
    """Check whether an entity is referenced in the story text.

    Latin-script identifiers keep the original exact substring match, which
    already works correctly.

    Cyrillic identifiers are often compound PascalCase names
    (e.g. "РольДоступа") that are never literally referenced as one token in
    Russian prose — instead, each concept is discussed as a separate,
    inflected word ("роль", "ролей", "доступа"...). A literal exact-substring
    match therefore produces systematic false positives. To fix this we split
    the identifier into its constituent words and, for each word, do a
    case-insensitive substring match against a stem (the word with its last
    couple of characters trimmed, to absorb Russian case endings). The
    entity is considered referenced only if *all* of its constituent words
    are found — this keeps the check meaningful and still able to catch
    genuinely unused entities.
    """
    if not _is_cyrillic(entity):
        return entity in story_text

    words = _split_words(entity)
    stems = [_stem(w).lower() for w in words]
    return all(stem in story_text_lower for stem in stems)


def _get_domain_entities(domain_dir: Path) -> list:
    dict_file = domain_dir / "manifest.yaml"
    if not dict_file.exists():
        return []
    d_data = load_yaml(dict_file)
    return [
        e.get("name")
        for e in d_data.get("entities", [])
        if isinstance(e, dict) and e.get("name")
    ]


def _get_story_text(domain_dir: Path) -> str:
    story_text = ""
    epics_dir = domain_dir / "epics"
    if epics_dir.exists():
        for epic_dir in epics_dir.iterdir():
            if not epic_dir.is_dir():
                continue
            s_file = epic_dir / "stories.yaml"
            if s_file.exists():
                with open(s_file, "r", encoding="utf-8") as sf:
                    story_text += sf.read()
    return story_text


def get_orphans(workspace_dir: Path, domain: Optional[str] = None) -> dict:
    res: Dict[str, Any] = {}
    domains_dir = domains_dir_or_warn(workspace_dir)

    if domains_dir is None:
        return res

    for domain_dir in domains_dir.iterdir():
        if not domain_dir.is_dir():
            continue
        if domain and domain_dir.name != domain:
            continue

        entities = _get_domain_entities(domain_dir)
        if not entities:
            continue

        story_text = _get_story_text(domain_dir)
        story_text_lower = story_text.lower()

        orphans: list = []
        for ent in entities:
            if not _entity_referenced(str(ent), story_text, story_text_lower):
                orphans.append(ent)

        if orphans:
            res[domain_dir.name] = orphans

    return res


MANDATORY_EPIC_TYPES = {
    "growth": "growth epic (sharing/onboarding/retention)",
    "monitoring": "monitoring/observability epic",
    "promo": "promo epic (landing/pricing/404)",
}


def get_coverage(workspace_dir: Path) -> dict:
    res: Dict[str, Any] = {"missing_mandatory_epics": {}}
    domains_dir = domains_dir_or_warn(workspace_dir)

    if domains_dir is None:
        return res

    # Reads the machine-readable `epic_type` field each stories.yaml is required to declare
    # (see job_stories_template.yaml) instead of guessing from the epic directory name — agents
    # are free to name directories however they like (e.g. "billing-admin" for a monitoring epic).
    for domain_dir in domains_dir.iterdir():
        if not domain_dir.is_dir():
            continue

        epics_dir = domain_dir / "epics"
        epic_types: Set[str] = set()
        if epics_dir.exists():
            for epic_dir in epics_dir.iterdir():
                if not epic_dir.is_dir():
                    continue
                s_file = epic_dir / "stories.yaml"
                if not s_file.exists():
                    continue
                s_data = load_yaml(s_file)
                epic_type = s_data.get("epic_type")
                if epic_type:
                    epic_types.add(epic_type)

        missing = [
            label
            for required, label in MANDATORY_EPIC_TYPES.items()
            if required not in epic_types
        ]

        if missing:
            res["missing_mandatory_epics"][domain_dir.name] = missing

    return res
