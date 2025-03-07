import logging
from datetime import datetime

from models import (
    Category,
    Ingredient,
    Recipe,
    RecipeIngredient,
    Session,
    User,
    Video
)


logging.basicConfig(
    filename='ingredients_parser.log',  # Файл для записи логов
    level=logging.DEBUG,  # Уровень логирования
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Создаем сессию для взаимодействия с базой данных
session = Session()


def add_user_if_not_exists(
        user_id,
        username,
        first_name,
        last_name,
        created_at
):
    ''' Функция для добавления нового пользователя, если его нет в базе. '''
    # Проверяем, существует ли пользователь с таким user_id
    user = session.query(User).filter_by(user_id=user_id).first()

    if not user:
        # Если пользователя нет, добавляем его
        new_user = User(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            created_at=created_at
        )
        session.add(new_user)
        session.commit()  # Сохраняем изменения


def add_recipe(user_id, title, recipe, ingredients, category_id):
    ''' Функция для добавления нового рецепта. '''
    created_at = datetime.now()
    new_recipe = Recipe(
        user_id=user_id,
        title=title,
        description=recipe,
        created_at=created_at,
        category_id=category_id
    )
    session.add(new_recipe)
    session.commit()  # Сохраняем изменения
    # Парсим ингредиенты
    ingredients = parse_ingredients(ingredients)

    for ingredient in ingredients:
        add_ingredient_and_associate_with_recipe(new_recipe.id, ingredient)

    return new_recipe


def parse_ingredients(text):
    '''
    Разбирает строку с ингредиентами и возвращает список ингредиентов.
    '''
    logging.info('Начало парсинга ингредиентов.')
    # Убираем лишние пробелы и символы
    lines = text.strip().split('\n')
    ingredients = []  # Инициализация списка ингредиентов

    logging.info(f'Количество строк для парсинга: {len(lines)}')

    for line_number, line in enumerate(lines, 1):
        logging.debug(f'Парсинг строки {line_number}: {line}')

        # Убираем лишние пробелы
        line = line.strip()

        # Проверяем, если строка начинается с маркера '- ', то это ингредиент
        if line.startswith('- '):
            ingredient_name = line[2:].strip()  # Убираем маркер '- ' и пробелы
            # Проверяем, что ингредиент не пустой
            if ingredient_name:
                ingredients.append(ingredient_name)

    logging.info(f'Парсинг завершен. Найдено ингредиентов: {len(ingredients)}')

    return ingredients


def add_ingredient_and_associate_with_recipe(recipe_id, name):
    ''' Функция для добавления ингридиентов и связываение с рецептом. '''
    # Проверяем, существует ли ингредиент в базе данных
    ingredient = session.query(Ingredient).filter_by(name=name).first()

    if not ingredient:
        # Если ингредиент не найден, добавляем новый
        ingredient = Ingredient(name=name)
        session.add(ingredient)
        session.commit()

    # Теперь добавляем связь между рецептом и ингредиентом
    recipe_ingredient = RecipeIngredient(
        recipe_id=recipe_id,
        ingredient_id=ingredient.id
    )
    session.add(recipe_ingredient)
    session.commit()

    return ingredient


def add_video_to_recipe(recipe_id, video_url):
    ''' Функция для добавления видео к рецепту. '''
    video = Video(recipe_id=recipe_id, video_url=video_url)
    session.add(video)
    session.commit()


def add_category_if_not_exists(category_name):
    """
    Функция для добавления категории в базу данных, если она еще не существует.
    """
    category = session.query(Category).filter_by(name=category_name).first()

    if not category:
        # Если категория не существует, создаем новую
        category = Category(name=category_name)
        session.add(category)
        session.commit()
        logging.info(
            f"Категория '{category_name}' успешно добавлена в базу данных."
        )

    return category


def get_recipe(recipe_id):
    ''' Функция для извлечения рецепта по ID. '''
    recipe = session.query(Recipe).filter_by(id=recipe_id).first()
    return recipe


def get_recipes_by_category_name(user_id, category_name):
    ''' Функция для извлечения рецептов по имени категории. '''

    # Получаем category_id по имени категории
    category = session.query(Category).filter_by(name=category_name).first()

    if not category:
        # Если категория не найдена
        logging.error(f"Категория с именем '{category_name}' не найдена.")
        return []

    # Теперь получаем рецепты пользователя по category_id
    recipes = session.query(Recipe).filter_by(
        user_id=user_id,
        category_id=category.id  # Используем найденный category_id
    ).all()

    return recipes
