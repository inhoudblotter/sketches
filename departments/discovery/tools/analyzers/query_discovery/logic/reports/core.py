from pathlib import Path
from ..core import load_domain_snapshot, load_yaml
from departments.discovery.tools.shared.file_utils import domains_dir_or_warn
from typing import Optional, Dict, Any


def _expected_domain_ids(workspace_dir: Path) -> list:
    manifest = load_yaml(workspace_dir / "discovery" / "meta" / "domains_manifest.yaml")
    return [
        d.get("id")
        for d in manifest.get("domains", [])
        if isinstance(d, dict) and d.get("id")
    ]


def get_toc(workspace_dir: Path, domain: Optional[str] = None) -> dict:
    idx = load_domain_snapshot(workspace_dir)
    res: Dict[str, Any] = {}
    for d_name, d_data in idx.get("domains", {}).items():
        if domain and d_name != domain:
            continue
        epics = d_data.get("epics", [])
        if domain:
            res[d_name] = [
                {"focus": e.get("focus"), "story_count": len(e.get("stories", []))}
                for e in epics
            ]
        else:
            status = (
                "ok"
                if d_data.get("_summary_present")
                else "degraded (summary.yaml missing)"
            )
            res[d_name] = {
                "status": status,
                "executive_summary": d_data.get("executive_summary", ""),
                "epic_count": len(epics),
                "story_count": sum(len(e.get("stories", [])) for e in epics),
            }

    if not domain:
        for expected_id in _expected_domain_ids(workspace_dir):
            if expected_id not in res:
                res[expected_id] = {"status": "MISSING (no summary.yaml produced)"}

    return res


def get_stats(workspace_dir: Path) -> dict:
    idx = load_domain_snapshot(workspace_dir)
    res: Dict[str, Any] = {}
    for d_name, d_data in idx.get("domains", {}).items():
        epics = d_data.get("epics", [])
        res[d_name] = {"pain_levels": {}, "priorities": {}, "epic_types": {}}
        for e in epics:
            et = e.get("epic_type", "core")
            res[d_name]["epic_types"][et] = res[d_name]["epic_types"].get(et, 0) + 1
            for s in e.get("stories", []):
                pl = s.get("pain_level", "unknown")
                res[d_name]["pain_levels"][pl] = (
                    res[d_name]["pain_levels"].get(pl, 0) + 1
                )
        features = d_data.get("features", {})
        res[d_name]["priorities"]["mvp_mandatory"] = len(
            features.get("mvp_mandatory", [])
        )
        res[d_name]["priorities"]["mvp_nice_to_have"] = len(
            features.get("mvp_nice_to_have", [])
        )
    return res


def _process_domain_metrics(metrics: dict, m_type: str, d_name: str, res: dict):
    d_res = {}
    if m_type in ("all", "kpi") and "kpi" in metrics:
        d_res["kpi"] = metrics["kpi"]
    if m_type in ("all", "event") and "critical_events" in metrics:
        d_res["critical_events"] = metrics["critical_events"]
    if d_res:
        res[d_name] = d_res


def _accumulate_global_metrics(
    metrics: dict,
    m_type: str,
    global_kpis: list,
    global_events: list,
    kpi_names: set,
    event_names: set,
) -> None:
    if m_type in ("all", "kpi") and "kpi" in metrics:
        for k in metrics["kpi"]:
            if k.get("name") not in kpi_names:
                kpi_names.add(k.get("name"))
                global_kpis.append(k)
    if m_type in ("all", "event") and "critical_events" in metrics:
        for e in metrics["critical_events"]:
            if e.get("event_name") not in event_names:
                event_names.add(e.get("event_name"))
                global_events.append(e)


def get_domain_metrics(
    workspace_dir: Path,
    domain: Optional[str] = None,
    m_type: str = "all",
    is_global: bool = False,
) -> dict:
    idx = load_domain_snapshot(workspace_dir)
    res: Dict[str, Any] = {}
    global_kpis: list = []
    global_events: list = []
    kpi_names: set = set()
    event_names: set = set()

    for d_name, d_data in idx.get("domains", {}).items():
        if not is_global and domain and d_name != domain:
            continue
        metrics = d_data.get("domain_metrics", {})
        if not metrics:
            continue

        if is_global:
            _accumulate_global_metrics(
                metrics, m_type, global_kpis, global_events, kpi_names, event_names
            )
        else:
            _process_domain_metrics(metrics, m_type, d_name, res)

    if is_global:
        g_res = {}
        if global_kpis:
            g_res["kpis"] = global_kpis
        if global_events:
            g_res["critical_events"] = global_events
        return {"global_metrics": g_res}
    return res


def _compute_entity_metrics(entities: list) -> dict:
    d_metrics = {
        "total_entities": len(entities),
        "aggregate_roots": 0,
        "value_objects": 0,
        "total_attributes": 0,
        "total_relationships": 0,
    }
    for ent in entities:
        ent_type = ent.get("type", "")
        if ent_type == "AggregateRoot":
            d_metrics["aggregate_roots"] += 1
        elif ent_type == "ValueObject":
            d_metrics["value_objects"] += 1
        d_metrics["total_attributes"] += len(ent.get("attributes", []))
        d_metrics["total_relationships"] += len(ent.get("relationships", []))
    return d_metrics


def get_data_model_metrics(
    workspace_dir: Path, domain: Optional[str] = None, is_global: bool = False
) -> dict:
    res: Dict[str, Any] = {}
    global_metrics = {
        "total_entities": 0,
        "aggregate_roots": 0,
        "value_objects": 0,
        "total_attributes": 0,
        "total_relationships": 0,
    }

    domains_dir = domains_dir_or_warn(workspace_dir)
    if domains_dir is None:
        return {"global_metrics": global_metrics} if is_global else res

    for domain_dir in sorted(domains_dir.iterdir()):
        if not domain_dir.is_dir() or (
            not is_global and domain and domain_dir.name != domain
        ):
            continue

        dict_data = load_yaml(domain_dir / "dictionary.yaml")
        entities = dict_data.get("entities", [])
        if not entities:
            continue

        d_metrics = _compute_entity_metrics(entities)

        if is_global:
            for k in global_metrics:
                global_metrics[k] += d_metrics[k]
        else:
            res[domain_dir.name] = d_metrics

    if is_global:
        return {"global_metrics": global_metrics}
    return res
