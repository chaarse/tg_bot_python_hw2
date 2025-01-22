# Telegram-бот для для расчёта нормы воды, калорий и трекинга активности
### Бот имеет основные команды:
- */set_profile*: создает профиль пользователя. Пользователю необходимо ввести свой вес, рост, возраст, ср. время физической активности в день и город (для получения текущей температуры и корректного расчета нормы воды с помощью [API OpenWeather](https://openweathermap.org/api));  
После создания профиля пользователь получает расчитанную норму калорий и воды в сутки.
- */log_water <количество>*: сохраняет, сколько воды выпито и показывает, сколько осталось до выполнения нормы;
- */log_food <название продукта>*: бот использует [API OpenFoodFacts](https://world.openfoodfacts.org/cgi/search.pl?action=process) для получения информации о продукте. Сохраняет калорийность;
- */log_workout <тип тренировки> <время (мин)>*: фиксирует сожжённые калории ([API Ninjas](https://www.api-ninjas.com/api/caloriesburned)). Учитывает расход воды на тренировке (дополнительные 200 мл за каждые 30 минут);
- */check_progress*: показывает, сколько воды и калорий потреблено, сожжено и сколько осталось до выполнения цели.  
  
### Чтобы запустить бот, надо:  
1. Перейти к боту @BotFather в Telegram;
2. Использовать команду */newbot* для создания нового бота;
3. Сохраните токен бота;
4. Получить API-ключи к OpenWeather и Ninjas;
5. Создать файл .env и положить в проект, записав туда все ключи:  
  BOT_TOKEN = 803xxx  
  WEATHER_API_KEY = 3b0xxx  
  CALORIES_API_KEY = WJ5xxx
6. Задеплоить бот на [render.com](https://render.com/);
7. Перейти в telegram к своему боту и запустить его командой */start*.

### Демонстрация работы tg-бота:
**Логи с render.com**:  

![alt text](https://raw.githubusercontent.com/chaarse/tg_bot_python_hw2/a4502f5cf02859c539028168a12310c7e0d6c3ef/sc_1.jpg)
![alt text](https://raw.githubusercontent.com/chaarse/tg_bot_python_hw2/6813c601e1c44c4e471ea175f8ae26aab9c328ac/sc_2.jpg)
![alt text](https://raw.githubusercontent.com/chaarse/tg_bot_python_hw2/0a20f79a11cb1b7f0c15b321730e7a2afb94aaac/sc_3.jpg)
![alt text](https://raw.githubusercontent.com/chaarse/tg_bot_python_hw2/53bbfaaa538091174526ebed39984e0ebde4dd39/sc_4.jpg)  

**Работа в Telegram**:  

![alt text](https://raw.githubusercontent.com/chaarse/tg_bot_python_hw2/b5492ebe07f54f3146ffd9a48ed0121d1726d0a0/telegram_bot.gif)
