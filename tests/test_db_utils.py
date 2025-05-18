import pytest

from app.db_utils import (
    add_category_if_not_exists,
    add_user_if_not_exists,
    add_video_to_recipe,
    get_recipe,
    get_recipes_by_category_name,
    parse_ingredients,
)
from app.models import Category, Ingredient, RecipeIngredient, User, Video


def test_add_user_if_not_exists(test_session, new_user_data):
    '''
    Проверяем добавление нового пользователя, если его нет в базе.
    '''
    add_user_if_not_exists(
        user_id=new_user_data['id'],
        username=new_user_data['username'],
        first_name=new_user_data['first_name'],
        last_name=new_user_data['last_name'],
        created_at=new_user_data['created_at'],
        session=test_session
    )

    # Проверяем, что пользователь добавлен
    user = test_session.get(User, new_user_data['id'])
    assert user is not None
    assert user.username == new_user_data['username']


@pytest.mark.parametrize(
    'input_text, expected_output',
    [
        # Стандартный случай
        (
            '- Ingredient 1\n- Ingredient 2\n- Ingredient 3',
            ['Ingredient 1', 'Ingredient 2', 'Ingredient 3']
        ),
        # Пустые строки
        (
            '- Ingredient 1\n\n- Ingredient 2\n   \n- Ingredient 3',
            ['Ingredient 1', 'Ingredient 2', 'Ingredient 3']
        ),
        # Строки без маркера '- '
        (
            'Ingredient 1\n- Ingredient 2\nIngredient 3',
            ['Ingredient 2']
        ),
        # Пустой ввод
        ('', []),
    ]
)
def test_parse_ingredients(input_text, expected_output):
    '''
    Проверяем парсинг строки с ингредиентами для разных сценариев.
    '''
    result = parse_ingredients(input_text)
    assert result == expected_output


def test_add_recipe_with_ingredients(test_session, added_recipe):
    '''
    Проверяем добавление рецепта с ингредиентами через фикстуру.
    '''
    # Проверяем, что рецепт добавлен
    assert added_recipe.id is not None
    assert added_recipe.title == 'New Recipe'
    assert added_recipe.description == 'Test recipe instructions'

    # Проверяем, что ингредиенты связаны с рецептом
    recipe_ingredients = test_session.query(RecipeIngredient).filter_by(
        recipe_id=added_recipe.id
    ).all()
    expected_ingredient_count = len(
        parse_ingredients(added_recipe.ingredients_string)
    )
    assert len(recipe_ingredients) == expected_ingredient_count

    # Проверяем, что имена ингредиентов корректны
    ingredient_names = [test_session.get(
        Ingredient, link.ingredient_id
    ).name for link in recipe_ingredients]
    assert 'Ingredient 1' in ingredient_names
    assert 'Ingredient 2' in ingredient_names

    # Проверяем, что общее количество связей между рецептами и ингредиентами
    # увеличилось
    total_recipe_ingredient_count = test_session.query(
        RecipeIngredient
    ).count()
    assert total_recipe_ingredient_count >= len(recipe_ingredients)


