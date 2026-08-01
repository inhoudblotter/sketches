from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Optional
import yaml
from pathlib import Path


class SLASchema(BaseModel):
    latency_ms: Optional[int] = None
    timeout_ms: Optional[int] = None
    ttl_seconds: Optional[int] = None
    retention_days: Optional[int] = None
    retry_policy: Optional[str] = None
    throughput: Optional[str] = None
    availability_target: Optional[str] = None
    model_config = ConfigDict(extra="allow")


class SharedStateDef(BaseModel):
    display_data: List[str] = Field(default_factory=list)
    interactive_elements: List[str] = Field(default_factory=list)
    Recovery: str
    model_config = ConfigDict(extra="allow")


class SharedRules(BaseModel):
    rule_file_size: Optional[str] = None
    rule_valid_email: Optional[str] = None
    model_config = ConfigDict(extra="allow")


class TelemetryEvent(BaseModel):
    event_name: str
    trigger_state: Optional[str] = None
    # Свободная строка, не Literal — базовые значения (session/interaction/
    # high_frequency, см. skill-user-flows.md) рекомендованы, но не единственные
    # допустимые: кастомное значение обязано пройти валидацию, а не упасть.
    frequency_class: Optional[str] = None
    model_config = ConfigDict(extra="allow")


class DesignRationale(BaseModel):
    cognitive_load: str
    friction_justification: str
    business_rule_refs: List[str] = Field(default_factory=list)
    model_config = ConfigDict(extra="allow")


# State names are author-chosen per flow (e.g. "gap_list_ready",
# "loading_gap_list") — there is no fixed set, so `states`/`shared_states`
# are keyed dicts rather than models with named fields.
class StateDef(BaseModel):
    display_data: List[str] = Field(default_factory=list)
    interactive_elements: List[str] = Field(default_factory=list)
    design_rationale: Optional[DesignRationale] = None
    # event -> target, where target is a same-file state name, "ref:<shared
    # state>", or "flow:<other flow_id>" (cross-file handoff).
    ON: Optional[Dict[str, str]] = None
    model_config = ConfigDict(extra="allow")


class UserFlowsSchema(BaseModel):
    author_agent: str
    flow_id: str
    domain: str
    platforms: List[str]
    intent: str
    linked_job_stories: List[str]
    entities: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    shared_rules: Optional[SharedRules] = None
    shared_states: Dict[str, SharedStateDef] = Field(default_factory=dict)
    states: Dict[str, StateDef] = Field(default_factory=dict)
    sla: Optional[SLASchema] = None
    telemetry_events: List[TelemetryEvent] = Field(default_factory=list)
    model_config = ConfigDict(extra="allow")


_REF_PREFIX = "ref:"
_FLOW_PREFIX = "flow:"


def _find_dangling_transitions(schema: UserFlowsSchema) -> List[str]:
    """Transitions (`ON:` targets) that point at neither a declared state in
    this flow nor a declared shared state. `flow:<id>` handoffs to another
    flow file are out of scope here — validating those needs the batch's
    other files, which flows-batch checks separately."""
    state_names = set(schema.states.keys())
    shared_names = set(schema.shared_states.keys())
    dangling = []
    for state_name, state_def in schema.states.items():
        for event, target in (state_def.ON or {}).items():
            if not isinstance(target, str) or target.startswith(_FLOW_PREFIX):
                continue
            if target.startswith(_REF_PREFIX):
                if target[len(_REF_PREFIX) :] not in shared_names:
                    dangling.append(
                        f"state '{state_name}' ON '{event}' targets undeclared shared state '{target}'"
                    )
            elif target not in state_names:
                dangling.append(
                    f"state '{state_name}' ON '{event}' targets undeclared state '{target}'"
                )
    return dangling


def run_validate_user_flows(file_path: Path) -> UserFlowsSchema:
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError("File is empty or invalid YAML")

    schema = UserFlowsSchema.model_validate(data)

    dangling = _find_dangling_transitions(schema)
    if dangling:
        raise ValueError("Dangling state transitions: " + "; ".join(dangling))

    return schema
