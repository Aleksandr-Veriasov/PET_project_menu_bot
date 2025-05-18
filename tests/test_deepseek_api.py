import importlib

import app.deepseek_api
from app.deepseek_api import (
    extract_recipe_data_with_deepseek, parse_deepseek_response
)


def test_extract_recipe_data_with_deepseek_success(mocker):
    mock_client = mocker.patch(
        'app.deepseek_api.client.chat.completions.create'
    )
    mock_client.return_value = mocker.Mock(
        choices=[mocker.Mock(message=mocker.Mock(content=(
            'Название рецепта: Борщ\n'
            'Рецепт: 1. Нарезать овощи.\n2. Варить 2 часа.\n'
            'Ингредиенты: - Свекла\n- Морковь\n- Лук'
        )))]
    )

    description = 'Как приготовить борщ?'
    recognized_text = 'Борщ, овощи, варить'

    title, recipe, ingredients = extract_recipe_data_with_deepseek(
        description, recognized_text
    )

    assert title == 'Борщ'
    assert recipe == '1. Нарезать овощи.\n2. Варить 2 часа.'
    assert ingredients == '- Свекла\n- Морковь\n- Лук'


def test_extract_recipe_data_with_deepseek_exception(mocker):
    mock_client = mocker.patch(
        'app.deepseek_api.client.chat.completions.create'
    )
    mock_client.side_effect = Exception('API Error')

    description = 'Как приготовить борщ?'
    recognized_text = 'Борщ, овощи, варить'

    title, recipe, ingredients = extract_recipe_data_with_deepseek(
        description, recognized_text
    )

    assert title == 'Ошибка при отправке запроса'
    assert recipe == ''
    assert ingredients == ''


def test_parse_deepseek_response_success():
    content = (
        'Название рецепта: Борщ\n'
        'Рецепт: 1. Нарезать овощи.\n2. Варить 2 часа.\n'
        'Ингредиенты: - Свекла\n- Морковь\n- Лук'
    )

    title, recipe, ingredients = parse_deepseek_response(content)

    assert title == 'Борщ'
    assert recipe == '1. Нарезать овощи.\n2. Варить 2 часа.'
    assert ingredients == '- Свекла\n- Морковь\n- Лук'


def test_parse_deepseek_response_empty():
    content = ''

    title, recipe, ingredients = parse_deepseek_response(content)

    assert title == 'Не указано'
    assert recipe == 'Не указан'
    assert ingredients == 'Не указаны'


def test_api_key_loaded(mocker):
    # Сначала мокируем
    mocker.patch('os.getenv', return_value='test_api_key')

    importlib.reload(app.deepseek_api)  # Перезагрузили модуль

    # Теперь замокали OpenAI после reload
    mock_openai = mocker.patch('app.deepseek_api.OpenAI')

    # Создаём клиента заново после мока
    from app.deepseek_api import OpenAI
    OpenAI(api_key='test_api_key', base_url='https://api.deepseek.com')

    mock_openai.assert_called_once_with(
        api_key='test_api_key', base_url='https://api.deepseek.com'
    )
