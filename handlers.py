from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
import aiohttp
from datetime import datetime
from config import WEATHER_API_KEY, CALORIES_API_KEY

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


# Хранилище для логов воды
user_water_logs = {}
# Хранилище для профилей пользователей
user_profiles = {}


# Команда /start
@router.message(Command('start'))
async def cmd_start(message: Message):
    await message.reply(
        "Привет! Я бот для расчёта нормы воды, калорий и трекинга активности.\nВведите /help для получения списка команд.")


# Команда /help
@router.message(Command('help'))
async def cmd_help(message: Message):
    await message.reply("Команды:\n"
                        "/set_profile - Настроить профиль\n"
                        "/log_water <количество> - Логировать воду\n"
                        "/log_food <название продукта> - Логировать еду\n"
                        "/check_progress - Проверить прогресс\n"
                        "/log_workout <тип тренировки> <время (мин)> - Логировать тренировку")


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


# Обработка команды /log_workout
@router.message(Command('log_workout'))
async def log_workout(message: Message):
    try:
        # Разделяем команду и аргументы
        args = message.text.split()
        if len(args) < 3:
            raise ValueError("Укажите тип тренировки и время в минутах.")

        workout_type = " ".join(args[1:-1])  # Тип тренировки - всё, что между первым и последним аргументами
        time_spent = int(args[-1])  # Время тренировки - последний аргумент

        if time_spent <= 0:
            raise ValueError("Время тренировки должно быть положительным числом.")

        # Запрос калорий, сожжённых на тренировке
        async with aiohttp.ClientSession() as session:
            url = f"https://api.api-ninjas.com/v1/caloriesburned?activity={workout_type}&duration={time_spent}"
            headers = {"X-Api-Key": CALORIES_API}
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    calories_burned = data[0].get('calories_burned', 0)
                else:
                    raise ValueError("Ошибка при получении данных о тренировке.")

        # Расчёт воды на тренировке
        water_needed = (time_spent // 30) * 200  # 200 мл на каждые 30 минут тренировки
        await message.answer(
            f"🏋️‍♂️ {workout_type.capitalize()} {time_spent} минут — {calories_burned} ккал.\n"
            f"Дополнительно: выпейте {water_needed} мл воды."
        )
    except ValueError as e:
        await message.answer(f"Ошибка: {e}")


# Логирование воды
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
        if user_id not in user_profiles:
            await message.answer("Ваш профиль не настроен. Введите /set_profile для настройки.")
            return

        user_data = user_profiles.get(user_id, {})
        user_data['water_drunk'] = user_data.get('water_drunk', 0) + water
        remaining_water = max(0, user_data['total_water_norm'] - user_data['water_drunk'])
        await message.answer(
            f"Вы выпили {user_data['water_drunk']} мл воды.\n"
            f"Осталось выпить: {remaining_water} мл до выполнения нормы."
        )
    except ValueError as e:
        await message.answer(f"Ошибка: {e}")

# Логирование еды
@router.message(Command('log_food'))
async def log_food(message: Message, state: FSMContext):
    try:
        args = message.text.split()
        if len(args) < 2:
            raise ValueError("Укажите название продукта.")
        product_name = " ".join(args[1:])

        # Запрос информации о продукте
        async with aiohttp.ClientSession() as session:
            url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&search_terms={product_name}&json=true"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    products = data.get('products', [])
                    if products:
                        first_product = products[0]
                        food_name = first_product.get('product_name', 'Неизвестно')
                        calories = first_product.get('nutriments', {}).get('energy-kcal_100g', 0)
                        if calories == 0:
                            await message.answer(f"Не удалось найти калорийность для продукта '{food_name}'.")
                            return
                        await message.answer(f"🍌 {food_name} — {calories} ккал на 100 г. Сколько грамм вы съели?")
                        await state.set_state(ProfileStates.waiting_for_food_amount)
                        await state.update_data(calories=calories)
                    else:
                        await message.answer(f"Продукт '{product_name}' не найден.")
                else:
                    raise ValueError("Ошибка при запросе данных о продукте.")
    except ValueError as e:
        await message.answer(f"Ошибка: {e}")

# Обработка количества съеденного продукта
@router.message(ProfileStates.waiting_for_food_amount)
async def process_food_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError("Количество продукта должно быть положительным числом.")

        # Получаем данные из состояния
        user_data = await state.get_data()
        calories_per_100g = user_data['calories']

        # Считаем общее количество калорий
        total_calories = (calories_per_100g * amount) / 100
        user_id = message.from_user.id

        if user_id not in user_profiles:
            await message.answer("Ваш профиль не настроен. Введите /set_profile для настройки.")
            return

        user_data = user_profiles[user_id]
        user_data['calories_consumed'] += total_calories

        # Считаем, сколько осталось до нормы
        remaining_calories = max(0, user_data['calories'] - user_data['calories_consumed'])

        # Обновляем профиль пользователя
        user_profiles[user_id] = user_data
        await message.answer(
            f"Вы съели {total_calories} ккал.\n"
            f"Осталось до нормы: {remaining_calories} ккал."
        )
    except ValueError as e:
        await message.answer(f"Ошибка: {e}")