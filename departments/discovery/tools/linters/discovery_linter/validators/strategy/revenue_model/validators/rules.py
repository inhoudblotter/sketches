from typing import Dict, Any, List

TARGET_TOTAL_SHARE = 100.0
TOLERANCE = 0.01


def _validate_shares(data: Dict[str, Any], errors: List[str]) -> None:
    try:
        shares = [
            float(s.get("expected_share_percent", 0))
            for s in data.get("revenue_streams", [])
        ]

        alt_streams = data.get("alternative_revenue_streams")
        if alt_streams:
            shares += [
                float(s.get("expected_share_percent", 0))
                for s in alt_streams
                if s.get("expected_share_percent")
            ]

        if sum(shares) != TARGET_TOTAL_SHARE and len(shares) > 0:
            errors.append(
                f"Total expected_share_percent should be {TARGET_TOTAL_SHARE}, got {sum(shares)}"
            )
    except Exception:
        pass


def _validate_scenario_bands(data: Dict[str, Any], errors: List[str]) -> None:
    scenario_bands = data.get("scenario_bands")
    if not scenario_bands:
        return
    try:
        worst = scenario_bands.get("worst", {})
        base = scenario_bands.get("base", {})
        best = scenario_bands.get("best", {})

        base_mau = float(base.get("target_mau", 0))
        base_arpu = float(base.get("blended_arpu_usd", 0))
        top_mau = float(data.get("target_mau", 0))
        top_arpu = float(data.get("blended_arpu_usd", 0))

        if abs(base_mau - top_mau) > TOLERANCE:
            errors.append(
                f"scenario_bands.base.target_mau ({base_mau}) must match top-level target_mau ({top_mau})"
            )
        if abs(base_arpu - top_arpu) > TOLERANCE:
            errors.append(
                f"scenario_bands.base.blended_arpu_usd ({base_arpu}) must match top-level blended_arpu_usd ({top_arpu})"
            )

        worst_mau = float(worst.get("target_mau", 0))
        best_mau = float(best.get("target_mau", 0))
        if not (worst_mau <= base_mau <= best_mau):
            errors.append(
                f"scenario_bands.target_mau must be non-decreasing worst<=base<=best, got {worst_mau}/{base_mau}/{best_mau}"
            )

        worst_arpu = float(worst.get("blended_arpu_usd", 0))
        best_arpu = float(best.get("blended_arpu_usd", 0))
        if not (worst_arpu <= base_arpu <= best_arpu):
            errors.append(
                f"scenario_bands.blended_arpu_usd must be non-decreasing worst<=base<=best, got {worst_arpu}/{base_arpu}/{best_arpu}"
            )

        for name in ("worst", "base", "best"):
            if not scenario_bands.get(name, {}).get("driver_ref"):
                errors.append(
                    f"scenario_bands.{name}.driver_ref is required (must reference market_context.md Scenario Drivers)"
                )
    except (TypeError, ValueError) as e:
        errors.append(f"scenario_bands validation error: {e}")


def validate_revenue_data(data: Dict[str, Any]) -> tuple[bool, List[str]]:
    from .. import RevenueModelConfig

    errors = []
    try:
        RevenueModelConfig.model_validate(data)
    except Exception as e:
        errors.append(str(e))

    _validate_shares(data, errors)
    _validate_scenario_bands(data, errors)

    return len(errors) == 0, errors


def _format_streams(data: Dict[str, Any]) -> None:
    for stream in data.get("revenue_streams", []):
        if "arpu_monthly_usd" in stream:
            stream["arpu_monthly_usd"] = float(stream["arpu_monthly_usd"])
        if "expected_share_percent" in stream:
            stream["expected_share_percent"] = float(stream["expected_share_percent"])


def _format_scenario_bands(data: Dict[str, Any]) -> None:
    scenario_bands = data.get("scenario_bands")
    if scenario_bands:
        for band in scenario_bands.values():
            if "target_mau" in band:
                band["target_mau"] = int(band["target_mau"])
            if "blended_arpu_usd" in band:
                band["blended_arpu_usd"] = float(band["blended_arpu_usd"])


def format_revenue_data(data: Dict[str, Any]) -> Dict[str, Any]:
    # Try to cast numbers
    try:
        if "target_mau" in data:
            data["target_mau"] = int(data["target_mau"])
        if "blended_arpu_usd" in data:
            data["blended_arpu_usd"] = float(data["blended_arpu_usd"])
        if "budget_constraint_usd" in data:
            data["budget_constraint_usd"] = float(data["budget_constraint_usd"])

        _format_streams(data)
        _format_scenario_bands(data)
    except Exception:
        pass
    return data
