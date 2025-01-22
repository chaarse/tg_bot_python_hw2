from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
import aiohttp
import logging

from config import WEATHER_API_KEY, CALORIES_API_KEY

logger = logging.getLogger(__name__)

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

# Хранилище для пользователей
users = {}

# Команда /start
@router.message(Command('start'))
async def cmd_start(message: Message):
    logger.info(f"Получено сообщение: {message.text}")
    await message.reply("Привет! Я бот для расчёта нормы воды, калорий и трекинга активности.\nВведите /help для получения списка команд.")

# Команда /help
@router.message(Command('help'))
async def cmd_help(message: Message):
    logger.info(f"Получено сообщение: {message.text}")
    await message.reply("Команды:\n"
                        "/set_profile - Настроить профиль\n"
                        "/log_water <количество> - Логировать воду\n"
                        "/log_food <название продукта> - Логировать еду\n"
                        "/log_workout <тип тренировки> <время (мин)> - Логировать тренировку\n"
                        "/check_progress - Проверить прогресс")

# Настройка профиля
@router.message(Command('set_profile'))
async def set_profile(message: Message, state: FSMContext):
    logger.info(f"Получено сообщение: {message.text}")
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
        return  # Останавливаем выполнение, если ошибка в запросе

    base_water_norm = user_data['weight'] * 30
    activity_bonus = user_data['activity_level'] // 30 * 500
    hot_weather_bonus = 500 if temperature > 25 else 0
    total_water_norm = base_water_norm + activity_bonus + hot_weather_bonus
    calories = 10 * user_data['weight'] + 6.25 * user_data['height'] - 5 * user_data['age']

    # Обновляем или создаём профиль пользователя
    users[message.from_user.id] = {
        'weight': user_data['weight'],
        'height': user_data['height'],
        'age': user_data['age'],
        'activity': user_data['activity_level'],
        'city': city,
        'water_goal': total_water_norm,
        'calorie_goal': calories,
        'logged_water': 0,
        'logged_calories': 0,
        'burned_calories': 0
    }

    await state.clear()
    await message.answer(
        f"Ваш профиль успешно сохранен!\n"
        f"Суточная норма воды: {total_water_norm} мл.\n"
        f"Базовая норма калорий: {calories} ккал."
    )

# Лог воды
@router.message(Command('log_water'))
async def log_water(message: Message):
    logger.info(f"Получено сообщение: {message.text}")
    try:
        args = message.text.split()
        if len(args) < 2:
            raise ValueError("Укажите количество воды в мл.")
        water = int(args[1])
        if water <= 0:
            raise ValueError("Количество воды должно быть положительным числом.")

        user_id = message.from_user.id
        if user_id not in users:
            await message.answer("Ваш профиль не настроен. Введите /set_profile для настройки.")
            return

        user_data = users[user_id]
        user_data['logged_water'] += water
        remaining_water = max(0, user_data['water_goal'] - user_data['logged_water'])

        await message.answer(
            f"Вы выпили {user_data['logged_water']} мл воды.\n"
            f"Осталось выпить: {remaining_water} мл до выполнения нормы."
        )
    except ValueError as e:
        await message.answer(f"Ошибка: {e}")

# Лог еды
@router.message(Command('log_food'))
async def log_food(message: Message, state: FSMContext):
    logger.info(f"Получено сообщение: {message.text}")
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
                    else:await message.answer(f"Продукт '{product_name}' не найден.")
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

        user_data = await state.get_data()
        calories_per_100g = user_data['calories']
        total_calories = (calories_per_100g * amount) / 100
        user_id = message.from_user.id
        if user_id not in users:
            await message.answer("Ваш профиль не настроен. Введите /set_profile для настройки.")
            return

        user_data = users[user_id]
        user_data['logged_calories'] += total_calories
        remaining_calories = max(0, user_data['calorie_goal'] - user_data['logged_calories'])
        users[user_id] = user_data

        await state.clear()
        await message.answer(
            f"Вы съели {total_calories} ккал.\n"
            f"Осталось до нормы: {remaining_calories} ккал."
        )
    except ValueError as e:
        await message.answer(f"Ошибка: {e}")

# Лог тренировки
@router.message(Command("log_workout"))
async def log_workout(message: Message):
    logger.info(f"Получено сообщение: {message.text}")
    _, _, command_args = message.text.partition('/log_workout ')
    args = command_args.split()  # список аргументов

    if len(args) < 2:
        await message.answer("Неверный формат команды. Используйте: /log_workout <тип тренировки> <время в минутах>")
        return

    workout_type = ' '.join(args[:-1]).strip()  # тип тренировки
    time_spent_str = args[-1].strip()  # время тренировки

    if not time_spent_str.isdigit():
        await message.answer("Время тренировки должно быть целым положительным числом.")
        return

    time_spent = int(time_spent_str)
    if time_spent <= 0:
        await message.answer("Время тренировки должно быть больше нуля.")
        return

    async with aiohttp.ClientSession() as session:
        url = f"https://api.api-ninjas.com/v1/caloriesburned?activity={workout_type}&duration={time_spent}"
        headers = {"X-Api-Key": CALORIES_API}
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                calories_burned = data[0].get('total_calories', 0) if data else 0
            else:
                await message.answer("Ошибка при запросе данных о тренировке.")
                return

    # Расчет дополнительной нормы воды
    water_needed = (time_spent // 30) * 200

    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Ваш профиль не настроен. Введите /set_profile для настройки.")
        return

    # Обновляем данные пользователя
    user_data = users[user_id]
    user_data['burned_calories'] += calories_burned
    user_data['water_goal'] += water_needed  # Увеличиваем норму воды
    users[user_id] = user_data

    await message.answer(
        f"🏋️‍♂️ {workout_type.capitalize()} ({time_spent} минут) — {calories_burned:.1f} ккал.\n"
        f"Дополнительно: выпейте {water_needed} мл воды.\n\n"
        f'Дополнительные мл. воды после тренировки добавляются к вашей норме.'
    )

# Прогресс пользователя
@router.message(Command('check_progress'))
async def check_progress(message: Message):
    logger.info(f"Получено сообщение: {message.text}")
    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Ваш профиль не настроен. Введите /set_profile для настройки.")
        return

    user_data = users[user_id]

    water_logged = user_data['logged_water']
    water_goal = user_data['water_goal']
    water_remaining = max(0, water_goal - water_logged)

    calories_logged = user_data['logged_calories']
    calorie_goal = user_data['calorie_goal']
    calories_burned = user_data['burned_calories']
    calorie_balance = max(0, calorie_goal - calories_logged + calories_burned)

    await message.answer(
        f"📊 Прогресс:\n"
        f"Вода:\n"
        f"- Выпито: {water_logged} мл из {water_goal} мл.\n"
        f"- Осталось: {water_remaining} мл.\n\n"
        f"Калории:\n"
        f"- Потреблено: {calories_logged} ккал из {calorie_goal} ккал.\n"
        f"- Сожжено: {calories_burned} ккал.\n"
        f"- Баланс: {calorie_balance} ккал."
    )