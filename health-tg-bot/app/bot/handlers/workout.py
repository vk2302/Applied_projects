from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.db.memory import get_profile, add_workout_entry
from app.utils.workouts import calc_workout_kcal, calc_workout_extra_water_ml

router = Router()

@router.message(Command("log_workout"))
async def log_workout(message: Message):
    parts = (message.text or "").split()
    if len(parts) < 3:
        await message.answer("Ожидается команда: /log_workout <тип> <минуты>")
        return

    workout_type = parts[1].strip()
    try:
        minutes = int(parts[2])
    except ValueError:
        await message.answer("Пожалуйста, введите численное значение больше нуля.")
        return

    if minutes <= 0:
        await message.answer("Введите длительность тренировки больше нуля.")
        return

    user_id = message.from_user.id
    profile = get_profile(user_id)
    if not profile:
        await message.answer("Пожалуйста, сначала настройте профиль: /set_profile")
        return

    weight_kg = int(profile["weight_kg"])

    kcal = calc_workout_kcal(workout_type=workout_type, minutes=minutes, weight_kg=weight_kg)
    extra_water_ml = calc_workout_extra_water_ml(workout_type=workout_type, minutes=minutes)

    today = datetime.now().date()
    total_kcal_today, total_extra_water_today = add_workout_entry(
        user_id,
        today,
        {
            "workout_type": workout_type,
            "minutes": minutes,
            "kcal": kcal,
            "extra_water_ml": extra_water_ml,
        },
    )

    await message.answer(
        f"Вы отметили тренировку {workout_type}, Ваша активность длилась {minutes} минут — это {kcal} ккал.\n"
        f"Очень важно для Вашего самочувствия и продуктивности: выпейте доп. {extra_water_ml} мл воды к стандартному уровню.\n\n"
        f"Сегодня сожжено {total_kcal_today} ккал благодаря тренировкам\n"
        f"Дополнительно воды: {total_extra_water_today} мл"
    )
