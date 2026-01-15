import re
from datetime import datetime

import aiohttp
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import settings
from app.db.memory import get_profile, add_food_entry
from app.services.openfoodfacts import search_food_candidates
from app.states import FoodLogStates

router = Router()



def _parse_grams(text: str | None) -> float | None:
    if not text:
        return None
    t = text.strip().lower().replace(",", ".")
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(g|гр|г)?", t)
    if not m:
        return None
    return float(m.group(1))


@router.message(Command("log_food"))
async def log_food_start(message: Message, state: FSMContext, http: aiohttp.ClientSession):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Необходимо ввести команду /log_food, затем название Вашего продукта: Вам будут предложены наиболее близкие варианты")
        return
    
    query = parts[1].strip()
    user_id = message.from_user.id
    profile = get_profile(user_id)
    if not profile:
        await message.answer("Необходимо сначала настроить профиль через команду /set_profile")
        return
    
    if len(query) < 2:
        await message.answer("Пожалуйста, введите более полное название")
        return

    await state.clear()

    try:
    candidates = await search_food_candidates(
        http,
        query=query,
        user_agent=settings.OFF_USER_AGENT,
        page_size=15,
        limit=5,
        timeout_s=10.0,
    )
    except (asyncio.TimeoutError, aiohttp.ClientError):
        await message.answer(
            "Сервис слишком долго ищет Ваш запрос. "
            "Напишите более короткое, понятное название."
            )
        return

    if not candidates:
        await message.answer("Не смог найти продукт, пожалуйста, попробуйте указать конкретный продукт из магазина (можно также попробовать на английском).")
        return

    if len(candidates) == 1:
        info = candidates[0]
        await state.set_state(FoodLogStates.grams)
        await state.update_data(food_name=info.name, kcal_per_100g=info.kcal_per_100g)
        await message.answer(f"{info.name} — {info.kcal_per_100g} ккал на 100 г. Укажите, сколько грамм вы употребили?")
        return

    await state.set_state(FoodLogStates.choosing)
    await state.update_data(candidates=[c.__dict__ for c in candidates])

    kb = InlineKeyboardBuilder()
    for i, c in enumerate(candidates):
        kb.button(
            text=f"{c.name} — {c.kcal_per_100g} ккал/100г",
            callback_data=f"food_pick:{i}",
        )
    kb.button(text="Не подходит", callback_data="food_pick:cancel")
    kb.adjust(1)

    await message.answer("Найдено несколько вариантов коммерческих продуктов, содержащих Ваш запрос. Пожалуйста, выберите наиболее подходящий:", reply_markup=kb.as_markup())


@router.callback_query(FoodLogStates.choosing, lambda c: c.data and c.data.startswith("food_pick:"))
async def food_pick(callback: CallbackQuery, state: FSMContext):
    pick = callback.data.split(":", 1)[1]

    if pick == "cancel":
        await state.clear()
        await callback.message.answer("Ок. Попробуйте уточнить Ваш запрос")
        await callback.answer()
        return

    try:
        idx = int(pick)
    except ValueError:
        await callback.answer("Не понял выбор", show_alert=True)
        return

    data = await state.get_data()
    candidates = data.get("candidates") or []

    if idx < 0 or idx >= len(candidates):
        await callback.answer("Не понял выбор", show_alert=True)
        return

    chosen = candidates[idx]
    await state.set_state(FoodLogStates.grams)
    await state.update_data(food_name=chosen["name"], kcal_per_100g=chosen["kcal_per_100g"])

    await callback.message.answer(
        f'{chosen["name"]} — {chosen["kcal_per_100g"]} ккал на 100 г. Сколько Вы употребили (укажите ответ в численном виде; сколько грамм)?'
    )
    await callback.answer()


@router.message(FoodLogStates.grams)
async def log_food_grams(message: Message, state: FSMContext):
    grams = _parse_grams(message.text)
    if grams is None or grams <= 0 or grams > 3000:
        await message.answer("Введите положительное число грамм.")
        return

    user_id = message.from_user.id
    profile = get_profile(user_id)
    if not profile:
        await message.answer("Сначала необходимо настроить профиль")
        await state.clear()
        return

    data = await state.get_data()
    name = str(data["food_name"])
    kcal_per_100g = float(data["kcal_per_100g"])

    kcal = round(grams * kcal_per_100g / 100.0, 1)
    today = datetime.now().date()

    total_today = add_food_entry(
        user_id,
        today,
        {"name": name, "grams": float(round(grams, 1)), "kcal": float(kcal)},
    )

    goal = int(profile["calorie_goal"])
    remaining = round(goal - total_today, 1)

    await state.clear()

    await message.answer(
        f"Употреблено: {kcal} ккал \n"
        f"Сегодня вы употребили: {round(total_today, 1)} ккал\n"
        f"Ваша цель: {goal} ккал\n"
        + (f"Осталось: {remaining} ккал" if remaining >= 0 else f"Излишне употреблено: {abs(remaining)} ккал")
    )
