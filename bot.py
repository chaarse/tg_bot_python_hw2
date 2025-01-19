from aiogram import Bot, Dispatcher
from handlers import router
import asyncio
from config import API_TOKEN
from datetime import datetime, timedelta

# Создание бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
dp.include_router(router)

# Хранилище данных пользователей (пример в памяти)
user_water_logs = {}  # user_id -> {"last_update": datetime, "water_logged": int}

# Асинхронная функция очистки старых данных
async def clear_old_data():
    while True:
        now = datetime.now()
        # Удаляем данные старше 24 часов
        for user_id, data in list(user_water_logs.items()):
            if (now - data["last_update"]).total_seconds() > 86400:  # 24 часа
                del user_water_logs[user_id]
        await asyncio.sleep(3600)  # Проверяем данные раз в час

async def main():
    print('Бот запущен!')
    # Запуск задачи очистки старых данных
    asyncio.create_task(clear_old_data())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())