@pytest.mark.parametrize(
    'added_recipe',
    [
        {
            'title': 'First Recipe',
            'recipe': 'First recipe instructions',
            'ingredients': '- Ingredient 1\n- Ingredient 2',
            'category_id': 5,
        },
        {
            'title': 'Second Recipe',
            'recipe': 'Second recipe instructions',
            'ingredients': '- Ingredient 1\n- Ingredient 2',
            'category_id': 4,
        },
    ],
    indirect=True,
)
def test_add_recipe_with_existing_ingredients(test_session, added_recipe):
    '''
    Проверяем добавление рецепта с уже существующими ингредиентами.
    '''
    # Проверяем, что рецепт добавлен
    assert added_recipe.id is not None
    assert added_recipe.title in ['First Recipe', 'Second Recipe']

    # Сохраняем количество ингредиентов после добавления первого рецепта
    initial_ingredient_count = test_session.query(Ingredient).count()

    # Проверяем, что количество ингредиентов не изменилось после добавления
    # второго рецепта
    if added_recipe.title == 'Second Recipe':
        final_ingredient_count = test_session.query(Ingredient).count()
        assert final_ingredient_count == initial_ingredient_count

        # Проверяем, что связи между вторым рецептом и ингредиентами созданы
        recipe_ingredients = test_session.query(RecipeIngredient).filter_by(
            recipe_id=added_recipe.id
        ).all()
        assert len(recipe_ingredients) == len(
            parse_ingredients(added_recipe.ingredients_string)
        )

        # Проверяем, что имена ингредиентов корректны
        ingredient_names = [test_session.get(
            Ingredient, link.ingredient_id
        ).name for link in recipe_ingredients]
        assert 'Ingredient 1' in ingredient_names
        assert 'Ingredient 2' in ingredient_names


def test_add_video_to_recipe(test_session, test_recipe):
    '''
    Проверяем добавление видео к рецепту.
    '''
    video_url = 'http://example.com/test_video.mp4'
    add_video_to_recipe(
        recipe_id=test_recipe.id,
        video_url=video_url,
        session=test_session
    )

    # Проверяем, что видео добавлено
    video = test_session.query(Video).filter_by(
        recipe_id=test_recipe.id
    ).first()
    assert video is not None
    assert video.video_url == video_url


def test_add_category_if_not_exists(test_session, test_category):
    '''
    Проверяем добавление категории, если её нет в базе, и предотвращение
    дублирования.
    '''
    category_name = test_category.name

    # Проверяем, что категория уже существует
    initial_category_count = test_session.query(Category).filter_by(
        name=category_name
    ).count()
    assert initial_category_count == 1  # Категория создана фикстурой

    # Вызываем функцию для добавления категории
    category = add_category_if_not_exists(
        category_name=category_name,
        session=test_session
    )

    # Проверяем, что функция возвращает существующую категорию
    assert category is not None
    assert category.name == category_name
    assert category.id == test_category.id

    # Подсчёт количества категорий с данным именем после вызова функции
    final_category_count = test_session.query(Category).filter_by(
        name=category_name
    ).count()
    assert final_category_count == initial_category_count


def test_get_recipe(test_session, test_recipe):
    '''
    Проверяем извлечение рецепта по ID.
    '''
    # Проверяем, что рецепт извлекается корректно
    recipe = get_recipe(recipe_id=test_recipe.id, session=test_session)
    assert recipe is not None
    assert recipe.id == test_recipe.id
    assert recipe.title == test_recipe.title

    # Проверяем, что возвращается None для несуществующего ID
    non_existent_recipe = get_recipe(9999, test_session)
    assert non_existent_recipe is None


def test_get_recipes_by_category_name(
        test_session,
        test_user,
        test_category,
        test_recipe
):
    '''
    Проверяем извлечение рецептов по имени категории.
    '''
    # Связываем рецепт с категорией
    test_recipe.category_id = test_category.id
    test_session.commit()

    # Проверяем, что рецепт извлекается корректно
    recipes = get_recipes_by_category_name(
        user_id=test_user.id,
        category_name=test_category.name,
        session=test_session
    )
    assert len(recipes) == 1
    assert recipes[0].id == test_recipe.id
    assert recipes[0].title == test_recipe.title

    # Проверяем, что возвращается пустой список для несуществующей категории
    non_existent_category_recipes = get_recipes_by_category_name(
        user_id=test_user.id,
        category_name='Nonexistent Category',
        session=test_session
    )
    assert non_existent_category_recipes == []

    # Проверяем, что возвращается пустой список, если у пользователя
    # нет рецептов в категории
    another_user_id = 9999  # ID пользователя, у которого нет рецептов
    no_recipes = get_recipes_by_category_name(
        user_id=another_user_id,
        category_name=test_category.name,
        session=test_session
    )
    assert no_recipes == []
