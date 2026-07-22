# ARTIFACTS: Отдел Discovery

> Автоматически сгенерировано `pipeline-analysis` из графа агентов (`departments/discovery/staff`).
**Generated:** 2026-07-21T23:13:40.036374+00:00

---

## 📥 Внешние входы (External Inputs)
Файлы, которые читаются агентами этого отдела, но не генерируются внутри него.

- `workspace/inputs/PROMPT.md`

---

## 📤 Внешние выходы (External Outputs)
Файлы, которые генерируются внутри этого отдела, но не используются (не читаются) его агентами. Они могут быть точками входа для других отделов или финальными артефактами.

- `workspace/discovery/strategy/investment_memo.md`
- `workspace/discovery/pitch_deck.html`

---

## 🛡️ Покрытие линтерами (Linter Coverage)
Доля выходных файлов отдела (сгенерированных агентом или тулом), которые проверяются хотя бы одним линтером (`tool_type: linter`, чей `inputs` совпадает с путём файла).

**97.7%** выходных артефактов покрыто линтерами.

Не покрыты линтером:
- `workspace/discovery/strategy/product_vision_and_critique.md`

---

## 🗂️ Дерево внутренних артефактов (Internal Artifacts Tree)
Структура директорий и файлов (включая будущие плейсхолдеры), генерируемых отделом.

```text
└── workspace
    └── discovery
        ├── domains
        │   └── {domain}
        │       ├── dictionary.yaml
        │       ├── domain_errata.yaml
        │       ├── epics
        │       │   └── {epic_name}
        │       │       ├── errata.yaml
        │       │       ├── estimation.yaml
        │       │       ├── features.yaml
        │       │       ├── flows
        │       │       │   └── {flow_id}.yaml
        │       │       ├── patches
        │       │       │   └── {patch_name}.yaml
        │       │       └── stories.yaml
        │       ├── patches
        │       │   └── {patch_name}.yaml
        │       └── summary.yaml
        ├── errata
        │   └── critical_errata.yaml
        ├── meta
        │   ├── bounded_contexts.yaml
        │   ├── domains_manifest.yaml
        │   ├── project_analytics.yaml
        │   └── project_analytics_detail.yaml
        ├── pitch_deck.html
        ├── pitch_deck.yaml
        ├── research
        │   ├── business-context
        │   │   ├── audience_draft.yaml
        │   │   ├── geopolitical_draft.yaml
        │   │   ├── growth_draft.md
        │   │   ├── gtm_strategy.md
        │   │   ├── market_dossier.md
        │   │   └── patches
        │   │       └── {patch_name}.yaml
        │   └── technical-context
        │       ├── algorithm_benchmarks.md
        │       ├── compliance_constraints.md
        │       ├── deployment_strategy.md
        │       ├── patches
        │       │   └── {patch_name}.yaml
        │       ├── tech_benchmarks.md
        │       └── ux_research.md
        └── strategy
            ├── business_observability.yaml
            ├── investment_memo.md
            ├── launch_roadmap.yaml
            ├── market_context.md
            ├── patches
            │   └── {patch_name}.yaml
            ├── platform_strategy.yaml
            ├── product_vision_and_critique.md
            ├── revenue_model.yaml
            ├── target_audience.yaml
            ├── tech_conflict_log.md
            ├── tech_constraints.yaml
            ├── tech_market_brief.yaml
            ├── unit_economics_model.yaml
            ├── ux_constraints.yaml
            └── ux_vision.md
```