import os

import pytest


def test_bot_initialization(mock_bot_dependencies):
    '''
    Проверяем инициализацию бота.
    '''
    (
        mock_builder,
        mock_setup_handlers,
        _,
        mock_app_instance,
    ) = mock_bot_dependencies

    # Вызываем функцию create_app()
    from app.bot import create_app
    app = create_app()

    # Проверяем, что Application.builder().token().build() был вызван
    mock_builder.assert_called_once()
    mock_builder.return_value.token.assert_called_once_with('test_token')
    mock_builder.return_value.token.return_value.build.assert_called_once()

    # Проверяем, что setup_handlers была вызвана
    mock_setup_handlers.assert_called_once_with(app)

    # Проверяем, что возвращённый объект приложения корректен
    assert app == mock_app_instance


def test_bot_run_polling(mock_bot_dependencies):
    '''
    Проверяем запуск бота (app.run_polling).
    '''
    _, _, _, mock_app_instance = mock_bot_dependencies

    # Вызываем функцию create_app()
    from app.bot import create_app
    app = create_app()

    # Проверяем, что app.run_polling() был вызван
    app.run_polling()
    mock_app_instance.run_polling.assert_called_once()


def test_bot_missing_token(mock_bot_dependencies):
    '''
    Проверяем, что create_app выбрасывает исключение, если токен отсутствует.
    '''
    _, _, mock_load_dotenv, _ = mock_bot_dependencies

    # Удаляем токен из окружения
    del os.environ['TELEGRAM_BOT_TOKEN']

    # Вызываем функцию create_app() и проверяем, что выбрасывается исключение
    from app.bot import create_app
    with pytest.raises(
        ValueError,
        match='TELEGRAM_BOT_TOKEN не найден в .env файле'
    ):
        create_app()
