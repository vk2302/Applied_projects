from datetime import datetime

import aiohttp
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.config import settings
from app.db.memory import get_profile, get_water_consumed, get_food_kcal, get_workout_totals
from app.services.openweather import get_current_temp_c_by_city
from app.utils.water_rate import calc_daily_water_ml, format_ml

router = Router()

@router.message(Command("check_progress"))
async def check_progress(message: Message, http: aiohttp.ClientSession):
    user_id = message.from_user.id
    profile = get_profile(user_id)
    if not profile:
        await message.answer("Пожалуйста, сначала настройте профиль: /set_profile")
        return

    today = datetime.now().date()

    temperature_c = None
    if settings.OPENWEATHER_API_KEY:
        try:
            w = await get_current_temp_c_by_city(
                http,
                city=str(profile["city"]),
                api_key=settings.OPENWEATHER_API_KEY,
            )
            temperature_c = w.temp_c
        except Exception:
            temperature_c = None

    consumed_water_ml = get_water_consumed(user_id, today)
    burned_kcal_today, extra_workout_water_ml = get_workout_totals(user_id, today)

    base_water_goal_ml = calc_daily_water_ml(
        weight_kg=int(profile["weight_kg"]),
        activity_min=int(profile["activity_min"]),
        temperature_c=temperature_c,
    )
    water_goal_ml = base_water_goal_ml + extra_workout_water_ml
    water_remaining_ml = max(0, water_goal_ml - consumed_water_ml)

    consumed_kcal_today = get_food_kcal(user_id, today)
    calorie_goal = int(profile["calorie_goal"])

    net_kcal = round(consumed_kcal_today - burned_kcal_today, 1)
    remaining_to_goal = round(calorie_goal - net_kcal, 1)

    date_str = today.strftime("%d.%m.%Y")

    if remaining_to_goal >= 0:
        remaining_line = f"Вам осталось до цели {remaining_to_goal} ккал."
    else:
        remaining_line = f"Перебор относительно цели: {abs(remaining_to_goal)} ккал."

    weather_line = ""
    if temperature_c is not None:
        weather_line = f"\n(Температура в {profile['city']}: {temperature_c:.1f}°C)"

    await message.answer(
        f"Прогресс за {date_str}:{weather_line}\n\n"
        "Вода:\n"
        f"- Выпито: {format_ml(consumed_water_ml)} из {format_ml(water_goal_ml)}.\n"
        f"- Осталось: {format_ml(water_remaining_ml)}.\n\n"
        "Калории:\n"
        f"- Потреблено: {round(consumed_kcal_today, 1)} ккал из {calorie_goal} ккал.\n"
        f"- Сожжено: {burned_kcal_today} ккал.\n"
        f"- Баланс: {net_kcal} ккал.\n"
        f"{remaining_line}"
    )
