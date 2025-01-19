from dotenv import load_dotenv
import os

load_dotenv()

API_TOKEN = os.getenv('BOT_TOKEN')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
CALORIES_API_KEY = os.getenv('CALORIES_API_KEY')


if not API_TOKEN:
    raise ValueError('Переменная окружения BOT_TOKEN не установлена!')

if not WEATHER_API_KEY:
    raise ValueError('Переменная окружения WEATHER_API_KEY не установлена!')

if not WEATHER_API_KEY:
    raise ValueError('Переменная окружения CALORIES_API_KEY не установлена!')
