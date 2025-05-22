import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import (
    Category,
    Ingredient,
    Recipe,
    RecipeIngredient,
    User,
    Video
)

logger = logging.getLogger(__name__)


def add_user_if_not_exists(
        user_id: int,
        username: str,
        first_name: str,
        last_name: str,
        created_at: datetime,
        session: Session
) -> None:
    ''' Функция для добавления нового пользователя, если его нет в базе. '''
    # Проверяем, существует ли пользователь с таким user_id
    try:
        # Проверяем, существует ли пользователь с таким user_id
        user = session.get(User, user_id)

        if not user:
            # Если пользователя нет, добавляем его
            new_user = User(
                id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                created_at=created_at
            )
            session.add(new_user)
            session.commit()  # Сохраняем изменения
    except Exception as e:
        session.rollback()  # 🔁 Откатываем транзакцию при ошибке
        logger.error(f'Ошибка при добавлении пользователя: {e}')


def add_recipe(
        user_id: int,
        title: str,
        recipe: str,
        ingredients: str,
        category_id: int,
        session: Session
) -> Recipe:
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
    session.flush()  # Получаем ID до коммита
    session.refresh(new_recipe)  # Обновляем объект рецепта
    recipe_id: int = int(new_recipe.id)
    # Парсим ингредиенты
    ingredients_lst: list = parse_ingredients(ingredients)

    try:
        for ingredient in ingredients_lst:
            add_ingredient_and_associate_with_recipe(
                recipe_id,
                ingredient,
                session
            )
    except Exception as e:
        session.rollback()
        logger.error(f'Ошибка при добавлении ингредиента: {e}')
        raise
    session.commit()  # Сохраняем изменения

    return new_recipe


def parse_ingredients(text: str) -> list:
    '''
    Разбирает строку с ингредиентами и возвращает список ингредиентов.
    '''
    logger.debug('Начинаем парсинг ингредиентов...')
    # Убираем лишние пробелы и символы
    lines: list = text.strip().split('\n')
    ingredients: list = []  # Инициализация списка ингредиентов

    logger.debug(f'Исходный текст: {text}')
    logger.debug(f'Количество строк: {len(lines)}')
    logger.debug(f'Строки: {lines}')

    for line_number, line in enumerate(lines, 1):
        logger.debug(f'Обрабатываем строку {line_number}: {line}')

        # Убираем лишние пробелы
        stripped_line: str = line.strip()

        # Проверяем, если строка начинается с маркера '- ', то это ингредиент
        if stripped_line.startswith('- '):
            # Убираем маркер '- ' и пробелы
            ingredient_name: str = stripped_line[2:].strip()
            # Проверяем, что ингредиент не пустой
            if ingredient_name:
                ingredients.append(ingredient_name)

    logger.debug(f'Парсинг завершен. Найдено ингредиентов: {len(ingredients)}')

    return ingredients


def add_ingredient_and_associate_with_recipe(
        recipe_id: int, name: str, session: Session
) -> Ingredient:
    ''' Функция для добавления ингридиентов и связываение с рецептом. '''
    # Проверяем, существует ли ингредиент в базе данных
    try:
        # Проверяем, есть ли ингредиент
        ingredient = session.query(Ingredient).filter_by(name=name).first()

        if not ingredient:
            ingredient = Ingredient(name=name)
            session.add(ingredient)
            session.flush()  # вызывает insert

        recipe_ingredient = RecipeIngredient(
            recipe_id=recipe_id,
            ingredient_id=ingredient.id
        )
        session.add(recipe_ingredient)
        session.commit()

        return ingredient

    except Exception as e:
        session.rollback()
        logger.error(f'Ошибка при добавлении ингредиента "{name}": {e}')
        raise


def add_video_to_recipe(
    recipe_id: int, video_url: str, session: Session
) -> None:
    ''' Функция для добавления видео к рецепту. '''
    try:
        video = Video(recipe_id=recipe_id, video_url=video_url)
        session.add(video)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f'Ошибка при добавлении видео к рецепту: {e}')
        raise


def add_category_if_not_exists(
    category_name: str, session: Session
) -> Category:
    '''
    Функция для добавления категории в базу данных, если она еще не существует.
    '''
    try:
        category = (
            session.query(Category).filter_by(name=category_name).first()
        )

        if not category:
            # Если категория не существует, создаем новую
            category = Category(name=category_name)
            session.add(category)
            session.commit()
            logger.info(
                f'Категория "{category_name}" добавлена в базу данных.'
            )

        return category
    except Exception as e:
        session.rollback()
        logger.error(f'Ошибка при добавлении категории "{category_name}": {e}')
        raise


def get_recipe(recipe_id: int, session: Session) -> Optional[Recipe]:
    ''' Функция для извлечения рецепта по ID. '''
    try:
        recipe = session.query(Recipe).filter_by(id=recipe_id).first()
        return recipe
    except Exception as e:
        logger.error(f'Ошибка при получении рецепта с ID {recipe_id}: {e}')
        return None


def get_recipes_by_category_name(
    user_id: int, category_name: str, session: Session
) -> List[Recipe]:
    ''' Функция для извлечения рецептов по имени категории. '''
    try:
        # Получаем category_id по имени категории
        category = (
            session.query(Category).filter_by(name=category_name).first()
        )

        if not category:
            # Если категория не найдена
            logger.warning(f'Категория "{category_name}" не найдена.')
            return []

        # Теперь получаем рецепты пользователя по category_id
        recipes = session.query(Recipe).filter_by(
            user_id=user_id,
            category_id=category.id  # Используем найденный category_id
        ).all()

        return recipes
    except Exception as e:
        logger.error(
            f'Ошибка при получении рецептов для '
            f'категории "{category_name}": {e}'
        )
        return []


def delete_recipe(recipe_id: int, session: Session) -> None:
    ''' Функция для удаления рецепта по ID. '''
    try:
        recipe = session.query(Recipe).filter_by(id=recipe_id).first()
        if recipe:
            session.delete(recipe)
            session.commit()
            logger.info(f'Рецепт с ID {recipe_id} был удален.')
        else:
            logger.warning(f'Рецепт с ID {recipe_id} не найден.')
            return None

    except Exception as e:
        logger.error(f'Ошибка при удалении рецепта: {e}', exc_info=True)
        session.rollback()
