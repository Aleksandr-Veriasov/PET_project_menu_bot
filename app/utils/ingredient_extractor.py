import logging
import os
import re
from http import HTTPStatus

import requests
from dotenv import load_dotenv

# Настроим логирование
logger = logging.getLogger(__name__)


def extract_recipe_data_with_deepseek(
    description: str, recognized_text: str
) -> tuple:
    '''Отправляем описание и распознанный текст в DeepSeek API для анализа.'''
    load_dotenv()  # Загружаем ключ API из .env
    API_KEY = os.getenv('DEEPSEEK_API_KEY')  # Получаем ключ
    if not API_KEY:
        raise ValueError('DEEPSEEK_API_KEY не найден в .env файле')
    BASE_URL = os.getenv('BASE_URL')  # Базовый URL

    headers: dict = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }

    data: dict = {
        'model': 'deepseek-chat',  # Используем модель DeepSeek-V3
        'messages': [
            {'role': 'system', 'content': 'You are a helpful assistant'},
            {'role': 'user', 'content': f'Description: {description}'},
            {'role': 'user', 'content': f'Recognized Text: {recognized_text}'}
        ]
    }

    # Логируем перед отправкой
    logger.info('Отправляем запрос в DeepSeek API')
    logger.info(f'Заголовки: {headers}')
    logger.info(f'Данные: {data}')
    logger.info(f'URL: {BASE_URL}/v1/chat/completions')

    try:
        response = requests.post(
            f'{BASE_URL}/v1/chat/completions',
            json=data,
            headers=headers
        )

        if response.status_code == HTTPStatus.OK:
            result = response.json()
            if result.get('choices'):
                content = result['choices'][0]['message']['content']
                title, recipe, ingredients = parse_deepseek_response(content)
                return title, recipe, ingredients
            else:
                logger.error('Не удалось извлечь данные из ответа DeepSeek')
                return 'Не удалось извлечь данные', '', ''
        else:
            logger.error(f'Ошибка API: {response.status_code}')
            return f'Ошибка API: {response.status_code}', '', ''
    except Exception as e:
        logger.error(f'Ошибка при отправке запроса: {e}')
        return f'Ошибка при отправке запроса: {e}', '', ''


def parse_deepseek_response(content: str) -> tuple[str, str, str]:
    '''Парсит ответ от DeepSeek и извлекает название, рецепт и ингредиенты.'''
    logger.info(f'Парсим ответ от DeepSeek:\n{content}')

    title_match = re.search(r'Название рецепта:\s*(.+)', content)

    # Новый паттерн: ищет между "Рецепт:" и "Ингредиенты:",
    # включая любые пробельные строки
    recipe_match = re.search(
        r'Рецепт:\s*((?:.*\n)*?)\s*Ингредиенты:',
        content,
        re.DOTALL
    )

    ingredients_match = re.search(
        r'Ингредиенты:\s*((?:.*\n*)+)', content, re.DOTALL
    )

    title = title_match.group(1).strip() if title_match else 'Не указано'
    recipe = recipe_match.group(1).strip() if recipe_match else 'Не указан'
    ingredients = (
        ingredients_match.group(1).strip() if ingredients_match else 'None'
    )

    logger.info(
        f'Извлеченные данные:\nНазвание: {title}\n'
        f'Рецепт: {recipe}\nИнгредиенты: {ingredients}'
    )
    return title, recipe, ingredients
