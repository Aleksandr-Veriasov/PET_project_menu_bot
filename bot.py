import os

from dotenv import load_dotenv
from telegram.ext import Application

from handlers import setup_handlers

# Загружаем токен из .env
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Создаём бота
app = Application.builder().token(TOKEN or '').build()

# Регистрация хандлеров
setup_handlers(app)

# Запускаем бота
print('Бот запущен...')
app.run_polling()
