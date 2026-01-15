from typing import TypedDict
from datetime import date

class UserProfile(TypedDict, total=False):
    weight_kg: int
    height_cm: int
    age: int
    activity_min: int
    city: str
    calorie_goal: int
    calorie_goal_mode: str


USER_PROFILES: dict[int, UserProfile] = {}


def save_profile(user_id: int, profile: UserProfile) -> None:
    USER_PROFILES[user_id] = profile


def get_profile(user_id: int) -> UserProfile | None:
    return USER_PROFILES.get(user_id)


def delete_profile(user_id: int) -> None:
    USER_PROFILES.pop(user_id, None)


water_dict: dict[int, dict[str, int]] = {}

def water_log(user_id: int, day: date, amount_ml: int) -> int:
    day_key = day.isoformat()
    user_days = water_dict.setdefault(user_id, {})
    user_days[day_key] = user_days.get(day_key, 0) + amount_ml
    return user_days[day_key]

def get_water_consumed(user_id: int, day: date) -> int:
    day_key = day.isoformat()
    return water_dict.get(user_id, {}).get(day_key, 0)

class FoodEntry(TypedDict):
    name: str
    grams: float
    kcal: float

FOOD_LOGS: dict[int, dict[str, list[FoodEntry]]] = {}

def add_food_entry(user_id: int, day: date, entry: FoodEntry) -> float:
    day_key = day.isoformat()
    user_days = FOOD_LOGS.setdefault(user_id, {})
    user_days.setdefault(day_key, []).append(entry)
    return get_food_kcal(user_id, day)

def get_food_kcal(user_id: int, day: date) -> float:
    day_key = day.isoformat()
    entries = FOOD_LOGS.get(user_id, {}).get(day_key, [])
    return float(sum(e["kcal"] for e in entries))

class WorkoutEntry(TypedDict):
    workout_type: str
    minutes: int
    kcal: int
    extra_water_ml: int


WORKOUT_LOGS: dict[int, dict[str, list[WorkoutEntry]]] = {}


def add_workout_entry(user_id: int, day: date, entry: WorkoutEntry) -> tuple[int, int]:
    day_key = day.isoformat()
    user_days = WORKOUT_LOGS.setdefault(user_id, {})
    user_days.setdefault(day_key, []).append(entry)
    return get_workout_totals(user_id, day)


def get_workout_totals(user_id: int, day: date) -> tuple[int, int]:
    day_key = day.isoformat()
    entries = WORKOUT_LOGS.get(user_id, {}).get(day_key, [])
    total_kcal = sum(e["kcal"] for e in entries)
    total_water = sum(e["extra_water_ml"] for e in entries)
    return int(total_kcal), int(total_water)

