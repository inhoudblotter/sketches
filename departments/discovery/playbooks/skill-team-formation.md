# Skill: Team Formation (Формирование Команды)

**Цель:** Операционный фреймворк проектирования минимальной жизнеспособной команды (Minimum Viable Team) для обеспечения и масштабирования продукта. Превращает функциональные требования (Job Stories) и нагрузочные метрики (MAU) в структурированный Headcount с обоснованными зарплатными вилками.

## 1. Принципы отбора ролей (Role Selection Heuristics)

- **Zero-Admin First:** Прежде чем создать роль — задай вопрос: «Может ли её заменить автоматизация, AI-агент или DAO-делегат?». Только если ответ «нет» — создавай штатную единицу.
- **Load-Driven Headcount:** Любое число людей в команде обязано быть выводом из формулы, а не экспертным мнением. Эталонная формула: `HC = ceil(target_mau / capacity_per_person_per_month)`. Использовать `python3 -c` для вычисления.
- **Functional Coverage Matrix:** Каждый класс функций из Job Stories (support, moderation, ops, devops, data, legal) должен быть явно закрыт хотя бы одной ролью или помечен как «Automated / DAO-delegated». Незакрытые функции — эскалация.
- **Dual-Hat Tolerance:** На ранней стадии (<10K MAU) одна роль может закрывать до двух смежных функций. При масштабировании (>100K MAU) — дуал-хэт снимается, роли дробятся.

## 2. Категории ролей (Role Taxonomy)

| Категория | Типовые роли | Trigg | Zero-Admin Substitute |
|---|---|---|---|
| **L1 Support** | Customer Support Specialist | Первые 1 000 активных пользователей | AI chatbot + async helpdesk |
| **Trust & Safety** | Content Moderator / Trust Agent | UGC или транзакционный marketplace | AI pre-filter + DAO-кураторы |
| **Operations** | Ops Manager / COO-функция | >3 активных внешних партнёра | Workflow automation (Make, Zapier) |
| **DevOps / SRE** | DevOps Engineer | Собственная инфраструктура или uptime SLA | Fully managed PaaS + Terraform |
| **Data / Analytics** | Data Analyst | Аналитика нужна для юнит-экономики | BI SaaS (Metabase, Hex) |
| **Legal / Compliance** | Legal Counsel | Регулируемый рынок, GDPR, финтех | Внешний retainer (не FTE) |
| **Community / DAO** | Community Manager / DAO Facilitator | Активная комьюнити-экономика | Token-incentivized delegates |

## 3. Расчёт Headcount (Формульный Метод)

### Шаг 1: Определи capacity_per_person

Для каждой роли установи дневную производительность из отраслевых бенчмарков:

| Роль | Capacity / month (единица нагрузки) |
|---|---|
| L1 Support | 400–800 обращений / месяц |
| Модератор | 2 000–5 000 единиц контента / месяц |
| DevOps | 20–50 сервисов / FTE |
| Аналитик | 3–5 дашбордов / месяц |

### Шаг 2: Вычисли HC

```
HC = ceil(metric_per_month / capacity_per_person)
```

Например, для L1 Support при 50 000 MAU, конверсии в обращения 2% (=1 000 тикетов/мес), capacity 500 тикетов/чел:
`HC = ceil(1000 / 500) = 2`

**Все расчёты выполнять через `python3 -c \"...\"`** — см. `skill-quantitative-integrity.md`.

### Шаг 3: Сценарное масштабирование

Привязывай Headcount к трём сценариям из `revenue_model.yaml` (Worst / Base / Best MAU):
- Worst: минимальный HC (возможно 0 — только автоматизация).
- Base: основной HC для артефакта `operations_team.yaml`.
- Best: peak HC с учётом дуал-хэт снятия и роста.

## 4. Зарплатные вилки (Salary Research Protocol)

- **Обязательный поиск:** Для каждой роли вызывай `search_web` минимум с двумя запросами — один по локальному рынку (если юрисдикция определена из `compliance_constraints.md`), один по глобальному рынку (USD).
- **Приоритет источников:** HH.ru (для СНГ), Glassdoor / levels.fyi (для глобального), LinkedIn Salary.
- **Формат результата:** Указывай медиану (P50), а не диапазон. Диапазон — в поле `salary_rationale`.
- **Запрет оценки «в уме»:** Любая зарплата, не подкреплённая результатом `search_web`, блокирует валидацию артефакта.

## 5. Выходной артефакт (Output Mapping)

Каждая роль маппируется в одну запись шаблона `operations_team_template.yaml`:

```yaml
roles:
  - id: l1_support
    title: 'Customer Support Specialist'
    headcount_formula: 'ceil(target_mau * 0.02 / 500)'
    estimated_headcount: 2          # результат python3 -c
    salary_usd: 1200                # P50 из search_web
    salary_rationale: '[ссылка: hh.ru поиск...]'
    responsibilities:
      - 'Обработка входящих тикетов из Job Story bs-003'
      - 'Эскалация блокирующих багов в DevOps'
```

`total_monthly_payroll_usd` = сумма `(estimated_headcount * salary_usd)` по всем ролям — вычислять через `python3 -c`.

## 6. Анти-паттерны (Anti-Patterns)

- ❌ **HC без формулы:** Указание числа людей без явного расчёта через `headcount_formula`. Нарушение трассируемости.
- ❌ **Роль без покрытия Job Story:** Если роль не привязана ни к одной Job Story для ролей из `domains_manifest.yaml`, она является галлюцинацией (No Role Bleed нарушен в обратную сторону).
- ❌ **Full-Time вместо Retainer:** Юридические и compliance-функции на ранней стадии всегда внешний retainer, не FTE.
- ❌ **Игнорирование Zero-Admin альтернативы:** Заполнять роль штатом без предварительной проверки автоматизации — запрещено.
- ❌ **ФОТ вне COGS:** `total_monthly_payroll_usd` должен быть перенесён в `fixed_monthly_usd` cogs-scout'ом. Ops-scout не вносит данные напрямую в юнит-экономику — только в `operations_team.yaml`.
