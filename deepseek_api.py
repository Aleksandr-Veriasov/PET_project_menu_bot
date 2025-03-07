import logging
import os

from dotenv import load_dotenv
from openai import OpenAI

# Загружаем API ключ из .env
load_dotenv()
API_KEY = os.getenv('DEEPSEEK_API_KEY')  # Получаем ключ

if not API_KEY:
    logging.error('API ключ не найден. Убедитесь, что он указан в .env файле.')
    exit(1)

# Настроим OpenAI клиент с DeepSeek API
client = OpenAI(api_key=API_KEY, base_url='https://api.deepseek.com')


def extract_recipe_data_with_deepseek(description: str, recognized_text: str):
    '''Отправляет описание и распознанный текст в DeepSeek API для анализа.'''

    logging.info(f'Отправка в DeepSeek: описание: {description}')
    logging.info(f'Отправка в DeepSeek: распознанный текст: {recognized_text}')

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
        message_content = response.choices[0].message.content
        logging.info(f'Ответ от DeepSeek: {message_content}')

        # Извлекаем данные из ответа
        title, recipe, ingredients = parse_deepseek_response(message_content)

        return title, recipe, ingredients

    except Exception as e:
        logging.error(f'Ошибка при отправке запроса: {e}')
        return 'Ошибка при отправке запроса', '', ''


def parse_deepseek_response(content: str):
    ''' Парсит ответ от DeepSeek и извлекает нужные данные. '''
    lines = content.split('\n')

    title = ''
    recipe = ''
    ingredients = ''

    # Флаги для определения текущего блока
    is_recipe = False
    is_ingredients = False

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
    logging.info(f'Название рецепта: {title}')
    logging.info(f'Рецепт: {recipe}')
    logging.info(f'Ингредиенты: {ingredients}')

    return title, recipe, ingredients
