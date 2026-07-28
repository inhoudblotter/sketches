# WORKFLOW: Отдел Discovery

> Автоматически сгенерировано `pipeline-analysis` из frontmatter агентов (`departments/discovery/staff`). Не редактируйте руками — правьте агентов и перегенерируйте файл (`pipeline-analysis discovery`). Философия и назначение отдела: см. [README.md](README.md).

**Generated:** 2026-07-28T11:59:14.842381+00:00

---

## Execution Plan

Фазы выведены из топологического порядка графа зависимостей (кто что читает/пишет), не заданы вручную — агенты в одной фазе не зависят друг от друга и могут выполняться параллельно.

### Phase 1

#### `business-synthesizer`
Синтезатор бизнес-контекста. Объединяет сырые данные от product и marketing скаутов и формирует единый отчет (Market Context) для PO Strategist, отфильтровывая шум и разрешая бизнес-конфликты.

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 84.4 (~, часть входов ещё не сгенерирована) |
| Status | READY |
**Required skills:** 7
**Uses tools:** 11
**Delegates to:** 6

**Reads (Inputs):**
  - `PROMPT.md`
  - `market_dossier.md`
  - `gtm_strategy.md`
  - `audience_draft.yaml`
  - `growth_draft.md`
  - `geopolitical_draft.yaml`

**Writes (Outputs):**
  - `{patch_name}.yaml`
  - `market_context.md`
  - `tech_market_brief.yaml`

##### `product-scout` _(subagent)_
Скаут по конкурентному ландшафту и продуктовой стратегии. Исследует существующих игроков, выявляет Gaps и помогает сформулировать Value Proposition.

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 58.3 |
**Required skills:** 7
**Uses tools:** 1

**Reads (Inputs):**
  - `PROMPT.md`
  - `{patch_name}.yaml`

**Writes (Outputs):**
  - `market_dossier.md`

##### `marketing-scout` _(subagent)_
Исследователь стратегий выхода на рынок (GTM) и SEO. Ищет каналы привлечения пользователей.

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 35.1 |
**Required skills:** 5
**Uses tools:** 1

**Reads (Inputs):**
  - `PROMPT.md`
  - `{patch_name}.yaml`

**Writes (Outputs):**
  - `gtm_strategy.md`

##### `growth-hacker-scout` _(subagent)_
Исследователь органического роста и виральности. Проектирует "Линзы Латерального Комьюнити", Magnet Features и Day-0 Traction Hooks на основе изначальной идеи.

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 21.8 |
**Required skills:** 3
**Uses tools:** 1

**Reads (Inputs):**
  - `PROMPT.md`
  - `{patch_name}.yaml`

**Writes (Outputs):**
  - `growth_draft.md`

##### `audience-scout` _(subagent)_
Исследователь аудитории. Собирает поведенческие данные, боли и субкультурные паттерны из открытых источников и формирует черновик target_audience_draft для Revenue Scout и PO Strategist.

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 31.3 |
**Required skills:** 5
**Uses tools:** 1

**Reads (Inputs):**
  - `PROMPT.md`
  - `{patch_name}.yaml`

**Writes (Outputs):**
  - `audience_draft.yaml`

##### `geopolitics-scout` _(subagent)_
Geopolitics & Censorship Scout. Исследует межгосударственные ограничения, барьеры Splinternet и риски цензуры.

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 26.1 |
**Required skills:** 4
**Uses tools:** 1

**Reads (Inputs):**
  - `PROMPT.md`
  - `{patch_name}.yaml`

**Writes (Outputs):**
  - `geopolitical_draft.yaml`

##### `revenue-scout` _(subagent)_
Финансовый скаут (Доходы). Оценивает готовность платить (Willingness to Pay), анализирует конкурентов и формирует бюджетные ограничения для технических решений.

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 144.1 (~, часть входов ещё не сгенерирована) |
**Required skills:** 8
**Uses tools:** 2

**Reads (Inputs):**
  - `PROMPT.md`
  - `market_context.md`
  - `audience_draft.yaml`
  - `{patch_name}.yaml`

**Writes (Outputs):**
  - `revenue_model.yaml`

### Phase 2

#### `po-strategist`
Product Strategist (Генератор смыслов). Разрабатывает общую стратегию MVP, выделяет домены и агрегирует/приоритизирует фичи на основе Job Stories, сгенерированных саб-агентом.

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 95.4 (~, часть входов ещё не сгенерирована) |
| Status | BLOCKED |
**Required skills:** 11
**Uses tools:** 28
**Delegates to:** 2
**Blocked on:** 1

**Reads (Inputs):**
  - `PROMPT.md`
  - `market_context.md`
  - `revenue_model.yaml`

