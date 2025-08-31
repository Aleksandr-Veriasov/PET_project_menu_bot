import logging
import random

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from packages.db.repository import (
    CategoryRepository, RecipeRepository, VideoRepository
)
# Включаем логирование
logger = logging.getLogger(__name__)


async def random_recipe(
    session: AsyncSession,
    user_id: int,
    category_slug: str
) -> tuple[Optional[str], str]:
    """
    Получает случайный рецепт из категории для пользователя.
    """
    category_id, category_name = await CategoryRepository(
        ).get_id_and_name_by_slug(session, category_slug)

    if category_id:
        recipes_ids = await RecipeRepository().get_recipes_id_by_category(
            session, user_id, category_id
        )
    random_recipe_id = random.choice(recipes_ids)
    recipe = await RecipeRepository().get_recipe_with_connections(
        session, random_recipe_id
    )
    if recipe is None:
        return '', ''
    else:
        video_url = await VideoRepository().get_video_url(
            session, int(recipe.id)
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
