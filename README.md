# SmartMenuBot 🍽️🤖

**SmartMenuBot** — это Telegram-бот [@ReceptAIbot](https://t.me/ReceptAIbot), который помогает сохранять, распознавать и организовывать рецепты из видео (TikTok, Instagram и других платформ). Он использует AI для извлечения ингредиентов и инструкций, а также позволяет управлять рецептами прямо из Telegram.  

---

## 🚀 Возможности

- 📥 Загрузка видео по ссылке (TikTok, Instagram)  
- 🧠 AI-распознавание рецепта и ингредиентов (DeepSeek API)  
- 🎙 Распознавание речи из аудио (Whisper)  
- 📂 Сохранение и организация рецептов по категориям  
- 🛠 Редактирование названия и удаление рецептов  
- 🎲 Выдача случайного рецепта  
- ⚡ Временное хранение категорий и названий рецептов в Redis для снижения нагрузки на БД  
- 🗄 Админка для работы с БД  
- 💬 Удобный интерфейс на Telegram-кнопках  

### 🔮 В разработке
- Улучшение загрузки видео из Instagram  
- Добавление ссылок на исходное видео для исключения повторной загрузки  
- 📋 Список покупок  
- 🌐 Добавление рецептов с сайтов  

---

## 🧠 Используемые технологии

- Python 3.10+  
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)  
- FastAPI  
- SQLAlchemy (async)  
- PostgreSQL (Supabase)  
- Redis  
- Docker + Docker Compose  
- NGINX  
- ffmpeg-python  
- OpenAI Whisper  
- DeepSeek API  
- Sentry  

---

## ⚙️ Установка и запуск

### 🔧 Предпосылки
- Docker  
- Docker Compose  

### 🚀 Запуск
```bash
git clone https://github.com/Aleksandr-Veriasov/Smart_menu_bot.git
cd SmartMenuBot
./refresh.sh
```
Все переменные окружения находятся в файле **.env.example.**

---

## 🧪 Тестирование и разработка

- Тесты пока в разработке (будут на pytest)
- Для main ветки настроен CI/CD (GitHub Actions)

---

## 📫 Контакты

👨‍💻 Автор: Александр Верясов \
📩 Telegram: @Alexveryasov \
🐙 GitHub: Aleksandr-Veriasov

---

## 📄 Лицензия

MIT License
