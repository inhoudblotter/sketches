# Discovery Department Report

**Generated:** 2026-07-21T23:13:40.036374+00:00
**Agents dir:** `departments/discovery/staff`
**Workspace dir:** `workspace/discovery`

---

## Summary

| Status | Count |
|---|---|
| ✅ DONE | 0 |
| 🔵 READY | 1 |
| 🔴 BLOCKED | 5 |
| 🟠 ESCALATED | 0 |
| ⬜ UNKNOWN | 0 |
| **Subagents** | **16** |
| **Completion** | **0.0%** |
| **Contract coverage** | **96.9%** |
| **Output Contract Coverage** | **97.7%** |

---

## Pipeline Status



| Agent | Model | Temp | Status | Blocked on Agents | Blocked on External |
|---|---|---|---|---|---|
| `business-synthesizer` | sonnet | 0.5 | READY | — | — |
| `↳ product-scout` | sonnet | 0.5 | _internal_ | — | — |
| `↳ marketing-scout` | sonnet | 0.5 | _internal_ | — | — |
| `↳ growth-hacker-scout` | sonnet | 0.5 | _internal_ | — | — |
| `↳ audience-scout` | sonnet | 0.5 | _internal_ | — | — |
| `↳ geopolitics-scout` | sonnet | 0.5 | _internal_ | — | — |
| `↳ revenue-scout` | sonnet | 0.5 | _internal_ | — | — |
| `po-strategist` | sonnet | 0.5 | BLOCKED | business-synthesizer | — |
| `↳ revenue-scout` | sonnet | 0.5 | _internal_ | — | — |
| `↳ po-strategist-sub` | sonnet | 0.5 | _internal_ | — | — |
| `tech-synthesizer` | sonnet | 0.5 | BLOCKED | revenue-scout, po-strategist | — |
| `↳ tech-scout` | sonnet | 0.5 | _internal_ | — | — |
| `↳ devops-scout` | sonnet | 0.5 | _internal_ | — | — |
| `↳ ai-data-scout` | sonnet | 0.5 | _internal_ | — | — |
| `↳ compliance-scout` | sonnet | 0.5 | _internal_ | — | — |
| `↳ ux-scout` | sonnet | 0.5 | _internal_ | — | — |
| `↳ cogs-scout` | sonnet | 0.5 | _internal_ | — | — |
| `ux-flow-architect` | sonnet | 0.5 | BLOCKED | po-strategist, tech-synthesizer, po-strategist-sub | — |
| `↳ ux-flow-architect-sub` | sonnet | 0.5 | _internal_ | — | — |
| `tech-lead` | sonnet | 0.5 | BLOCKED | po-strategist, po-strategist-sub, ux-flow-architect-sub | — |
| `↳ tech-estimator` | sonnet | 0.5 | _internal_ | — | — |
| `↳ errata-resolver` | sonnet | 0.5 | _internal_ | — | — |
| `discovery-pitcher` | sonnet | 0.5 | BLOCKED | tech-lead, business-synthesizer, tech-synthesizer, po-strategist | — |

---

## Context Budget

