from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
import aiohttp
from datetime import datetime
from config import WEATHER_API_KEY, CALORIES_API_KEY  # Подключаем ключи API

API_KEY = WEATHER_API_KEY  # Ключ API для получения данных о погоде
CALORIES_API_KEY = CALORIES_API_KEY  # Ключ API для расчёта сожжённых калорий
router = Router()

# Структура данных пользователей
users_data = {}

# Состояния пользователя
class ProfileStates(StatesGroup):
    waiting_for_weight = State()
    waiting_for_height = State()
    waiting_for_age = State()
    waiting_for_activity_level = State()
    waiting_for_city = State()
    waiting_for_food_amount = State()

# Команда /start
@router.message(Command('start'))
async def cmd_start(message: Message):
    await message.reply("Привет! Я бот для расчёта нормы воды, калорий и трекинга активности.\nВведите /help для получения списка команд.")

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

# Обработка веса
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

# Обработка роста
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

# Обработка возраста
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

# Обработка уровня активности
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
        await message.answer(f"Неверный формат уровня активности. Попробуйте еще раз: {e}")# Обработка города
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
        'last_update': datetime.now(),
        'calories_consumed': 0
    })

    # Сохраняем данные пользователя
    users_data[message.from_user.id] = user_data

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
        if user_id not in users_data:
            await message.answer("Ваш профиль не настроен. Введите /set_profile для настройки.")
            return
        user_data = users_data[user_id]
        user_data['logged_water'] = user_data.get('logged_water', 0) + water
        remaining_water = max(0, user_data['total_water_norm'] - user_data['logged_water'])
        await message.answer(
            f"Вы выпили {user_data['logged_water']} мл воды.\n"
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

# Логирование тренировок
@router.message(Command('log_workout'))
async def log_workout(message: Message):
    try:
        args = message.text.split()
        if len(args) < 3:
            raise ValueError("Укажите тип тренировки и время в минутах.")
        workout_type = " ".join(args[1:-1])
        workout_time = int(args[-1])
        if workout_time <= 0:
            raise ValueError("Время тренировки должно быть положительным числом.")

        user_id = message.from_user.id
        if user_id not in users_data:
            await message.answer("Ваш профиль не настроен. Введите /set_profile для настройки.")
            return

        user_data = users_data[user_id]
        # Пример расчета сожженных калорий на основе типа тренировки
        calories_burned = workout_time * 8  # Примерный коэффициент для тренировки
        user_data['burned_calories'] = user_data.get('burned_calories', 0) + calories_burned

        # Логируем тренировку
        workout_log = {
            'type': workout_type,
            'duration': workout_time,
            'calories_burned': calories_burned,
            'timestamp': datetime.now()
        }
        if 'workout_logs' not in user_data:
            user_data['workout_logs'] = []
        user_data['workout_logs'].append(workout_log)

        users_data[user_id] = user_data

        await message.answer(f"Тренировка '{workout_type}' длительностью {workout_time} мин. "
                             f"Сожжено {calories_burned} калорий.")
    except ValueError as e:
        await message.answer(f"Ошибка: {e}")