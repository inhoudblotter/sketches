import re
from typing import Dict, Any, List, Tuple

# Плейсхолдеры из шаблона — поля, заполненные ими, считаются незаполненными
_PLACEHOLDER_PATTERN = re.compile(r"^\[.*\]$")

# Обязательные фазы в roadmap
_REQUIRED_PHASES = {"demo_prototype", "seed_mvp", "v1_scale"}

# Обязательные поля в каждой фазе
_REQUIRED_PHASE_FIELDS = {"source_ref", "description", "unit_economics_validation"}

# Паттерн валидной ссылки Traceability: [file.md#L12], [file.yaml#L5-L10] или [file.yaml#L5-10]
_TRACEABILITY_PATTERN = re.compile(r"\[[\w./\-]+#L\d+(-L?\d+)?\]")


def _is_placeholder(value: str) -> bool:
    """Значение является незаполненным плейсхолдером из шаблона."""
    return bool(_PLACEHOLDER_PATTERN.match(str(value).strip()))


def _has_traceability(value: str) -> bool:
    """Значение содержит хотя бы одну валидную ссылку [file#Lxx]."""
    return bool(_TRACEABILITY_PATTERN.search(str(value)))


def _validate_metadata(data: Dict[str, Any], errors: List[str]) -> None:
    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        errors.append("CRITICAL: 'metadata' отсутствует или не является объектом.")
        return

    if not metadata.get("generated_by"):
        errors.append("CRITICAL: metadata.generated_by не заполнен.")
    if (
        not metadata.get("last_updated")
        or metadata.get("last_updated") == "[YYYY-MM-DD]"
    ):
        errors.append(
            "CRITICAL: metadata.last_updated не заполнен (остался плейсхолдер)."
        )


_CONTENT_KEYS = [
    "primary_growth_loop",
    "cold_start_tactics",
    "friction_management",
    "ecosystem_symbiosis",
    "defensibility_moats",
]


def _validate_required_fields(phase_data: dict, prefix: str, errors: List[str]) -> None:
    for field in _REQUIRED_PHASE_FIELDS:
        value = phase_data.get(field)
        if not value:
            errors.append(f"CRITICAL: {prefix} Поле '{field}' отсутствует.")
        elif _is_placeholder(str(value)):
            errors.append(
                f"CRITICAL: {prefix} Поле '{field}' содержит незаполненный "
                f"плейсхолдер: {value!r}"
            )


def _validate_source_ref_traceability(
    phase_data: dict, prefix: str, errors: List[str]
) -> None:
    source_ref = phase_data.get("source_ref", "")
    if (
        source_ref
        and not _is_placeholder(source_ref)
        and not _has_traceability(source_ref)
    ):
        errors.append(
            f"HIGH: {prefix} 'source_ref' не содержит валидной ссылки "
            f"[file.md#Lxx]: {source_ref!r}"
        )


def _has_real_content(val: Any) -> bool:
    if isinstance(val, list):
        return any(not _is_placeholder(str(v)) for v in val)
    return bool(val) and not _is_placeholder(str(val))


def _validate_content_filled(phase_data: dict, prefix: str, errors: List[str]) -> None:
    has_content = any(_has_real_content(phase_data.get(key)) for key in _CONTENT_KEYS)
    if not has_content:
        errors.append(
            f"HIGH: {prefix} Ни один content-ключ не заполнен реальными данными "
            f"({', '.join(_CONTENT_KEYS)}). Фаза содержит только плейсхолдеры."
        )


def _validate_unit_economics_traceability(
    phase_data: dict, prefix: str, warnings: List[str]
) -> None:
    ue_val = phase_data.get("unit_economics_validation", "")
    if ue_val and not _is_placeholder(ue_val) and not _has_traceability(ue_val):
        warnings.append(
            f"MEDIUM: {prefix} 'unit_economics_validation' не содержит ссылки "
            f"[file#Lxx] — добавь источник для Traceability."
        )


def _validate_phase(
    phase_id: str, phase_data: Any, errors: List[str], warnings: List[str]
) -> None:
    if not isinstance(phase_data, dict):
        errors.append(f"CRITICAL: Фаза '{phase_id}' не является объектом.")
        return

    prefix = f"[{phase_id}]"
    _validate_required_fields(phase_data, prefix, errors)
    _validate_source_ref_traceability(phase_data, prefix, errors)
    _validate_content_filled(phase_data, prefix, errors)
    _validate_unit_economics_traceability(phase_data, prefix, warnings)


def validate_roadmap_data(data: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []

    # 1. Проверка metadata
    _validate_metadata(data, errors)

    # 2. Проверка наличия phases
    phases = data.get("phases", {})
    if not isinstance(phases, dict) or not phases:
        errors.append("CRITICAL: 'phases' отсутствует или пуст.")
        return False, errors, warnings

    # 3. Проверка обязательных фаз
    missing_phases = _REQUIRED_PHASES - set(phases.keys())
    if missing_phases:
        errors.append(
            f"CRITICAL: Отсутствуют обязательные фазы: {sorted(missing_phases)}"
        )

    # 4. Проверка каждой фазы
    for phase_id, phase_data in phases.items():
        _validate_phase(phase_id, phase_data, errors, warnings)

    is_valid = len(errors) == 0
    return is_valid, errors, warnings