> "Tool Output KB" is measured by actually running each agent's `<call_tool>` invocations against the real workspace and sizing stdout. A non-templated call runs once ("single"); a templated call outside a `<for_each>` (e.g. `--domain {domain}`) is sampled once per real domain/epic and the 90th percentile size is used ("p90", mirrors how templated `<read>` paths are already sized); a templated call inside a `<for_each>` accumulates every iteration into the same context, measured via one unfiltered call standing in for the cumulative total ("full"). Mutation subcommands (e.g. `rename-entity`, mode "write") are never executed and excluded here — they produce a file, not context the calling agent reads back; see Output Sizes below for that. Invocations with unresolved/unsupported `{placeholder}` variables are skipped and excluded from Tool Output KB entirely. Per-invocation detail (including skipped calls): see "Tool Invocation Cost" below. "Own Write KB" adds this agent's own `<write>` tags — before handoff downstream, that output still sits in its own working context alongside everything it read, so it counts toward Total KB/Risk. Tool-produced output (e.g. a generator's own file) does not: that's a separate process's file, never held in this agent's context — see Output Sizes below for that instead.
>
> Risk bands are calibrated for frontier ~1M-token context windows, where a single agent's own prompt is meant to stay a small slice of the budget: 🟢 OK &lt;150 KB, 🟡 WATCH 150–300 KB (worth a look, not urgent), 🔴 HIGH &gt;300 KB (real context-bloat signal).

| Agent | Skills | Skills KB | Contracts KB | Artifacts KB (p90) | Tool Output KB | Own Write KB | Total KB | Risk |
|---|---|---|---|---|---|---|---|---|
| `po-strategist` | 11 | 80.47 | 7.54 | 14.26 | 0.29 | 7.54 | 102.56~ | 🟢 OK |
| `↳ revenue-scout` | 8 | 71.48 | 7.33 | 9.4 | 0.0 | 7.33 | 88.21~ | 🟢 OK |
| `↳ po-strategist-sub` | 2 | 7.96 | 8.52 | 5.8 | 0.0 | 6.33 | 20.09~ | 🟢 OK |
| `discovery-pitcher` | 9 | 68.3 | 19.22 | 7.29 | 0.0 | 19.22 | 94.81~ | 🟢 OK |
| `business-synthesizer` | 7 | 68.2 | 8.38 | 15.81 | 0.0 | 8.38 | 92.39~ | 🟢 OK |
| `↳ revenue-scout` | 8 | 71.48 | 7.33 | 9.4 | 0.0 | 7.33 | 88.21~ | 🟢 OK |
| `↳ product-scout` | 7 | 57.91 | 6.19 | 0.01 | 0.0 | 6.19 | 64.11 | 🟢 OK |
| `↳ marketing-scout` | 5 | 34.68 | 1.48 | 0.01 | 0.0 | 1.48 | 36.17 | 🟢 OK |
| `↳ audience-scout` | 5 | 30.91 | 2.47 | 0.01 | 0.0 | 2.47 | 33.39 | 🟢 OK |
| `↳ geopolitics-scout` | 4 | 25.66 | 3.17 | 0.01 | 0.0 | 3.17 | 28.84 | 🟢 OK |
| `↳ growth-hacker-scout` | 3 | 21.41 | 2.49 | 0.01 | 0.0 | 2.49 | 23.91 | 🟢 OK |
| `tech-synthesizer` | 5 | 38.05 | 3.93 | 15.89 | 0.0 | 3.93 | 57.87~ | 🟢 OK |
| `↳ tech-scout` | 8 | 54.76 | 1.19 | 14.55 | 0.15 | 1.19 | 70.65~ | 🟢 OK |
| `↳ devops-scout` | 8 | 46.42 | 2.7 | 18.14 | 0.17 | 2.7 | 67.43~ | 🟢 OK |
| `↳ cogs-scout` | 7 | 39.98 | 1.56 | 17.92 | 0.0 | 1.56 | 59.46~ | 🟢 OK |
| `↳ ux-scout` | 5 | 30.75 | 1.85 | 5.42 | 0.15 | 1.85 | 38.17~ | 🟢 OK |
| `↳ ai-data-scout` | 3 | 16.65 | 0.59 | 10.28 | 0.15 | 0.59 | 27.67~ | 🟢 OK |
| `↳ compliance-scout` | 4 | 21.95 | 0.49 | 4.41 | 0.17 | 0.49 | 27.02~ | 🟢 OK |
| `ux-flow-architect` | 3 | 21.6 | 0.0 | 3.26 | 0.23 | 0.0 | 25.09~ | 🟢 OK |
| `↳ ux-flow-architect-sub` | 4 | 31.63 | 8.41 | 4.92 | 0.0 | 6.22 | 42.77~ | 🟢 OK |
| `tech-lead` | 0 | 0.0 | 0.0 | 1.74 | 0.33 | 0.0 | 2.07~ | 🟢 OK |
| `↳ tech-estimator` | 1 | 19.7 | 1.32 | 11.3 | 0.0 | 1.32 | 32.32~ | 🟢 OK |
| `↳ errata-resolver` | 1 | 5.04 | 2.19 | 0.0 | 0.02 | 2.19 | 7.25 | 🟢 OK |
`~` = часть входных файлов ещё не сгенерирована (upstream не отработал) — Total KB для этой строки включает оценку по шаблону контракта, а не только уже существующие файлы.

---

## Tool Invocation Cost

Per-`<call_tool>` breakdown behind the "Tool Output KB" column above. Identical (agent, tool, subcommand, invocation) calls from multiple prompt sites are merged into one row — "Sites" is how many prompt locations contribute to that row's KB, "Samples" is the per-site run count used for sizing (p90 sampling, loop iterations, etc). Skipped (never-executed) calls are omitted — see "Skipped" in Context Budget above.

| Agent | Tool | Subcommand | Mode | Sites | Samples | KB | Invocation |
|---|---|---|---|---|---|---|---|
| `tech-lead` | `Query Discovery` | flows-self-check | single | 1 | 1 | 0.19 | `query-discovery flows-self-check --counts-only workspace/` |
| `ux-flow-architect` | `Query Discovery` | flows-self-check | single | 1 | 1 | 0.19 | `query-discovery flows-self-check workspace/` |
| `ai-data-scout` | `Query Discovery` | requirements | single | 1 | 1 | 0.15 | `query-discovery requirements --global workspace/` |
| `compliance-scout` | `Query Discovery` | requirements | single | 1 | 1 | 0.15 | `query-discovery requirements --global workspace/` |
| `devops-scout` | `Query Discovery` | requirements | single | 1 | 1 | 0.15 | `query-discovery requirements --global workspace/` |
| `tech-scout` | `Query Discovery` | requirements | single | 1 | 1 | 0.15 | `query-discovery requirements --global workspace/` |
| `ux-scout` | `Query Discovery` | requirements | single | 1 | 1 | 0.15 | `query-discovery requirements --global workspace/` |
| `po-strategist` | `Query Discovery` | self-check | single | 1 | 1 | 0.13 | `query-discovery self-check workspace/` |
| `tech-lead` | `Query Discovery` | estimation | single | 1 | 1 | 0.11 | `query-discovery estimation --global workspace/` |
| `po-strategist` | `Query Discovery` | boundary-check | single | 1 | 1 | 0.05 | `query-discovery boundary-check` |
| `po-strategist` | `Query Discovery` | errata-domain | single | 2 | 2 | 0.04 | `query-discovery errata-domain --status open workspace/` |
| `ux-flow-architect` | `Query Discovery` | errata-epic | single | 2 | 2 | 0.04 | `query-discovery errata-epic --status open workspace/` |
| `po-strategist` | `Query Discovery` | orphans | single | 1 | 1 | 0.03 | `query-discovery orphans workspace/` |
| `tech-lead` | `Query Discovery` | coverage | single | 1 | 1 | 0.03 | `query-discovery coverage --check workspace/` |
| `po-strategist` | `Query Discovery` | metrics | single | 1 | 1 | 0.02 | `query-discovery metrics --global --type kpi workspace/` |
| `po-strategist` | `Query Discovery` | metrics | single | 1 | 1 | 0.02 | `query-discovery metrics --global --type event workspace/` |
| `compliance-scout` | `Query Discovery` | metrics | single | 1 | 1 | 0.02 | `query-discovery metrics --type event --global workspace/` |
| `devops-scout` | `Query Discovery` | metrics | single | 1 | 1 | 0.02 | `query-discovery metrics --type event --global workspace/` |
| `errata-resolver` | `Query Discovery` | errata-global | single | 1 | 1 | 0.02 | `query-discovery errata-global --status all workspace/` |
| `po-strategist` | `Query Discovery` | toc | single | 1 | 1 | 0.0 | `query-discovery toc workspace/` |
| `tech-lead` | `Query Discovery` | toc | single | 1 | 1 | 0.0 | `query-discovery toc workspace/` |
| `tech-lead` | `Query Discovery` | stats | single | 1 | 1 | 0.0 | `query-discovery stats workspace/` |
| `tech-lead` | `Query Discovery` | flows | single | 1 | 1 | 0.0 | `query-discovery flows --only-sla workspace/` |
| `tech-lead` | `Query Discovery` | epics | single | 1 | 1 | 0.0 | `query-discovery epics workspace/` |
| `ux-flow-architect` | `Query Discovery` | toc | single | 1 | 1 | 0.0 | `query-discovery toc workspace/` |
| `ux-flow-architect` | `Query Discovery` | stats | single | 1 | 1 | 0.0 | `query-discovery stats workspace/` |
| `ai-data-scout` | `Query Discovery` | epics | single | 1 | 1 | 0.0 | `query-discovery epics --complex-only workspace/` |
| `ai-data-scout` | `Query Discovery` | features | single | 1 | 1 | 0.0 | `query-discovery features --priority mvp_mandatory workspace/` |
| `devops-scout` | `Query Discovery` | epics | single | 1 | 1 | 0.0 | `query-discovery epics --complex-only workspace/` |
| `tech-scout` | `Query Discovery` | epics | single | 1 | 1 | 0.0 | `query-discovery epics --complex-only workspace/` |
| `tech-scout` | `Query Discovery` | stats | single | 1 | 1 | 0.0 | `query-discovery stats workspace/` |
| `ux-scout` | `Query Discovery` | features | single | 1 | 1 | 0.0 | `query-discovery features --priority mvp_mandatory workspace/` |
| `ux-scout` | `Query Discovery` | stories | single | 1 | 1 | 0.0 | `query-discovery stories --pain-level Critical workspace/` |

---

## Output Sizes

> "Write KB" sizes an agent's own `<write>` tags (p90 across glob matches), plus any single-purpose generator/preprocessor/aggregator `<call_tool>` it invokes (e.g. `generate_pitch_deck`, `extract_bounded_contexts`) — their one deterministic output file is sized directly off disk, same as a `<write>` tag. Not context cost (that's Tool Output KB above), just data volume produced. Mutation subcommands (e.g. `rename-entity`) are still excluded: they're never executed, and their real output size is situational (however many entities the diff touches at runtime), so there's nothing reliable to size.

