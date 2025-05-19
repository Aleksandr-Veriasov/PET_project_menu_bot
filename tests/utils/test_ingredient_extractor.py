from http import HTTPStatus
from unittest.mock import Mock

import pytest

from app.utils.ingredient_extractor import extract_recipe_data_with_deepseek


def test_extract_recipe_data_with_deepseek_success(mocker):
    '''
    Проверяем успешный ответ от API.
    '''
    mock_post = mocker.patch('app.utils.ingredient_extractor.requests.post')
    mock_post.return_value = Mock(
        status_code=HTTPStatus.OK,
        json=lambda: {
            'choices': [
                {
                    'message': {
                        'content': (
                            'Название рецепта: Борщ\n'
                            'Рецепт: 1. Нарезать овощи. 2. Варить 2 часа.\n'
                            'Ингредиенты: - Свекла - Морковь - Лук\n'
                        )
                    }
                }
            ]
        }
    )

    description = 'Как приготовить борщ?'
    recognized_text = 'Борщ, овощи, варить'

    title, recipe, ingredients = extract_recipe_data_with_deepseek(
        description,
        recognized_text
    )

    # Проверяем, что результат содержит префиксы, как возвращает
    # parse_deepseek_response
    assert title == 'Название рецепта: Борщ'
    assert recipe == 'Рецепт: 1. Нарезать овощи. 2. Варить 2 часа.'
    assert ingredients == 'Ингредиенты: - Свекла - Морковь - Лук'


def test_extract_recipe_data_with_deepseek_missing_api_key(mocker):
    '''
    Проверяем, что выбрасывается исключение, если ключ API отсутствует.
    '''
    mocker.patch('os.getenv', side_effect=lambda key: (
        None if key == 'DEEPSEEK_API_KEY' else 'http://example.com'
    ))

    description = 'Как приготовить борщ?'
    recognized_text = 'Борщ, овощи, варить'

    with pytest.raises(ValueError, match='DEEPSEEK_API_KEY не найден в .env'):
        extract_recipe_data_with_deepseek(description, recognized_text)


def test_extract_recipe_data_with_deepseek_api_error(mocker):
    '''
    Проверяем обработку ошибки API.
    '''
    mock_post = mocker.patch('app.utils.ingredient_extractor.requests.post')
    mock_post.return_value = Mock(status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

    description = 'Как приготовить борщ?'
    recognized_text = 'Борщ, овощи, варить'

    title, recipe, ingredients = extract_recipe_data_with_deepseek(
        description,
        recognized_text
    )

    assert title == 'Ошибка API: 500'
    assert recipe == ''
    assert ingredients == ''


def test_extract_recipe_data_with_deepseek_exception(mocker):
    '''
    Проверяем обработку исключения при запросе.
    '''
    mock_post = mocker.patch('app.utils.ingredient_extractor.requests.post')
    mock_post.side_effect = Exception('Connection error')

    description = 'Как приготовить борщ?'
    recognized_text = 'Борщ, овощи, варить'

    title, recipe, ingredients = extract_recipe_data_with_deepseek(
        description,
        recognized_text
    )

    assert title == 'Ошибка при отправке запроса: Connection error'
    assert recipe == ''
    assert ingredients == ''
