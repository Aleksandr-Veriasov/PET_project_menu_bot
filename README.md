# SmartMenuBot 🍽️🤖

**SmartMenuBot** — это Telegram-бот (@ReceptAIbot), который помогает сохранять, распознавать и организовывать рецепты из видео (TikTok, Instagram и других платформ). Он использует AI для извлечения ингредиентов и инструкций, а также позволяет управлять рецептами прямо из Telegram. 

---

## 🚀 Возможности

- 📥 Загрузка видео по ссылке (TikTok, Instagram)
- 🧠 AI-распознавание рецепта и ингредиентов (DeepSeek API)
- 🎙 Распознавание речи из аудио (Whisper)
- 📂 Сохранение и организация рецептов по категориям
- 🛠 Редактирование названия и удаление рецептов
- 🎲 Выдача случайного рецепта
- 💬 Удобный интерфейс на Telegram-кнопках

---

## 🛠 Установка

### 🔧 Предпосылки:

- Python 3.10+
- PostgreSQL
- ffmpeg

### 📦 Установка зависимостей

```bash
git clone https://github.com/yourusername/SmartMenuBot.git
cd SmartMenuBot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## ⚙️ Конфигурация

Создайте файл `.env`:

```env
TELEGRAM_BOT_TOKEN=ваш_токен_бота
DATABASE_URL=postgresql+psycopg2://username:password@localhost:5432/smart_menu
CHAT_ID=@your_channel_or_chat_id
DEEPSEEK_API_KEY=ключ_от_DeepSeek
SENTRY_DS=ключ_от_Sentry
```

---

## 📋 Запуск

```bash
alembic upgrade head  # миграции
python -m app.bot
```

---

## 🧪 Тесты

```bash
pytest
```

---

## 🗂 Структура проекта

```
app/
├── api/
├── db/
├── handlers/
├── media/
├── utils/
├── bot.py
tests/
migrations/
.env
requirements.txt
```

---

## 🧠 Используемые технологии

- python-telegram-bot v20+
- SQLAlchemy 2.0
- PostgreSQL
- OpenAI Whisper
- DeepSeek API
- yt-dlp
- ffmpeg

---

## 🤝 Автор

Александр Верясов  
📫 Telegram: @Alexveryasov  
🐙 GitHub: github.com/Aleksandr-Veriasov

---

## 📄 Лицензия

MIT License
