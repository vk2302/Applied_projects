from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.states import ProfileStates
from app.db.memory import save_profile
from app.utils.calories import calc_default_calorie_goal

router = Router()


def _parse_int(text: str | None) -> int | None:
    if not text:
        return None
    t = text.strip().replace(",", ".")
    try:
        return int(float(t))
    except ValueError:
        return None


def _ask_prompt_for(state_name: str) -> str:
    prompts = {
        ProfileStates.weight_kg.state: "Введите Ваш вес (в кг):",
        ProfileStates.height_cm.state: "Введите Ваш рост (в см):",
        ProfileStates.age.state: "Введите Ваш возраст:",
        ProfileStates.activity_min.state: "Сколько минут в день Вы обычно (в среднем) занимаетесь спортом?",
        ProfileStates.city.state: "Где Вы живете? Укажите ближайший город (лучше использовать язык страны проживания)",
        ProfileStates.calorie_goal.state: ("Пожалуйста, напишите Вашу цель по калориям (опционально): число ккал или 'auto' (по умолчанию)"),
    }
    return prompts[state_name]


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отмена. Чтобы начать заново, введите команду /set_profile")


@router.message(Command("set_profile"))
async def set_profile_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(ProfileStates.weight_kg)
    await message.answer(_ask_prompt_for(ProfileStates.weight_kg.state))


@router.message(StateFilter(
    ProfileStates.weight_kg,
    ProfileStates.height_cm,
    ProfileStates.age,
    ProfileStates.activity_min,
    ProfileStates.city,
    ProfileStates.calorie_goal,
))

async def profile_form(message: Message, state: FSMContext):
    current_state = await state.get_state()
    text = message.text or ""

    if current_state == ProfileStates.weight_kg.state:
        val = _parse_int(text)
        if val is None or not (30 <= val <= 300):
            await message.answer("Пожалуйста, введите ваш корректный вес числом (пример: 80).")
            return
        await state.update_data(weight_kg=val)
        await state.set_state(ProfileStates.height_cm)
        await message.answer(_ask_prompt_for(ProfileStates.height_cm.state))
        return
    
    if current_state == ProfileStates.height_cm.state:
        val = _parse_int(text)
        if val is None or not (100 <= val <= 250):
            await message.answer("Пожалуйста, введите корректный рост числом (пример: 184).")
            return
        await state.update_data(height_cm=val)
        await state.set_state(ProfileStates.age)
        await message.answer(_ask_prompt_for(ProfileStates.age.state))
        return

    if current_state == ProfileStates.age.state:
        val = _parse_int(text)
        if val is None or not (6 <= val <= 120):
            await message.answer("Пожалуйста, введите корректный возраст числом (пример: 26).")
            return
        await state.update_data(age=val)
        await state.set_state(ProfileStates.activity_min)
        await message.answer(_ask_prompt_for(ProfileStates.activity_min.state))
        return

    if current_state == ProfileStates.activity_min.state:
        val = _parse_int(text)
        if val is None or not (0 <= val <= 600):
            await message.answer("Введите число минут вашей активности в день (пример: 45).")
            return
        await state.update_data(activity_min=val)
        await state.set_state(ProfileStates.city)
        await message.answer(_ask_prompt_for(ProfileStates.city.state))
        return

    if current_state == ProfileStates.city.state:
        city = text.strip()
        if len(city) < 2:
            await message.answer("Введите название (ближайшего к вам) города по-английски (пример: Moscow).")
            return
        await state.update_data(city=city)
        await state.set_state(ProfileStates.calorie_goal)
        await message.answer(_ask_prompt_for(ProfileStates.calorie_goal.state))
        return

    if current_state == ProfileStates.calorie_goal.state:
        raw = text.strip().lower()
        data = await state.get_data()

        if raw in {"auto", "авто", "-", "default", None}:
            goal = calc_default_calorie_goal(
                weight_kg=int(data["weight_kg"]),
                height_cm=int(data["height_cm"]),
                age=int(data["age"]),
                activity_min=int(data["activity_min"]),
            )
            mode = "auto"
        else:
            val = _parse_int(raw)
            if val is None or not (800 <= val <= 6000):
                await message.answer("Введите цель по ккал или напишите auto: тогда будет взято значение по умолчанию.")
                return
            goal = int(val)
            mode = "manual"

        profile = {
            "weight_kg": int(data["weight_kg"]),
            "height_cm": int(data["height_cm"]),
            "age": int(data["age"]),
            "activity_min": int(data["activity_min"]),
            "city": str(data["city"]),
            "calorie_goal": int(goal),
            "calorie_goal_mode": mode,
        }

        save_profile(message.from_user.id, profile)
        await state.clear()

        await message.answer(
            "Профиль сохранён\n\n"
            f"Вес: {profile['weight_kg']} кг\n"
            f"Рост: {profile['height_cm']} см\n"
            f"Возраст: {profile['age']}\n"
            f"Активность: {profile['activity_min']} мин/день\n"
            f"Город: {profile['city']}\n"
            f"Цель калорий: {profile['calorie_goal']} ккал ({profile['calorie_goal_mode']})\n"
        )
        return

    await message.answer("Что-то пошло не так. Начните заново: /set_profile")
    await state.clear()



