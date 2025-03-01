import os
import logging
import requests
from dotenv import load_dotenv

# Загружаем ключ API из .env
load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")  # Получаем ключ из переменных окружения
BASE_URL = "https://api.deepseek.com"  # Базовый URL

# Настроим логирование
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

def extract_recipe_data_with_deepseek(description, recognized_text):
    """Отправляем описание и распознанный текст в DeepSeek API для анализа."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",  # Используем модель DeepSeek-V3
        "messages": [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": f"Description: {description}"},
            {"role": "user", "content": f"Recognized Text: {recognized_text}"}
        ]
    }

    # Логируем перед отправкой
    logging.info(f"Отправляем данные в API DeepSeek: {data}")
    logging.info(f"URL запроса: {BASE_URL}/v1/chat/completions")

    try:
        response = requests.post(f"{BASE_URL}/v1/chat/completions", json=data, headers=headers)

        # Логируем статус код и ответ от API
        logging.info(f"Ответ от DeepSeek: {response.status_code}, {response.text}")

        if response.status_code == 200:
            result = response.json()
            if result.get("choices"):
                content = result['choices'][0]['message']['content']
                title, recipe, ingredients = parse_deepseek_response(content)
                return title, recipe, ingredients
            else:
                logging.error("Не удалось извлечь данные из ответа.")
                return "Не удалось извлечь данные", "", ""
        else:
            logging.error(f"Ошибка API: {response.status_code}")
            return f"Ошибка API: {response.status_code}", "", ""
    except Exception as e:
        logging.error(f"Ошибка при отправке запроса: {e}")
        return f"Ошибка при отправке запроса: {e}", "", ""

def parse_deepseek_response(content):
    """Парсит ответ от DeepSeek и извлекает нужные данные"""
    lines = content.split("\n")
    title = lines[0] if len(lines) > 0 else "Не указано"
    recipe = lines[1] if len(lines) > 1 else "Не указан"
    ingredients = lines[2] if len(lines) > 2 else "Не указаны"
    return title, recipe, ingredients
