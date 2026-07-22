# Discovery Department Linters

This directory contains `discovery_linter`, a multi-tool that validates agent-generated
YAML/Markdown artifacts in the Discovery workspace against the department's contract
templates (`departments/discovery/contracts/`).

## Architecture

- Each check lives in its own module under `discovery_linter/validators/<group>/<name>/`,
  declaring itself via a sibling `meta.yaml` (name, entrypoint, inputs).
- `discovery_linter/command.py` auto-discovers every `meta.yaml` under `validators/` and
  registers its entrypoint as a subcommand on the `discovery-linter` Typer CLI — there is
  no separate per-check script or `lint.py` entry point.
- **State Machine Integrity**: `general/user_flows` (used by `epic/flows_batch`) checks
  that every `ON:` transition in a User Flow's `states` targets either a state declared in
  the same file, or a `ref:`-prefixed shared state declared in `shared_states`. An
  undeclared target fails validation with a clear error naming the offending state/event;
  there is no auto-fix — a human or the authoring agent corrects the flow. `flow:`-prefixed
  targets (handoffs to another flow file) are out of scope for this check.

## How to Run

```bash
# List every registered check
discovery-linter --help

# Run one check
discovery-linter flows-batch workspace/discovery/domains/<domain>/epics/<epic>/flows
discovery-linter workspace workspace
```

## Running the Tests

```bash
python -m pytest departments/discovery/tools/linters -q
```
