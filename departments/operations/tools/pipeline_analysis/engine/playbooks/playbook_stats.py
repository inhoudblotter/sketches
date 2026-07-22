"""Playbook subscriber/reference stats, split out of logic.run()."""

from __future__ import annotations
from collections import defaultdict
from pathlib import Path

from ..playbooks import playbook_analyzer
from ..core.utils import _skill_size_kb
from ...schemas import PlaybookStat


def build_playbook_stats(
    raw_agents: list[dict], project_root: Path
) -> tuple[dict[str, set[str]], list[PlaybookStat]]:
    playbook_dict: dict[str, set[str]] = defaultdict(set)
    for a in raw_agents:
        for p in a["required_skills"]:
            playbook_dict[p].add(a["name"])
        # transitively-loaded playbooks (referenced by an explicitly-required
        # one) still consume context for this agent — surface them as
        # subscribers too, not just the playbooks the agent's frontmatter lists.
        for p in a.get("transitive_skills", []):
            playbook_dict[p].add(a["name"])

    references_by_playbook = {
        pb: playbook_analyzer.parse_references(pb, project_root) for pb in playbook_dict
    }
    referenced_by_map: dict[str, set[str]] = defaultdict(set)
    for pb, refs in references_by_playbook.items():
        for ref in refs:
            referenced_by_map[ref].add(pb)

    playbook_stats = []
    for pb, subs in playbook_dict.items():
        playbook_stats.append(
            PlaybookStat(
                name=pb,
                subscribers=sorted(subs),
                size_kb=_skill_size_kb(pb, project_root),
                references=sorted(references_by_playbook.get(pb, [])),
                referenced_by=sorted(referenced_by_map.get(pb, [])),
            )
        )
    playbook_stats.sort(key=lambda x: (-len(x.subscribers), x.name))

    return playbook_dict, playbook_stats
