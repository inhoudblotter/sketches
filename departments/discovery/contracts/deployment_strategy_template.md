---
author_agent: 'devops-scout'
---
# Deployment Strategy

## 1. Infrastructure Benchmarks
Где и как обычно хостят такие решения (PaaS vs K8s vs Serverless).

### 1.1 Alternatives Comparison
Обязательная таблица по каждому инфраструктурному решению (compute, DB, storage, monitoring): рассмотренные варианты, включая self-hosted-опцию на том же VPS, с явной причиной отказа от неё. Пустая или однострочная таблица (только победитель без альтернатив) — брак.

### 1.2 Self-Hosted-First Compliance
Явный ответ на вопрос из `skill-devops-scout.md` ("Monolith First"): для каждого компонента, вынесенного за пределы единого VPS в managed/multi-vendor решение (Supabase вместо self-hosted Postgres, S3 вместо self-hosted object storage, отдельный HA-регион/облако и т.д.) — обоснование, почему нагрузка/риск оправдывают добавленного вендора и его эксплуатационную стоимость. Если обоснования нет — решение остаётся self-hosted на основном VPS.

## 2. Infrastructure Flows
Базовое описание топологии серверов и сетевого взаимодействия (приветствуются Mermaid диаграммы).

## 3. Monitoring & Logging
Рекомендуемый стек для Observability.

## 4. Data Protection
Стратегии бэкапов и хранения чувствительных данных.

## 5. Scalability Guardrails
На каких этапах и какие ресурсы начнут деградировать (Bottlenecks).

### 5.1 Growth Path
Обязательная таблица по каждому ключевому компоненту (compute, DB, storage): Stage (MVP/N) → Триггер перехода (конкретная метрика/порог из `business_scaling_triggers`) → Действие → Что переписывается / что переживёт переход без рефакторинга. Компонент без описанного пути роста — брак.

### 5.2 Maintainability Note
Кратко (1-2 предложения на компонент): какой эксплуатационной экспертизы требует решение и что происходит, если её нет (команда 1-2 человека, без выделенного SRE/DBA).
