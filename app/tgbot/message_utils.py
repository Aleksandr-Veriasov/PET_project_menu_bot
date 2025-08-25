import logging
import random

from sqlalchemy.orm import Session

from app.db.repository import (
    CategoryRepository, RecipeRepository, VideoRepository
)
# Включаем логирование
logger = logging.getLogger(__name__)


def random_recipe(
    session: Session,
    user_id: int,
    category_name: str
) -> tuple[str, str]:
    """
    Получает случайный рецепт из категории для пользователя.
    """
    category_ids = CategoryRepository().get_id_by_name(
        session, category_name
    )
    recipes_ids = RecipeRepository().get_recipes_id_by_category(
        session, user_id, category_ids
    )
    random_recipe_id = random.choice(recipes_ids)
    recipe = RecipeRepository().get_recipe_with_connections(
        session, random_recipe_id
    )

    video_url = VideoRepository().get_video_url(
        session, recipe.id
    )
    logger.info(f'◀️ {video_url} - video URL для рецепта {recipe.title}')
    # Формируем список ингредиентов
    ingredients_text = '\n'.join(
        f"- {ingredient.name}" for ingredient in recipe.ingredients
    )
    text = (
        f'Вот случайный рецепт из категории "{category_name}":\n\n'
        f'🍽 *{recipe.title}*\n\n'
        f'📝 {recipe.description or ""}\n\n'
        f'🥦 *Ингредиенты:*\n{ingredients_text}'
    )
    return video_url, text
