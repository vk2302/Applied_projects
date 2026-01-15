import math
from typing import Literal

Intensity = Literal["light", "moderate", "intense"]

WORKOUT_MET: dict[str, float] = {
    "бег": 9.8,
    "run": 9.8,
    "running": 9.8,

    "ходьба": 3.3,
    "walk": 3.3,
    "walking": 3.3,

    "велосипед": 7.5,
    "вел": 7.5,
    "cycling": 7.5,
    "bike": 7.5,

    "плавание": 8.0,
    "swim": 8.0,
    "swimming": 8.0,

    "силовая": 6.0,
    "тренажерный": 6.0,
    "зал": 6.0,
    "gym": 6.0,
    "strength": 6.0,

    "йога": 3.0,
    "yoga": 3.0,

    "hiit": 10.0,
    "интервальная": 10.0,
}


WORKOUT_INTENSITY: dict[str, Intensity] = {
    "ходьба": "light", "walk": "light", "walking": "light", "йога": "light", "yoga": "light",
    "велосипед": "moderate", "cycling": "moderate", "bike": "moderate", "зал": "moderate", "gym": "moderate",
    "бег": "intense", "run": "intense", "running": "intense", "плавание": "intense", "swimming": "intense", "hiit": "intense",
}


def normalize_workout_type(raw: str) -> str:
    return raw.strip().lower()


def calc_workout_kcal(workout_type: str, minutes: int, weight_kg: int) -> int:
    if minutes <= 0:
        raise ValueError("minutes must be > 0")
    if weight_kg <= 0:
        raise ValueError("weight_kg must be > 0")

    key = normalize_workout_type(workout_type)
    met = WORKOUT_MET.get(key, 6.0) 
    hours = minutes / 60.0
    kcal = met * weight_kg * hours
    return int(round(kcal))


def calc_workout_extra_water_ml(workout_type: str, minutes: int) -> int:
    key = normalize_workout_type(workout_type)
    intensity: Intensity = WORKOUT_INTENSITY.get(key, "moderate")

    per30 = {"light": 150, "moderate": 200, "intense": 300}[intensity]
    blocks = math.ceil(minutes / 30)
    return blocks * per30
