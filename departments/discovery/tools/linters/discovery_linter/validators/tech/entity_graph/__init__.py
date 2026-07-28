from pydantic import BaseModel, Field
from typing import List, Optional, Set, Any
from pathlib import Path
import networkx as nx
import yaml


class ValidateEntityGraphInput(BaseModel):
    domains_dir: Path = Field(
        ...,
        description="Path to the domains directory containing manifest.yaml and epics/*/flows/*.yaml files",
    )


class EntityEdge(BaseModel):
    epic_or_flow: str
    entity: str
    relation_type: str


class ValidateEntityGraphOutput(BaseModel):
    is_valid: bool
    edges: List[EntityEdge]
    service_coupling_factor: float
    latency_risk_path_length: Optional[int] = None


class EntityItem(BaseModel):
    name: str


class DictionarySchema(BaseModel):
    entities: List[EntityItem]


SCF_THRESHOLD = 0.3


def extract_entities_from_dictionary(data: Any) -> Set[str]:
    entities = set()
    if isinstance(data, dict):
        for entity in data.get("entities") or []:
            if isinstance(entity, dict) and entity.get("name"):
                entities.add(str(entity["name"]))
            elif isinstance(entity, str):
                entities.add(entity)
    return entities


def search_effects_for_entities(
    data: Any, entities: Set[str], current_flow: str, edges: List[EntityEdge]
):
    if isinstance(data, dict):
        for k, v in data.items():
            key_str = str(k).lower()
            if key_str in {
                "read",
                "write",
                "side_effects",
                "effects",
                "creates",
                "updates",
                "deletes",
            }:
                words = str(v).split()
                for w in words:
                    clean_w = "".join(c for c in w if c.isalnum() or c in ["_"])
                    if clean_w in entities:
                        edges.append(
                            EntityEdge(
                                epic_or_flow=current_flow,
                                entity=clean_w,
                                relation_type=key_str,
                            )
                        )
            search_effects_for_entities(v, entities, current_flow, edges)
    elif isinstance(data, list):
        for item in data:
            search_effects_for_entities(item, entities, current_flow, edges)


def run_validate_entity_graph(
    input_data: ValidateEntityGraphInput,
) -> ValidateEntityGraphOutput:
    if not input_data.domains_dir.is_dir():
        raise FileNotFoundError(
            f"Domains directory not found: {input_data.domains_dir}"
        )

    known_entities: Set[str] = set()
    for dict_path in input_data.domains_dir.rglob("manifest.yaml"):
        try:
            dict_data = yaml.safe_load(dict_path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        known_entities.update(extract_entities_from_dictionary(dict_data))

    # Flows are only written after ux-flow-architect-sub finishes per epic
    # (workspace/discovery/domains/{domain}/epics/{epic}/flows/*.yaml) — glob
    # them directly from disk; there is no aggregated index to read paths from.
    edges: List[EntityEdge] = []
    G: Any = nx.DiGraph()

    for flow_path in input_data.domains_dir.rglob("epics/*/flows/*.yaml"):
        try:
            flow_data = yaml.safe_load(flow_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        search_effects_for_entities(flow_data, known_entities, flow_path.stem, edges)

    G.add_nodes_from(known_entities)
    for edge in edges:
        G.add_edge(edge.epic_or_flow, edge.entity, type=edge.relation_type)

    # SCF (Service Coupling Factor) calculated as graph density
    scf = nx.density(G)
    is_valid = scf <= SCF_THRESHOLD

    latency_risk_path_length = None
    if nx.is_directed_acyclic_graph(G):
        longest_path_len = nx.dag_longest_path_length(G)
        if longest_path_len > 1:
            latency_risk_path_length = longest_path_len

    return ValidateEntityGraphOutput(
        is_valid=is_valid,
        edges=edges,
        service_coupling_factor=scf,
        latency_risk_path_length=latency_risk_path_length,
    )
