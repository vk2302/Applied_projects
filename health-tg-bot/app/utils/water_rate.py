def calc_daily_water_ml(
    *,
    weight_kg: int,
    activity_min: int,
    temperature_c: float | None = None,
) -> int:
    base_need = weight_kg * 30 if weight_kg > 0 else 0
    extra_activity = 500 * (activity_min / 30) if activity_min > 0 else 0

    extra_heat = 750 if (temperature_c is not None and temperature_c > 25) else 0
    return int(base_need + extra_activity + extra_heat)


def format_ml(value: int) -> str:
    return f"{int(value)} мл"

