from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
import aiohttp
import logging
from datetime import datetime
from config import WEATHER_API_KEY

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
router = Router()
storage = MemoryStorage()

API_KEY = WEATHER_API_KEY

# Состояния пользователя
class ProfileStates(StatesGroup):
    waiting_for_weight = State()
    waiting_for_height = State()
    waiting_for_age = State()
    waiting_for_activity_level = State()
    waiting_for_city = State()
    waiting_for_food_weight = State()

# Хранилища данных
user_profiles = {}
user_water_logs = {}
user_food_logs = {}

# Функция для получения информации о еде через OpenFoodFacts API
async def get_food_info(product_name):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&search_terms={product_name}&json=true"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                products = data.get('products', [])
                if products:
                    first_product = products[0]
                    return {
                        'name': first_product.get('product_name', 'Неизвестно'),
                        'calories': first_product.get('nutriments', {}).get('energy-kcal_100g', 0)
                    }
    return None

# Команда /start
@router.message(Command('start'))
async def cmd_start(message: Message):
    logging.info(f"Получено сообщение: {message.text}")
    await message.reply(
        "Привет!\nЯ бот для расчёта нормы воды, калорий и трекинга активности.\n"
        "Введите /help для получения списка команд."
    )

# Команда /help
@router.message(Command('help'))
async def cmd_help(message: Message):
    logging.info(f"Получено сообщение: {message.text}")
    await message.reply(
        "Команды:\n"
        "/set_profile - Настроить профиль\n"
        "/log_water <количество> - Логировать воду\n"
        "/log_food <название продукта> - Логировать еду\n"
        "/check_progress - Проверить прогресс"
    )

# Настройка профиля
@router.message(Command('set_profile'))
async def set_profile(message: Message, state: FSMContext):
    logging.info(f"Получено сообщение: {message.text}")
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
        await message.answer(f"Ошибка: {e}")

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
        await message.answer(f"Ошибка: {e}")

@router.message(ProfileStates.waiting_for_age)
async def process_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        if age <= 0 or age > 120:
            raise ValueError("Возраст должен быть в пределах от 1 до 120")
        await state.update_data(age=age)
        await state.set_state(ProfileStates.waiting_for_activity_level)
        await message.answer("Сколько минут физической активности у вас в среднем за день?")
    except ValueError as e:
        await message.answer(f"Ошибка: {e}")

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
        await message.answer(f"Ошибка: {e}")

@router.message(ProfileStates.waiting_for_city)
async def process_city(message: Message, state: FSMContext):
    city = message.text.strip().title()
    user_data = await state.get_data()

    async with aiohttp.ClientSession() as session:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
        async with session.get(url) as resp:
            weather_data = await resp.json()
            temperature = weather_data['main']['temp']

    base_water_norm = user_data['weight'] * 30
    activity_bonus = user_data['activity_level'] // 30 * 500
    hot_weather_bonus = 500 if temperature > 25 else 0
    total_water_norm = base_water_norm + activity_bonus + hot_weather_bonus

    calories = 10 * user_data['weight'] + 6.25 * user_data['height'] - 5 * user_data['age']
    user_profiles[message.from_user.id] = {
        'weight': user_data['weight'],
        'height': user_data['height'],
        'age': user_data['age'],
        'activity_level': user_data['activity_level'],
        'city': city,
        'total_water_norm': total_water_norm,
        'calories': calories,
    }

    await state.clear()
    await message.answer(
        f"Профиль сохранен!\nСуточная норма воды: {total_water_norm} мл.\n"
        f"Базовая норма калорий: {calories} ккал."
    )

# Логирование еды
@router.message(Command('log_food'))
async def log_food(message: Message, state: FSMContext):
    logging.info(f"Получено сообщение: {message.text}")
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Укажите название продукта. Пример: /log_food банан")
        return
    product_name = args[1]
    food_info = await get_food_info(product_name)

    if not food_info:
        await message.answer("Продукт не найден. Попробуйте указать точное название.")
        return

    await state.update_data(food_name=food_info['name'], food_calories=food_info['calories'])
    await state.set_state(ProfileStates.waiting_for_food_weight)
    await message.answer(
        f"🍴 {food_info['name']} — {food_info['calories']} ккал на 100 г. Сколько грамм вы съели?"
    )

@router.message(ProfileStates.waiting_for_food_weight)
async def process_food_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text)
        if weight <= 0:
            raise ValueError("Вес должен быть положительным числом.")
        data = await state.get_data()
        calories = (data['food_calories'] / 100) * weight
        user_food_logs.setdefault(message.from_user.id, []).append({
            'name': data['food_name'],
            'weight': weight,
            'calories': calories
        })
        await state.clear()
        await message.answer(f"Записано: {calories:.2f} ккал из {data['food_name']}.")
    except ValueError as e:
        await message.answer(f"Ошибка: {e}")