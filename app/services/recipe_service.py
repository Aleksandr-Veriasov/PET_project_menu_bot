from typing import List
from sqlalchemy.orm import Session, joinedload
from db.models import Recipe, Category
import logging

logger = logging.getLogger(__name__)


class RecipeService:
    def __init__(self, session: Session):
        self.session = session

    def get_by_category(self, user_id: int, category_name: str) -> List[dict]:
        '''Получить рецепты пользователя по названию категории.'''
        category = (
            self.session.query(Category)
            .filter_by(name=category_name)
            .first()
        )

        if not category:
            logger.warning(f'Категория "{category_name}" не найдена.')
            return []

        recipes = (
            self.session.query(Recipe)
            .filter_by(user_id=user_id, category_id=category.id)
            .options(
                joinedload(Recipe.category),
                joinedload(Recipe.ingredients),
                joinedload(Recipe.video),
            )
            .all()
        )

        return self.serialize(recipes)

    def serialize(self, recipes: List[Recipe]) -> List[dict]:
        '''Сериализация списка рецептов.'''
        return [
            {
                "id": recipe.id,
                "title": recipe.title,
            }
            for recipe in recipes
        ]
