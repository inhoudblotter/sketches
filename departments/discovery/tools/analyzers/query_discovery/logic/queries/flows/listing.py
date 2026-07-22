from pathlib import Path
from typing import Optional

from ...core import load_domain_snapshot


def get_filtered_flows(
    workspace_dir: Path,
    domain: Optional[str] = None,
    epic: Optional[str] = None,
    only_sla: bool = False,
) -> list:
    idx = load_domain_snapshot(workspace_dir)
    res = []
    for d_name, d_data in idx.get("domains", {}).items():
        if domain and d_name != domain:
            continue
        for e in d_data.get("epics", []):
            epic_id = e.get("epic_id")
            if epic and epic_id != epic:
                continue
            for flow in e.get("flows", []):
                if only_sla:
                    res.append(
                        {
                            "flow_id": flow.get("flow_id"),
                            "_domain": d_name,
                            "_epic": epic_id,
                            "sla": flow.get("sla", {}),
                            "linked_job_stories": flow.get("linked_job_stories", []),
                        }
                    )
                else:
                    flow_copy = dict(flow)
                    flow_copy["_domain"] = d_name
                    flow_copy["_epic"] = epic_id
                    res.append(flow_copy)
    return res
