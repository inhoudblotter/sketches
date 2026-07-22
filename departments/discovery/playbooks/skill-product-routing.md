# Skill: Product Routing & Operational Constraints

**Цель:** Строгое управление операционным пайплайном трансляции продуктовых требований, выбор платформ, соблюдение контрактов файловой структуры и синтаксических правил генерации артефактов.

## 1. Концептуальные ограничения (Workflow Constraints)
- **Асимметрия функционала (Platform Strategy):** Никогда не предполагай платформу (Web, iOS, Android, Telegram Bot, Desktop) по умолчанию. Всегда выбирай оптимальные платформы для MVP, оценивая: физический контекст использования, аппаратные требования (камера, GPS), плотность данных (Data Density) и барьер входа (Friction). Разные платформы решают разные задачи, функционал не должен быть абсолютно симметричным.

## 2. Операционный Пайплайн (Workflow Pipeline)

### Шаг 1: Product Trajectory Analysis (Diagnostics Tool vs Platform)
- **Триггер:** Выполняется самым первым, до шага Idea Augmentation.
- **Действие:** Проверка трех признаков Platform Trajectory:
  1. Two-sided market: Есть ли две стороны с разными интересами?
  2. Network Effect: Становится ли продукт ценнее с ростом числа пользователей?
  3. Third-party Value: Есть ли третьи стороны, которым ценна аудитория или данные?
- **Обязательный вывод:** В файл `features_index.md` ОБЯЗАТЕЛЬНО добавить раздел **Strategic Trajectory** с выводом:
  - **Вариант A: Pure SaaS Tool** (если нет сетевого эффекта, строим монолитный инструмент; текущая фича = ядро).
  - **Вариант B: Platform** (если ≥2 признаков, текущая фича = Growth Acquisition Channel; архитектура должна поддерживать multi-tenant; расписать функционал на NOW, NEXT, LATER).

### Шаг 2: Idea Augmentation (Скрытая инфраструктура)
- **Триггер:** При детализации базового (Core) функционала.
- **Действие:** Использовать чек-лист для распределения скрытой инфраструктуры по доменам:
  - Identity → Auth
  - Value Exchange → Billing
  - Physical Constraints → Physical Dependencies
  - Governance → System / Backoffice (Всегда 100%)
  - Retention → Notifications
  - Personalization → Settings
  - Tooling → Профильный редактор
  - Community → Community / Social
  - Collaboration → Collaboration
  - Matchmaking → Marketplace
  - Growth → Growth / Public Presence
  - Edge Computing → On-Device Processing
  - Ecosystem & Hardware (Core Value Prop) → выделяй полноценный домен (например, `devices` или `hardware`), если продукт физически не функционирует без устройства/сенсора (аппаратный доступ к среде — не косметика)
  - Ecosystem & Hardware (Peripheral) → Future Features, если устройство — необязательное расширение уже работающего цифрового ядра

## 3. Правила Файловой Системы и Синтаксиса (File System & Syntax Rules)
- **Business-Sliced Design (Маршрутизация):** Вся генерация артефактов строго изолируется по доменам.
  - Все контракты, относящиеся к домену `{domain}`, обязаны лежать строго в папке: `workspace/discovery/domains/{domain}/`.
  - Внутри папки должны лежать исключительно: `dictionary.yaml` (сущности только этого домена), `summary.yaml`, `features.yaml` и папка `epics/` (сценарии, оценки и стейт-машины).
- **Ubiquitous Language Framework (Синтаксис YAML):**
  - **Отказ от тех-сленга:** ЗАПРЕЩЕНО использовать в словаре типы БД (например, `UUID`, `varchar`, `boolean`). Используй бизнес-типы (`Identifier`, `Text`, `Status Flag`). Названия сущностей берутся из реального мира бизнеса (не `UserRecord`, а `Client`).
  - **Кросс-доменные ссылки (Bounded Context):** Запрещено неявно ссылаться на сущности из других доменов. Обязателен префикс неймспейса: `[domain].[EntityName]` (например, `catalog.SurfaceType` или `auth.User`).
  - **Однозначность:** Одно понятие = один термин (запрещены синонимы вроде Order/Request/Application в рамках одного проекта).
  - **Состояния (State):** Ключевые состояния сущности (например, Оплачен, Отменен) должны быть явно зафиксированы.

## 4. Анти-паттерны (Anti-Patterns)
- ❌ **Свалка файлов (Attention Dilution):** Запрещено создавать общие папки (`shared`) или файлы-монстры на множество килобайт. Контракты каждого домена хранятся исключительно в его изолированной папке.
- ❌ **Техническая структура БД:** Проектирование `dictionary.yaml` с использованием технических типов данных баз данных вместо бизнес-сущностей и терминов.