**Writes (Outputs):**
  - `product_vision_and_critique.md`
  - `target_audience.yaml`
  - `{patch_name}.yaml`
  - `platform_strategy.yaml`
  - `domains_manifest.yaml`
  - `dictionary.yaml`
  - `{patch_name}.yaml`
  - `business_observability.yaml`

##### `revenue-scout` _(subagent)_
Финансовый скаут (Доходы). Оценивает готовность платить (Willingness to Pay), анализирует конкурентов и формирует бюджетные ограничения для технических решений.

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 144.1 (~, часть входов ещё не сгенерирована) |
**Required skills:** 8
**Uses tools:** 2

**Reads (Inputs):**
  - `PROMPT.md`
  - `market_context.md`
  - `audience_draft.yaml`
  - `{patch_name}.yaml`

**Writes (Outputs):**
  - `revenue_model.yaml`

##### `po-strategist-sub` _(subagent)_
Вспомогательный Product Strategist (Генератор Job Stories). Фокусируется на одном конкретном бизнес-домене, анализирует его скоуп и роли, и генерирует детальный список Job Stories (JTBD) по контракту.

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 13.8 (~, часть входов ещё не сгенерирована) |
**Required skills:** 2
**Uses tools:** 2

**Reads (Inputs):**
  - `{patch_name}.yaml`
  - `target_audience.yaml`
  - `platform_strategy.yaml`
  - `domains_manifest.yaml`
  - `dictionary.yaml`

**Writes (Outputs):**
  - `stories.yaml`
  - `features.yaml`
  - `summary.yaml`
  - `domain_errata.yaml`

### Phase 3

#### `tech-synthesizer`
Синтезатор технического контекста. Объединяет данные от tech, ux, devops, compliance скаутов и формирует технические ограничения для архитекторов (ux-flow-architect и system-design-architect).

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 53.9 (~, часть входов ещё не сгенерирована) |
| Status | BLOCKED |
**Required skills:** 5
**Uses tools:** 11
**Delegates to:** 6
**Blocked on:** 2

**Reads (Inputs):**
  - `revenue_model.yaml`
  - `business_observability.yaml`
  - `tech_benchmarks.md`
  - `deployment_strategy.md`
  - `algorithm_benchmarks.md`
  - `compliance_constraints.md`
  - `ux_research.md`

**Writes (Outputs):**
  - `{patch_name}.yaml`
  - `tech_conflict_log.md`
  - `ux_vision.md`
  - `tech_constraints.yaml`
  - `ux_constraints.yaml`

##### `tech-scout` _(subagent)_
Исследователь технологических бенчмарков. Ищет в интернете лучшие практики, открытые библиотеки и известные проблемы для реализации заявленных функций.

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 69.5 (~, часть входов ещё не сгенерирована) |
**Required skills:** 8
**Uses tools:** 4

**Reads (Inputs):**
  - `platform_strategy.yaml`
  - `revenue_model.yaml`
  - `tech_market_brief.yaml`
  - `business_observability.yaml`
  - `supported_tech_stacks.yaml`
  - `{patch_name}.yaml`

**Writes (Outputs):**
  - `tech_benchmarks.md`

##### `devops-scout` _(subagent)_
Исследователь инфраструктуры и SRE-практик. Ищет стандарты деплоя, CI/CD паттерны и стратегии масштабирования для заданного стека и нагрузки.

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 127.5 (~, часть входов ещё не сгенерирована) |
**Required skills:** 8
**Uses tools:** 4

**Reads (Inputs):**
  - `platform_strategy.yaml`
  - `revenue_model.yaml`
  - `tech_market_brief.yaml`
  - `business_observability.yaml`
  - `pricing_oracle.yaml`
  - `{patch_name}.yaml`

**Writes (Outputs):**
  - `deployment_strategy.md`

##### `ai-data-scout` _(subagent)_
Исследователь математических алгоритмов, AI-моделей и датасетов. Подбирает оптимальные решения для сложных вычислительных задач.

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 29.9 (~, часть входов ещё не сгенерирована) |
**Required skills:** 4
**Uses tools:** 4

**Reads (Inputs):**
  - `platform_strategy.yaml`
  - `revenue_model.yaml`
  - `business_observability.yaml`
  - `{patch_name}.yaml`

**Writes (Outputs):**
  - `algorithm_benchmarks.md`

##### `compliance-scout` _(subagent)_
Исследователь юридических рисков и комплаенса. Ищет требования к хранению данных и лицензированию.

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 26.5 (~, часть входов ещё не сгенерирована) |
**Required skills:** 4
**Uses tools:** 3

**Reads (Inputs):**
  - `platform_strategy.yaml`
  - `tech_market_brief.yaml`
  - `business_observability.yaml`
  - `{patch_name}.yaml`

**Writes (Outputs):**
  - `compliance_constraints.md`

