from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
import aiohttp
from datetime import datetime
from config import WEATHER_API_KEY, CALORIES_API_KEY

# Ключи API
API_KEY = WEATHER_API_KEY
CALORIES_API = CALORIES_API_KEY

router = Router()

# Состояния пользователя
class ProfileStates(StatesGroup):
    waiting_for_weight = State()
    waiting_for_height = State()
    waiting_for_age = State()
    waiting_for_activity_level = State()
    waiting_for_city = State()
    waiting_for_food_amount = State()

# Хранилище для профилей пользователей
user_profiles = {}

# Команда /start
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply(
        "Привет! Я бот для расчёта нормы воды, калорий и трекинга активности.\n"
        "Введите /help для получения списка команд."
    )

# Команда /help
@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.reply(
        "Команды:\n"
        "/set_profile - Настроить профиль\n"
        "/log_water <количество> - Логировать воду\n"
        "/log_food <название продукта> - Логировать еду\n"
        "/check_progress - Проверить прогресс\n"
        "/log_workout <тип тренировки> <время (мин)> - Логировать тренировку"
    )

# Настройка профиля
@router.message(Command("set_profile"))
async def set_profile(message: Message, state: FSMContext):
    await state.set_state(ProfileStates.waiting_for_weight)
    await message.answer("Введите свой вес в килограммах:")

@router.message(ProfileStates.waiting_for_weight)
async def process_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text)
        if weight <= 0:
            raise ValueError("Вес должен быть положительным числом")
        await state.update_data(weight=weight)
        await state.set_state(ProfileStates.waiting_for_height)
        await message.answer("Теперь введите свой рост в сантиметрах:")
    except ValueError:
        await message.answer("Ошибка: введите корректное значение веса.")

@router.message(ProfileStates.waiting_for_height)
async def process_height(message: Message, state: FSMContext):
    try:
        height = int(message.text)
        if height <= 0:
            raise ValueError("Рост должен быть положительным числом")
        await state.update_data(height=height)
        await state.set_state(ProfileStates.waiting_for_age)
        await message.answer("Введите ваш возраст:")
    except ValueError:
        await message.answer("Ошибка: введите корректное значение роста.")

@router.message(ProfileStates.waiting_for_age)
async def process_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        if age <= 0 or age > 120:
            raise ValueError("Возраст должен быть положительным числом и меньше 121 года")
        await state.update_data(age=age)
        await state.set_state(ProfileStates.waiting_for_activity_level)
        await message.answer("Сколько минут физической активности у вас в среднем за день?")
    except ValueError:
        await message.answer("Ошибка: введите корректное значение возраста.")

@router.message(ProfileStates.waiting_for_activity_level)
async def process_activity_level(message: Message, state: FSMContext):
    try:
        activity_level = int(message.text)
        if activity_level < 0:
            raise ValueError("Уровень активности должен быть неотрицательным числом")
        await state.update_data(activity_level=activity_level)
        await state.set_state(ProfileStates.waiting_for_city)
        await message.answer("Введите город вашего проживания:")
    except ValueError:
        await message.answer("Ошибка: введите корректное значение уровня активности.")

@router.message(ProfileStates.waiting_for_city)
async def process_city(message: Message, state: FSMContext):
    city = message.text.strip().title()
    user_data = await state.get_data()

    try:
        async with aiohttp.ClientSession() as session:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
            async with session.get(url) as resp:
                if resp.status == 200:
                    weather_data = await resp.json()
                    temperature = weather_data['main']['temp']
                else:
                    raise ValueError("Город не найден. Проверьте корректность ввода.")
    except Exception:
        await message.answer("Ошибка при получении данных о погоде. Попробуйте снова.")
        return

    base_water_norm = user_data['weight'] * 30
    activity_bonus = (user_data['activity_level'] // 30) * 500
    hot_weather_bonus = 500 if temperature > 25 else 0
    total_water_norm = base_water_norm + activity_bonus + hot_weather_bonus
    calories = 10 * user_data['weight'] + 6.25 * user_data['height'] - 5 * user_data['age']

    user_data.update({
        'city': city,
        'total_water_norm': total_water_norm,
        'calories': calories,
        'last_update': datetime.now(),
        'calories_consumed': 0
    })

    user_profiles[message.from_user.id] = user_data
    await state.clear()
    await message.answer(
        f"Ваш профиль успешно сохранен!\n"
        f"Суточная норма воды: {total_water_norm:.1f} мл.\n"
        f"Базовая норма калорий: {calories:.1f} ккал."
    )

# Логирование тренировки
@router.message(Command("log_workout"))
async def log_workout(message: Message):
    try:
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            raise ValueError("Укажите тип тренировки и время в минутах.")

        workout_type = args[1]
        time_spent = int(args[2])

        if time_spent <= 0:
            raise ValueError("Время тренировки должно быть положительным числом.")

        async with aiohttp.ClientSession() as session:
            url = f"https://api.api-ninjas.com/v1/caloriesburned?activity={workout_type}&duration={time_spent}"
            headers = {"X-Api-Key": CALORIES_API}
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    calories_burned = data[0].get('total_calories', 0) if data else 0
                else:
                    raise ValueError("Ошибка при получении данных о тренировке.")

        water_needed = (time_spent // 30) * 200
        await message.answer(
            f"🏋️‍♂️ {workout_type.capitalize()} ({time_spent} минут) — {calories_burned:.1f} ккал.\n"
            f"Дополнительно: выпейте {water_needed} мл воды."
        )
    except ValueError as e:
        await message.answer(f"Ошибка: {e}")