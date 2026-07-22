from pydantic import BaseModel
from typing import List


class Dependency(BaseModel):
    target_domain: str
    relationship_type: str
    data_exchanged: List[str]
    business_reason: str


class Context(BaseModel):
    domain: str
    description: str
    dependencies: List[Dependency] = []


class SharedSignal(BaseModel):
    signal_type: str
    value: str
    domains: List[str]


class BoundedContextsOutput(BaseModel):
    contexts: List[Context]
    shared_kernel_signals: List[SharedSignal] = []


class ExtractBoundedContextsInput(BaseModel):
    domains_dir: str
    output_file: str
