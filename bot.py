from aiogram import Bot, Dispatcher
from handlers import router
import asyncio
from config import API_TOKEN

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
dp.include_router(router)

async def main():
    print('Бот запущен!')
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())