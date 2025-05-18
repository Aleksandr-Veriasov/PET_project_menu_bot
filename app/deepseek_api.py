import asyncio
import logging
import os
from functools import partial

from dotenv import load_dotenv
from openai import OpenAI

# Загружаем API ключ из .env
load_dotenv()
API_KEY = os.getenv('DEEPSEEK_API_KEY')  # Получаем ключ

logger = logging.getLogger(__name__)

if not API_KEY:
    logger.error('DEEPSEEK_API_KEY не найден в .env файле')
    exit(1)

# Настроим OpenAI клиент с DeepSeek API
client = OpenAI(api_key=API_KEY, base_url='https://api.deepseek.com')


def extract_recipe_data_with_deepseek(
    description: str, recognized_text: str
) -> tuple[str, str, str]:
    '''Отправляет описание и распознанный текст в DeepSeek API для анализа.'''

    logger.info('Отправка запроса в DeepSeek API...')
    logger.info(f'Описание: {description}')
    logger.info(f'Распознанный текст: {recognized_text}')

    try:
        # Создаем запрос с использованием DeepSeek
        response = client.chat.completions.create(
            model='deepseek-chat',  # Используем модель DeepSeek-V3
            messages=[
                {
                    'role': 'system',
                    'content': (
                        'You are a helpful assistant that extracts recipe '
                        'data. '
                        'Always respond in Russian, even if the input is '
                        'in English. '
                        'Use the following format:\n'
                        'Название рецепта: <название>\n'
                        'Рецепт: <текст рецепта>\n'
                        'Ингредиенты: <список ингредиентов>\n'
                        'Если в рецепте есть соус или заправка, включи их '
                        'ингредиенты в список ингредиентов.'
                    )
                },
                {'role': 'user', 'content': f'Description: {description}'},
                {
                    'role': 'user',
                    'content': f'Recognized Text: {recognized_text}'
                }
            ],
            stream=False  # False, чтобы не использовать потоковый режим
        )

        # Логируем ответ от DeepSeek
        message_content = response.choices[0].message.content or ''
        logger.info(f'Ответ от DeepSeek: {message_content}')

        # Извлекаем данные из ответа
        title, recipe, ingredients = parse_deepseek_response(message_content)

        return title, recipe, ingredients

    except Exception as e:
        logger.error(f'Ошибка при отправке запроса в DeepSeek API: {e}')
        return 'Ошибка при отправке запроса', '', ''


async def extract_recipe_data_async(
    description: str, recognized_text: str
) -> tuple[str, str, str]:
    '''Асинхронная обертка для запроса к DeepSeek.'''
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, partial(
            extract_recipe_data_with_deepseek, description, recognized_text
        )
    )


def parse_deepseek_response(content: str) -> tuple:
    ''' Парсит ответ от DeepSeek и извлекает нужные данные. '''
    lines: list[str] = content.split('\n')

    title: str = ''
    recipe: str = ''
    ingredients: str = ''

    # Флаги для определения текущего блока
    is_recipe: bool = False
    is_ingredients: bool = False

    for line in lines:
        # Удаляем лишние пробелы и символы
        line = line.strip()

        # Пропускаем пустые строки
        if not line:
            is_recipe = False
            continue

        # Извлечение названия
        if line.startswith('Название рецепта:'):
            title = line.replace('Название рецепта:', '').strip()

        # Начало блока рецепта
        elif line.startswith('Рецепт:'):
            is_recipe = True
            # Добавляем сам текст после 'Рецепт:'
            recipe = line.replace('Рецепт:', '').strip()

        # Начало блока ингредиентов
        elif line.startswith('Ингредиенты:'):
            is_ingredients = True
            is_recipe = False
            ingredients = line.replace('Ингредиенты:', '').strip()

        # Если мы внутри блока рецепта
        elif is_recipe:
            if line[0].isdigit() and len(line) > 1 and line[1] == '.':
                # Если строка с номера (например: '1.')
                recipe += '\n' + line.strip()

        # Если мы внутри блока ингредиентов
        elif is_ingredients:
            if line.startswith(('- ', '* ')):
                # Если строка начинается с маркера списка
                ingredients += '\n' + line.strip()

    # Проверка на пустые строки или разделение блоков
    title = title if title else 'Не указано'
    recipe = recipe if recipe else 'Не указан'
    ingredients = ingredients if ingredients else 'Не указаны'

    # Логируем извлеченные данные для отладки
    logger.info(f'Название: {title}')
    logger.info(f'Рецепт: {recipe}')
    logger.info(f'Ингредиенты: {ingredients}')

    return title, recipe, ingredients
