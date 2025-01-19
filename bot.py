from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
import aiohttp
from datetime import datetime
from config import WEATHER_API_KEY

API_KEY = WEATHER_API_KEY
router = Router()
storage = MemoryStorage()

# Состояния пользователя
class ProfileStates(StatesGroup):
    waiting_for_weight = State()
    waiting_for_height = State()
    waiting_for_age = State()
    waiting_for_activity_level = State()
    waiting_for_city = State()

# Хранилище для логов воды
user_water_logs = {}

# Команда /start
@router.message(Command('start'))
async def cmd_start(message: Message):
    await message.reply(
        "Привет!\nЯ бот для расчёта нормы воды, калорий и трекинга активности.\n"
        "Введите /help для получения списка команд."
    )

# Команда /help
@router.message(Command('help'))
async def cmd_help(message: Message):
    await message.reply(
        "Команды:\n"
        "/set_profile - Настроить профиль\n"
        "/log_water <количество> - Логировать воду\n"
        "/check_progress - Проверить прогресс"
    )

# Настройка профиля
@router.message(Command('set_profile'))
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
    except ValueError as e:
        await message.answer(f"Неверный формат веса. Попробуйте еще раз: {e}")

@router.message(ProfileStates.waiting_for_height)
async def process_height(message: Message, state: FSMContext):
    try:
        height = int(message.text)
        if height <= 0:
            raise ValueError("Рост должен быть положительным числом")
        await state.update_data(height=height)
        await state.set_state(ProfileStates.waiting_for_age)
        await message.answer("Отлично! Теперь введите свой возраст:")
    except ValueError as e:
        await message.answer(f"Неверный формат роста. Попробуйте еще раз: {e}")

@router.message(ProfileStates.waiting_for_age)
async def process_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        if age <= 0 or age > 120:
            raise ValueError("Возраст должен быть положительным числом и меньше 121 года")
        await state.update_data(age=age)
        await state.set_state(ProfileStates.waiting_for_activity_level)
        await message.answer("Сколько минут физической активности у вас в среднем за день?")
    except ValueError as e:
        await message.answer(f"Неверный формат возраста. Попробуйте еще раз: {e}")

@router.message(ProfileStates.waiting_for_activity_level)
async def process_activity_level(message: Message, state: FSMContext):
    try:
        activity_level = int(message.text)
        if activity_level < 0:
            raise ValueError("Уровень активности должен быть неотрицательным числом")
        await state.update_data(activity_level=activity_level)
        await state.set_state(ProfileStates.waiting_for_city)
        await message.answer("Наконец, напишите город вашего проживания:")
    except ValueError as e:
        await message.answer(f"Неверный формат уровня активности. Попробуйте еще раз: {e}")

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
    except Exception as e:
        await message.answer(f"Ошибка при получении данных о погоде: {e}")
        return

    base_water_norm = user_data['weight'] * 30
    activity_bonus = user_data['activity_level'] // 30 * 500
    hot_weather_bonus = 500 if temperature > 25 else 0
    total_water_norm = base_water_norm + activity_bonus + hot_weather_bonus
    calories = 10 * user_data['weight'] + 6.25 * user_data['height'] - 5 * user_data['age']

    user_data.update({
        'city': city,
        'total_water_norm': total_water_norm,
        'calories': calories,
        'last_update': datetime.now()
    })
    user_water_logs[message.from_user.id] = {'water_drunk': 0, **user_data}

    await state.clear()
    await message.answer(
        f"Ваш профиль успешно сохранен!\n"
        f"Суточная норма воды: {total_water_norm} мл.\n"
        f"Базовая норма калорий: {calories} ккал."
    )

# Лог воды
@router.message(Command('log_water'))
async def log_water(message: Message):
    try:
        args = message.text.split()
        if len(args) < 2:
            raise ValueError("Укажите количество воды в мл.")
        water = int(args[1])
        if water <= 0:
            raise ValueError("Количество воды должно быть положительным числом.")

        user_id = message.from_user.id
        if user_id not in user_water_logs:
            await message.answer("Ваш профиль не настроен. Введите /set_profile для настройки.")
            return

        user_data = user_water_logs[user_id]
        user_data['water_drunk'] += water
        remaining_water = max(0, user_data['total_water_norm'] - user_data['water_drunk'])

        await message.answer(
            f"Вы выпили {user_data['water_drunk']} мл воды.\n"
            f"Осталось выпить: {remaining_water} мл до выполнения нормы."
        )
    except ValueError as e:
        await message.answer(f"Ошибка: {e}")