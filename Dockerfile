# Базовый образ
FROM python:3.10-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# 🔽 Загружаем модель whisper 'base'
RUN python3 -c "import whisper; whisper.load_model('base')"

# Копируем весь проект
COPY . .

# Указываем переменные окружения (опционально)
ENV PYTHONUNBUFFERED=1

# Команда запуска
CMD ["python", "-m", "app.bot"]
