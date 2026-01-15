from aiogram.fsm.state import State, StatesGroup


class ProfileStates(StatesGroup):
    weight_kg = State()
    height_cm = State()
    age = State()
    activity_min = State()
    city = State()
    calorie_goal = State()


class FoodLogStates(StatesGroup):
    choosing = State()
    grams = State()
    

    
