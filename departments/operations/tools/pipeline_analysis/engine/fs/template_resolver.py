"""Resolve {variable} templates in paths and delegations."""

from __future__ import annotations
import re
import itertools
from pathlib import Path
import networkx as nx


def _template_to_regex(template_str: str) -> tuple[re.Pattern, list[str]]:
    escaped = re.escape(template_str)
    # Extract variable names
    var_names = re.findall(r"\\\{([^}]+)\\\}", escaped)
    # Replace \{var_name\} with (?P<var_name>.*)
    pattern = re.sub(r"\\\{([^}]+)\\\}", r"(?P<\1>.*)", escaped)
    return re.compile("^" + pattern + "$"), var_names


def _resolve_template_writes(
    agent, name, concrete_reads, G, workspace_dir, artifact_attrs_fn, add_bindings
):
    for w in agent["writes"]:
        if "{" in w:
            regex, _ = _template_to_regex(w)
            for cr in concrete_reads:
                match = regex.match(cr)
                if match:
                    add_bindings(name, match.groupdict())
                    if cr not in G:
                        G.add_node(cr, **artifact_attrs_fn(cr, workspace_dir))
                    G.add_edge(w, cr, edge_type="template_match")


def _resolve_template_reads(
    agent, name, concrete_writes, G, workspace_dir, artifact_attrs_fn, add_bindings
):
    for r in agent["reads"]:
        if "{" in r:
            regex, _ = _template_to_regex(r)
            for cw in concrete_writes:
                match = regex.match(cw)
                if match:
                    add_bindings(name, match.groupdict())
                    if cw not in G:
                        G.add_node(cw, **artifact_attrs_fn(cw, workspace_dir))
                    G.add_edge(cw, r, edge_type="template_match")


def _resolve_delegations(agent, name, agents, G, bindings):
    for target in agent.get("delegates_to", []):
        if "{" in target:
            vars_in_target = re.findall(r"\{([^}]+)\}", target)
            val_lists = []
            can_resolve = True
            for v in vars_in_target:
                if v in bindings[name] and bindings[name][v]:
                    val_lists.append(list(bindings[name][v]))
                else:
                    can_resolve = False
                    break

            if can_resolve:
                for combo in itertools.product(*val_lists):
                    var_dict = dict(zip(vars_in_target, combo, strict=False))
                    resolved_target = target.format(**var_dict)

                    # Find if resolved_target is an actual subagent
                    for other_agent in agents:
                        if other_agent["name"] == resolved_target and other_agent.get(
                            "is_subagent"
                        ):
                            if resolved_target not in G:
                                G.add_node(
                                    resolved_target,
                                    node_type="agent",
                                    model="unknown",
                                    temperature=0.5,
                                    context_load_kb=0.0,
                                )
                            G.add_edge(name, resolved_target, edge_type="delegates")
                            break


def resolve_templates(
    G: nx.DiGraph, agents: list[dict], workspace_dir: Path, artifact_attrs_fn
) -> None:
    concrete_reads: set[str] = set()
    concrete_writes: set[str] = set()
    for agent in agents:
        concrete_reads.update(r for r in agent["reads"] if "{" not in r)
        concrete_writes.update(w for w in agent["writes"] if "{" not in w)

    # Store extracted variable bindings per agent
    # e.g. bindings["tech-synthesizer"]["scout_name"] = {"tech-scout", "ux-scout"}
    bindings: dict[str, dict[str, set[str]]] = {a["name"]: {} for a in agents}

    def add_bindings(agent_name: str, match_dict: dict[str, str]):
        for k, v in match_dict.items():
            bindings[agent_name].setdefault(k, set()).add(v)

    for agent in agents:
        name = agent["name"]
        _resolve_template_writes(
            agent,
            name,
            concrete_reads,
            G,
            workspace_dir,
            artifact_attrs_fn,
            add_bindings,
        )
        _resolve_template_reads(
            agent,
            name,
            concrete_writes,
            G,
            workspace_dir,
            artifact_attrs_fn,
            add_bindings,
        )

    for agent in agents:
        name = agent["name"]
        _resolve_delegations(agent, name, agents, G, bindings)
