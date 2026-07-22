"""Resolve narrow directory reads against concrete write paths."""

from __future__ import annotations
from pathlib import Path
import networkx as nx

MIN_SEGMENTS = 4
MIN_DEPTH = 3


def _group_dir_writers(write_index: dict[str, str]) -> dict[str, set[str]]:
    dir_writers: dict[str, set[str]] = {}
    for write_path, writer in write_index.items():
        prefix = "/".join(write_path.split("/")[:MIN_DEPTH]) + "/"
        dir_writers.setdefault(prefix, set()).add(writer)
        parts = write_path.split("/")
        if len(parts) >= MIN_SEGMENTS:
            sub = "/".join(parts[:MIN_SEGMENTS]) + "/"
            dir_writers.setdefault(sub, set()).add(writer)
    return dir_writers


def _resolve_agent_dir_reads(
    agent: dict,
    write_index: dict[str, str],
    G: nx.DiGraph,
    workspace_dir: Path,
    artifact_attrs_fn,
) -> None:
    name = agent["name"]
    dir_reads = [r for r in agent["reads"] if r.endswith("/")]
    optional_dir_reads = [r for r in agent.get("optional_reads", []) if r.endswith("/")]
    for dir_prefix in dir_reads:
        depth = dir_prefix.rstrip("/").count("/")
        if depth < MIN_DEPTH:
            continue
        is_optional = dir_prefix in optional_dir_reads
        for write_path, writer in write_index.items():
            if write_path.startswith(dir_prefix) and writer != name:
                if write_path not in G:
                    G.add_node(
                        write_path, **artifact_attrs_fn(write_path, workspace_dir)
                    )
                G.add_edge(write_path, name, edge_type="reads", is_optional=is_optional)


def resolve_directories(
    G: nx.DiGraph, agents: list[dict], workspace_dir: Path, artifact_attrs_fn
) -> None:
    write_index: dict[str, str] = {}
    for agent in agents:
        for w in agent["writes"]:
            write_index[w] = agent["name"]

    _group_dir_writers(write_index)

    for agent in agents:
        _resolve_agent_dir_reads(
            agent, write_index, G, workspace_dir, artifact_attrs_fn
        )