| Agent | Runs | Write KB (p90) | Tool Output KB | Total Output KB |
|---|---|---|---|---|
| `business-synthesizer` | 1 | 0.0 | 0.0 | 0.0 |
| `↳ product-scout` | 1 | 0.0 | 0.0 | 0.0 |
| `↳ marketing-scout` | 1 | 0.0 | 0.0 | 0.0 |
| `↳ growth-hacker-scout` | 1 | 0.0 | 0.0 | 0.0 |
| `↳ audience-scout` | 1 | 0.0 | 0.0 | 0.0 |
| `↳ geopolitics-scout` | 1 | 0.0 | 0.0 | 0.0 |
| `↳ revenue-scout` | 1 | 0.0 | 0.0 | 0.0 |
| `discovery-pitcher` | 1 | 0.0 | 0.0 | 0.0 |
| `po-strategist` | 1 | 0.0 | 0.0 | 0.0 |
| `↳ revenue-scout` | 1 | 0.0 | 0.0 | 0.0 |
| `↳ po-strategist-sub` | 0 | 0.0 | 0.0 | 0.0 |
| `tech-lead` | 0 | 0.0 | 0.0 | 0.0 |
| `↳ tech-estimator` | 0 | 0.0 | 0.0 | 0.0 |
| `↳ errata-resolver` | 1 | 0.0 | 0.0 | 0.0 |
| `tech-synthesizer` | 1 | 0.0 | 0.0 | 0.0 |
| `↳ tech-scout` | 1 | 0.0 | 0.0 | 0.0 |
| `↳ devops-scout` | 1 | 0.0 | 0.0 | 0.0 |
| `↳ ai-data-scout` | 1 | 0.0 | 0.0 | 0.0 |
| `↳ compliance-scout` | 1 | 0.0 | 0.0 | 0.0 |
| `↳ ux-scout` | 1 | 0.0 | 0.0 | 0.0 |
| `↳ cogs-scout` | 1 | 0.0 | 0.0 | 0.0 |
| `ux-flow-architect` | 0 | 0.0 | 0.0 | 0.0 |
| `↳ ux-flow-architect-sub` | 0 | 0.0 | 0.0 | 0.0 |

---

## Parallelism Groups

### Layer 0

- `business-synthesizer`
### Layer 1

- `po-strategist`
### Layer 2

- `tech-synthesizer`
### Layer 3

- `ux-flow-architect`
### Layer 4

- `tech-lead`
### Layer 5

- `discovery-pitcher`

---

## Critical Path

`business-synthesizer → po-strategist → tech-synthesizer → ux-flow-architect → tech-lead → discovery-pitcher`

---

## Model Distribution

| Model | Agents |
|---|---|
| sonnet | 22 |

---

---