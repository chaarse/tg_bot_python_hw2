from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
import aiohttp
from config import WEATHER_API_KEY


API_KEY = WEATHER_API_KEY

# Данные о пользователи
class ProfileStates(StatesGroup):
    waiting_for_weight = State()  # вес
    waiting_for_height = State()  # рост
    waiting_for_age = State()  # возраст
    waiting_for_activity_level = State()  # уровень активности
    waiting_for_city = State()  # название города


# Меню для выбора команд
menu_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add(types.KeyboardButton('/set_profile'),
                                                                    types.KeyboardButton('/log_water'),
                                                                    types.KeyboardButton('/log_food'),
                                                                    types.KeyboardButton('/log_workout'),
                                                                    types.KeyboardButton('/check_progress'))


@router.message(Command('start'))
async def cmd_start(message: Message, state: FSMContext):
    chat_id = str(message.from_user.id)
    async with state.proxy() as data:
        if 'last_interaction' in data and (
                datetime.datetime.now() - data['last_interaction']).total_seconds() < 86400:  # 24 часа
            await message.reply("Привет! Продолжаем работу (я обновляюсь каждый 24 часа).", reply_markup=menu_keyboard)
        else:
            await state.clear()
            await message.reply("Привет! Я бот для расчета нормы воды и калорий. Начнем с создания профиля?",
                                reply_markup=menu_keyboard)


@router.message(Command('help'))
async def cmd_help(message: Message):
    await message.reply(
        'Доступные команды:\n'
        '/set_profile - Настроить профиль\n'
        '/log_water <количество> - Логировать воду\n'
        '/log_food <название продукта> - Логировать еду\n'
        '/log_workout <тип тренировки> <время (мин)> - Логировать тренировку\n'
        '/check_progress - Проверить прогресс\n',
        reply_markup=menu_keyboard
    )


@router.message(Command('set_profile'))
async def set_profile(message: Message, state: FSMContext):
    await state.set_state(ProfileStates.waiting_for_weight)
    await message.answer("Введите свой вес в килограммах:", reply_markup=types.ReplyKeyboardRemove())


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
        await message.answer(
            "И последний шаг перед городом: сколько минут физической активности у вас в среднем за день?")

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
        await message.answer("Наконец, напишите город своего проживания:")

    except ValueError as e:
        await message.answer(f"Неверный формат уровня активности. Попробуйте еще раз: {e}")


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

    await state.update_data(profile={
        'weight': user_data['weight'],
        'height': user_data['height'],
        'age': user_data['age'],
        'activity_level': user_data['activity_level'],
        'city': city,
        'water_norm': total_water_norm,
        'calories_norm': calories,
        'water_consumed': 0,
        'last_interaction': datetime.datetime.now()
    })
    await state.clear()
    await message.answer(
        f"Ваш профиль успешно сохранен!\n"
        f"Вес: {user_data['weight']} кг\n"
        f"Рост: {user_data['height']} см\n"
        f"Возраст: {user_data['age']}\n"
        f"Уровень активности: {user_data['activity_level']} мин/день\n"
        f"Город: {city}\n"
        f"\nСуточная норма воды: {total_water_norm} мл.\n"
        f"Базовая норма калорий: {calories} ккал.",
        reply_markup=menu_keyboard
    )


@router.message(Command('log_water'))
async def log_water(message: Message, state: FSMContext):
    async with state.proxy() as data:
        if 'profile' not in data or (
                datetime.datetime.now() - data['last_interaction']).total_seconds() >= 86400:  # 24 часа
            await message.answer("Пожалуйста, сначала настройте свой профиль через команду /set_profile.",
                                 reply_markup=menu_keyboard)
            return

        profile = data['profile']
        water_consumed = profile.get('water_consumed', 0)
        water_norm = profile['water_norm']

        try:
            water_amount = float(message.text.split()[1])
            if water_amount <= 0:
                raise ValueError("Количество воды должно быть положительным числом")
        except (IndexError, ValueError) as e:
            await message.answer(f"Неверный формат количества воды. Попробуйте снова: {e}", reply_markup=menu_keyboard)
            return

        water_consumed += water_amount
        remaining_water = water_norm - water_consumed

        profile['water_consumed'] = water_consumed
        profile['last_interaction'] = datetime.datetime.now()

        await message.answer(
            f"Вы уже выпили {water_consumed} мл воды.\n"
            f"Осталось выпить: {remaining_water} мл.",
            reply_markup=menu_keyboard
        )


if __name__ == '__main__':
    dp.include_router(router)
    start_polling(dp, skip_updates=True)