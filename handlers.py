from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
import aiohttp

router = Router()

# Словарь для хранения данных пользователей
users = {}

# Обработчик команды /start
@router.message(Command('start'))
async def cmd_start(message: Message):
    await message.reply("Привет! Я твой бот для расчета нормы воды, калорий и трекинга активности. \nВведи /help для "
                        "получения списка доступных команд.")

# Обработчик команды /help
@router.message(Command('help'))
async def cmd_help(message: Message):
    await message.reply(
        'Команды:\n'
        '/set_profile - Настроить профиль\n'
        '/log_water <количество> - Логировать воду\n'
        '/log_food <название продукта> - Логировать еду\n'
        '/log_workout <тип тренировки> <время (мин)> - Логировать тренировку\n'
        '/check_progress - Проверить прогресс\n'
    )


# Обработчик команды /set_profile
@router.message(Command('set_profile'))
async def set_profile(message: Message, state: FSMContext):
    await message.reply("Введите ваш вес (в кг):")
    await state.set_state('weight')


@router.message(StateFilter(state='weight'))
async def process_weight(message: Message, state: FSMContext):
    weight = int(message.text)
    await state.update_data(weight=weight)
    await message.reply("Введите ваш рост (в см):")
    await state.set_state('height')


@router.message(StateFilter(state='height'))
async def process_height(message: Message, state: FSMContext):
    height = int(message.text)
    await state.update_data(height=height)
    await message.reply("Введите ваш возраст:")
    await state.set_state('age')


@router.message(StateFilter(state='age'))
async def process_age(message: Message, state: FSMContext):
    age = int(message.text)
    await state.update_data(age=age)
    await message.reply("Сколько минут активности у вас в день?")
    await state.set_state('activity')


@router.message(StateFilter(state='activity'))
async def process_activity(message: Message, state: FSMContext):
    activity = int(message.text)
    await state.update_data(activity=activity)
    await message.reply("В каком городе вы находитесь?")
    await state.set_state('city')


@router.message(StateFilter(state='city'))
async def process_city(message: Message, state: FSMContext):
    city = message.text
    user_data = await state.get_data()

    weight = user_data['weight']
    height = user_data['height']
    age = user_data['age']
    activity = user_data['activity']

    water_goal = weight * 30 + (500 * (activity // 30))  # Рассчитываем норму воды
    calorie_goal = 10 * weight + 6.25 * height - 5 * age  # Рассчитываем норму калорий

    users[message.from_user.id] = {
        "weight": weight,
        "height": height,
        "age": age,
        "activity": activity,
        "city": city,
        "water_goal": water_goal,
        "calorie_goal": calorie_goal,
        "logged_water": 0,
        "logged_calories": 0,
        "burned_calories": 0
    }

    await message.reply("Ваш профиль установлен.")