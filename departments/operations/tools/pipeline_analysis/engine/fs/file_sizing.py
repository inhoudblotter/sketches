import re
from pathlib import Path


def build_template_kb_by_path(
    raw_agents: list[dict], project_root: Path
) -> dict[str, float]:
    template_kb_by_path: dict[str, float] = {}
    for a in raw_agents:
        for path, contract in a.get("write_contracts", {}).items():
            tpl = project_root / contract
            if tpl.is_file():
                template_kb_by_path[path] = round(tpl.stat().st_size / 1024, 2)
    return template_kb_by_path


def _process_brace_pattern(r: str, project_root: Path) -> tuple[list[Path], int]:
    pattern = re.sub(r"\{[^}]+\}", "*", r)
    matches = list(project_root.glob(pattern))

    last_brace_idx = r.rfind("}")
    if last_brace_idx != -1:
        truncated = r[: last_brace_idx + 1]
        trunc_pattern = re.sub(r"\{[^}]+\}", "*", truncated)
        expected_len = len(list(project_root.glob(trunc_pattern)))
    else:
        expected_len = len(matches)

    return matches, expected_len


def _calculate_brace_file_kb(
    r: str,
    is_looped: bool,
    project_root: Path,
    template_kb_by_path: dict[str, float],
    is_optional: bool = False,
) -> tuple[float, float, int, bool]:
    total_add = 0.0
    looped_add = 0.0
    is_partial = False

    matches, expected_len = _process_brace_pattern(r, project_root)

    if not matches:
        if is_optional:
            return 0.0, 0.0, expected_len, False
        is_partial = True
        kb = template_kb_by_path.get(r, 0.0)
        if is_looped:
            looped_add += kb
        else:
            total_add += kb
        return total_add, looped_add, expected_len, is_partial

    if is_looped:
        looped_add += sum(m.stat().st_size for m in matches) / 1024
    else:
        sizes = sorted(m.stat().st_size for m in matches)
        p90_idx = int(len(sizes) * 0.9)
        total_add += sizes[p90_idx] / 1024

    return total_add, looped_add, expected_len, is_partial


def _calculate_glob_file_kb(
    r: str,
    is_looped: bool,
    project_root: Path,
    template_kb_by_path: dict[str, float],
    is_optional: bool = False,
) -> tuple[float, float, int, bool]:
    total_add = 0.0
    looped_add = 0.0
    is_partial = False

    matches = list(project_root.glob(r))
    if not matches:
        if is_optional:
            return 0.0, 0.0, 0, False
        is_partial = True
        kb = template_kb_by_path.get(r, 0.0)
        total_add += kb  # Original logic added it to total even if looped
        return total_add, looped_add, 0, is_partial

    expected_len = len(matches)
    if is_looped:
        looped_add += sum(m.stat().st_size for m in matches) / 1024
    else:
        total_add += sum(m.stat().st_size for m in matches) / 1024

    return total_add, looped_add, expected_len, is_partial


def _calculate_exact_file_kb(
    r: str,
    project_root: Path,
    template_kb_by_path: dict[str, float],
    is_optional: bool = False,
) -> tuple[float, bool]:
    p = project_root / r
    if not p.exists():
        if is_optional:
            return 0.0, False
        is_partial = True
        return template_kb_by_path.get(r, 0.0), is_partial
    return p.stat().st_size / 1024, False


def _calculate_entry_kb(
    r: str,
    is_looped: bool,
    is_optional: bool,
    project_root: Path,
    template_kb_by_path: dict[str, float],
) -> tuple[float, float, int, bool]:
    if "{" in r:
        return _calculate_brace_file_kb(
            r, is_looped, project_root, template_kb_by_path, is_optional
        )
    if "*" in r:
        return _calculate_glob_file_kb(
            r, is_looped, project_root, template_kb_by_path, is_optional
        )
    t_add, partial = _calculate_exact_file_kb(
        r, project_root, template_kb_by_path, is_optional
    )
    return t_add, 0.0, 1, partial


def _calculate_file_list_kb(
    file_list: list[str],
    optional_list: list[str],
    looped_list: list[str],
    project_root: Path,
    template_kb_by_path: dict[str, float],
) -> tuple[float, int, int, bool]:
    if not file_list:
        return 0.0, 0, 0, False

    total = 0.0
    looped_totals = 0.0
    max_matches = 0
    unlooped_max_matches = 0
    is_partial = False

    for r in file_list:
        is_looped = r in looped_list
        is_optional = r in optional_list

        t_add, l_add, exp_len, partial = _calculate_entry_kb(
            r, is_looped, is_optional, project_root, template_kb_by_path
        )
        total += t_add
        looped_totals += l_add
        if partial:
            is_partial = True
        max_matches = max(max_matches, exp_len)
        if not is_looped:
            unlooped_max_matches = max(unlooped_max_matches, exp_len)

    total += looped_totals / max(1, unlooped_max_matches)
    return round(total, 2), max_matches, unlooped_max_matches, is_partial
