def calc_default_calorie_goal(*,weight_kg: int,height_cm: int,age: int,activity_min: int,) -> int:
    cal = 10 * weight_kg + 6.25 * height_cm - 5 * age
    if activity_min < 30:
        cal += 200
    elif activity_min < 60:
        cal += 300
    else:
        cal += 400

    return int(round(cal))


