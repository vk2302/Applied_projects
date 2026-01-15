import re
from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.db.memory import get_profile, water_log
from app.utils.water_rate import calc_daily_water_ml, format_ml

router = Router()


def parse_water_amount_ml(text: str) -> int | None:
    t = text.strip().lower().replace(",", ".")
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(ml|мл|l|л)?", t)
    if not m:
        return None

    value = float(m.group(1))
    unit = m.group(2) or "ml"
    if unit in {"l", "л"}:
        return int(round(value * 1000))
    return int(round(value))


@router.message(Command("log_water"))
async def log_water_cmd(message: Message):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Введите команду /log_water, затем численное значение миллилитров, или число литров + буква L")
        return

    amount_ml = parse_water_amount_ml(parts[1])
    if amount_ml is None or amount_ml < 0:
        await message.answer("Данные невалидны. Укажите, например, /log_water 250 или /log_water 0.25L")
        return

    user_id = message.from_user.id
    profile = get_profile(user_id)
    if not profile:
        await message.answer("Сначала необходимо настроить профиль: /set_profile")
        return

    today = datetime.now().date()
    consumed_today = water_log(user_id, today, amount_ml)

    goal_ml = calc_daily_water_ml(
        weight_kg=int(profile["weight_kg"]),
        activity_min=int(profile["activity_min"]),
        temperature_c=None,
    )

    remaining_ml = max(0, goal_ml - consumed_today)

    await message.answer(
        f"Добавлено: {format_ml(amount_ml)}\n"
        f"Сегодня выпито: {format_ml(consumed_today)}\n"
        f"Цель: {format_ml(goal_ml)}\n"
        f"Осталось: {format_ml(remaining_ml)}"
    )