##### `ux-scout` _(subagent)_
Исследователь пользовательского опыта и эргономики. Собирает паттерны взаимодействия, адаптированные под среду использования и устройства.

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 36.3 (~, часть входов ещё не сгенерирована) |
**Required skills:** 5
**Uses tools:** 4

**Reads (Inputs):**
  - `platform_strategy.yaml`
  - `target_audience.yaml`
  - `business_observability.yaml`
  - `{patch_name}.yaml`

**Writes (Outputs):**
  - `ux_research.md`

##### `cogs-scout` _(subagent)_
Финансовый аналитик (Расходы). Подбивает итоговую юнит-экономику, рассчитывая себестоимость инфраструктуры (COGS) на основе технических ограничений и сравнивая ее с доходами.

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 120.7 (~, часть входов ещё не сгенерирована) |
**Required skills:** 7
**Uses tools:** 2

**Reads (Inputs):**
  - `revenue_model.yaml`
  - `tech_constraints.yaml`
  - `business_observability.yaml`
  - `{patch_name}.yaml`
  - `pricing_oracle.yaml`
  - `compliance_constraints.md`

**Writes (Outputs):**
  - `unit_economics_model.yaml`

### Phase 4

#### `ux-flow-architect`
UX Flow Architect (Проектировщик путей). Планирует полный список пользовательских сценариев через State Machines на основе Job Stories и платформ, затем проверяет полноту результата.

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 25.1 (~, часть входов ещё не сгенерирована) |
| Status | BLOCKED |
**Required skills:** 3
**Uses tools:** 17
**Delegates to:** 1
**Blocked on:** 5

**Reads (Inputs):**
  - `domains_manifest.yaml`
  - `platform_strategy.yaml`
  - `ux_constraints.yaml`

**Writes (Outputs):**
  - `{patch_name}.yaml`

##### `ux-flow-architect-sub` _(subagent)_
Вспомогательный UX Flow Architect. Фокусируется на генерации Машин Состояний (State Machines) для группы Job Stories, детально прописывая бизнес-логику, информационные контракты и Edge Cases в YAML.

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 36.5 (~, часть входов ещё не сгенерирована) |
**Required skills:** 4
**Uses tools:** 2

**Reads (Inputs):**
  - `dictionary.yaml`
  - `ux_constraints.yaml`
  - `stories.yaml`
  - `{patch_name}.yaml`

**Writes (Outputs):**
  - `{flow_id}.yaml`
  - `errata.yaml`

### Phase 5

#### `tech-lead`
Tech Lead (Технический Лид). Управляет фазой технической эстимации (Story Points), выполняет Post-Discovery Aggregation — строит bounded_contexts.yaml (для Architecture) и триажит global errata в critical_errata.yaml (для discovery-pitcher) через утилиты и саб-агентов.

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 2.1 (~, часть входов ещё не сгенерирована) |
| Status | BLOCKED |
**Uses tools:** 17
**Delegates to:** 2
**Blocked on:** 4

**Reads (Inputs):**
  - `business_observability.yaml`


##### `tech-estimator` _(subagent)_
Technical Estimator. Анализирует сгенерированные Job Stories и оценивает их сложность в Story Points (по шкале Фибоначчи), выявляя переусложненные или скрытые технические требования.

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 31.0 (~, часть входов ещё не сгенерирована) |
**Required skills:** 1
**Uses tools:** 1

**Reads (Inputs):**
  - `tech_constraints.yaml`
  - `stories.yaml`
  - `{flow_id}.yaml`

**Writes (Outputs):**
  - `estimation.yaml`

##### `errata-resolver` _(subagent)_
Саб-агент Фазы 7.5 (Triage Agent). Очищает сырой AST лог ошибок от тривиального шума, схлопывает дубликаты, разрешает противоречия и оставляет только Actionable Blockers.

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 5.1 |
**Required skills:** 1
**Uses tools:** 3


**Writes (Outputs):**
  - `critical_errata.yaml`

### Phase 6

#### `discovery-pitcher`
Discovery Auditor (Red Teamer). Анализирует собранную стратегию, экономику и технические ограничения. Формирует жесткий инвестиционный меморандум для владельцев, выявляя слабые места и нестыковки.

| Field | Value |
|---|---|
| Model | sonnet |
| Temperature | 0.5 |
| Context KB | 75.6 (~, часть входов ещё не сгенерирована) |
| Status | BLOCKED |
**Required skills:** 9
**Uses tools:** 11
**Blocked on:** 5

**Reads (Inputs):**
  - `project_analytics.yaml`
  - `bounded_contexts.yaml`
  - `market_context.md`
  - `ux_vision.md`
  - `product_vision_and_critique.md`
  - `tech_conflict_log.md`

**Writes (Outputs):**
  - `launch_roadmap.yaml`
  - `investment_memo.md`
  - `pitch_deck.yaml`

---



