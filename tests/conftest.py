import os
import subprocess
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.db.db import get_engine, get_session
from app.db.db_utils import add_recipe
from app.db.models import Base, Category, Ingredient, Recipe, User, Video

# Используем SQLite in-memory базу данных для тестов
TEST_DATABASE_URL = 'sqlite:///:memory:'


@pytest.fixture(scope='function')
def test_session():
    '''
    Создаёт тестовую сессию базы данных и сбрасывает её перед каждым тестом.
    '''
    # Создаём движок для тестовой базы данных
    engine = get_engine(TEST_DATABASE_URL)
    # Создаём все таблицы
    print('Создаём таблицы...')
    Base.metadata.create_all(bind=engine)

    # Создаём сессию
    session = get_session(engine)

    yield session

    # Закрываем сессию и удаляем таблицы после теста
    session.close()
    print('Удаляем таблицы...')
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_video_file(tmp_path):
    '''
    Фикстура для создания минимального видеофайла с помощью ffmpeg.
    '''
    video_file = tmp_path / 'test_video.mp4'
    # Создаём минимальный видеофайл с помощью ffmpeg
    subprocess.run(
        [
            'ffmpeg', '-f', 'lavfi', '-i', 'color=c=blue:s=128x128:d=1',
            str(video_file)
        ],
        check=True
    )
    return video_file


@pytest.fixture
def test_user(test_session):
    '''
    Создаёт тестового пользователя.
    '''
    user = User(
        id=1,
        username='test_user',
        first_name='Test',
        last_name='User',
        created_at=datetime.now()
    )
    test_session.add(user)
    test_session.commit()
    return user


@pytest.fixture
def new_user_data():
    '''
    Возвращает данные для нового пользователя.
    '''
    return {
        'id': 5,
        'username': 'new_user',
        'first_name': 'New',
        'last_name': 'User',
        'created_at': datetime.now()
    }


@pytest.fixture
def test_recipe(test_session, test_user):
    '''
    Создаёт тестовый рецепт.
    '''
    recipe = Recipe(
        user_id=test_user.id,
        title='Test Recipe',
        description='Test recipe description',
        category_id=4,
        created_at=datetime.now()
    )
    test_session.add(recipe)
    test_session.commit()
    return recipe


@pytest.fixture
def added_recipe(request, test_session, test_user):
    '''
    Добавляет рецепт через функцию add_recipe и возвращает объект рецепта.
    Параметры рецепта можно передать через request.param.
    '''
    # Значения по умолчанию
    params = getattr(request, 'param', {})
    title = params.get('title', 'New Recipe')
    recipe = params.get('recipe', 'Test recipe instructions')
    ingredients = params.get('ingredients', '- Ingredient 1\n- Ingredient 2')
    category_id = params.get('category_id', 5)

    # Добавляем рецепт
    new_recipe = add_recipe(
        user_id=test_user.id,
        title=title,
        recipe=recipe,
        ingredients=ingredients,
        category_id=category_id,
        session=test_session
    )
    # Сохраняем строку ингредиентов в объекте рецепта для тестов
    new_recipe.ingredients_string = ingredients
    return new_recipe


@pytest.fixture
def test_ingredient(test_session):
    '''
    Создаёт тестовый ингредиент.
    '''
    ingredient = Ingredient(
        name='Test Ingredient'
    )
    test_session.add(ingredient)
    test_session.commit()
    return ingredient


@pytest.fixture
def test_category(test_session):
    '''
    Создаёт тестовую категорию.
    '''
    category = Category(
        name='Test Category'
    )
    test_session.add(category)
    test_session.commit()
    return category


@pytest.fixture
def test_video(test_session, test_recipe):
    '''
    Создаёт тестовое видео, связанное с рецептом.
    '''
    video = Video(
        recipe_id=test_recipe.id,
        video_url='http://example.com/test_video.mp4'
    )
    test_session.add(video)
    test_session.commit()
    return video


@pytest.fixture
def mock_bot_dependencies():
    '''
    Фикстура для мока зависимостей бота.
    '''
    with patch('app.bot.Application.builder') as mock_builder, \
         patch('app.bot.setup_handlers') as mock_setup_handlers, \
         patch('app.bot.load_dotenv') as mock_load_dotenv:

        # Мокаем загрузку токена из .env
        mock_load_dotenv.return_value = None
        os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token'

        # Мокаем Application.builder().token().build()
        mock_app_instance = MagicMock()
        mock_builder.return_value.token.return_value.build.return_value = (
            mock_app_instance
        )

        yield (
            mock_builder,
            mock_setup_handlers,
            mock_load_dotenv,
            mock_app_instance
        )
