# в этом файле описаны команды, которые позволят при вводе /start показать пользователю все доступные ему опции для записи,
# а также инструкции, как правильно вводить информацию.
# Также написан код для кнопок, которые упростят и ускорят работу с ботом. Приводятся примеры заполнения данных.
# Для еды будет доступен выбор из нескольких продуктов (а не одного), наиболее похожих на записанный пользователем.
# Это повысит шансы расчета калорий по настоящему продукту, который человек употребил.


from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

@router.message(CommandStart())
@router.message(Command("help"))
async def start(message: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="Настроить профиль", callback_data="go:set_profile")
    kb.button(text="Прогресс", callback_data="go:check_progress")
    kb.button(text="Записать потребление воды, см пример", callback_data="go:log_water_example")
    kb.button(text="Записать потребление еды, см пример", callback_data="go:log_food_example")
    kb.adjust(1)

    text = (
        "Привет, я бот, помогающий тебе следить за твоим здоровьем, записывая твои цели по калориям и достижения, прогресс по питанию и тренировкам.\n\n"
        "Это команды, которые ты можешь вызвать:\n"
        "• /set_profile чтобы заполнить профиль (вес/рост/возраст/активность/город)\n"
        "• /log_water — зарегистрировать потребление воды в течение суток. Нужно указать численное значение в мл."
        "• /log_food — записать еду, необходимо указать название продукта\n"
        "• /log_workout — тренировка, нужно указать тип (бег, гимнастика), и продолжительность (целое число минут)\n"
        "• /check_progress позволяет посмотреть прогресс по калориям за день\n"
        "• /cancel — отмена ввода формы\n"
    )
    await message.answer(text, reply_markup=kb.as_markup())


@router.callback_query(lambda c: c.data and c.data.startswith("go:"))
async def go_buttons(callback):
    data = callback.data

    if data == "go:set_profile":
        await callback.message.answer("Ввести /set_profile")
    elif data == "go:check_progress":
        await callback.message.answer("Ввести /check_progress")
    elif data == "go:log_water_example":
        await callback.message.answer("Пример: /log_water 250")
    elif data == "go:log_food_example":
        await callback.message.answer("Пример: /log_food banana")

    await callback.answer()
