
from __future__ import annotations

import logging
from typing import Generic, List, Optional, TypeVar

from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    Category, Ingredient, Recipe, RecipeIngredient, User, Video
)
from app.db.schemas import (
    CategoryCreate,
    RecipeCreate,
    RecipeUpdate,
    UserCreate,
    UserUpdate,
)

M = TypeVar("M")  # тип модели

logger = logging.getLogger(__name__)


class BaseRepository(Generic[M]):
    model: type[M]  # обязан задать наследник

    @classmethod
    def get_by_id(cls, session: Session, id: int) -> Optional[M]:
        return session.get(cls.model, id)

    @classmethod
    def get_all(
        cls,
        session: Session,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[M]:
        statement = select(cls.model).order_by(cls.model.id)
        if limit is not None:
            statement = statement.limit(limit).offset(offset)
        result = session.execute(statement)
        return result.scalars().all()


class UserRepository(BaseRepository[User]):
    model = User

    @classmethod
    def create(cls, session: Session, payload: UserCreate) -> User:
        data = payload.model_dump(exclude_unset=True, exclude_none=True)
        user = cls.model(**data)
        session.add(user)
        try:
            session.flush()     # получаем PK / дефолты
        except IntegrityError as exc:
            session.rollback()
            raise ValueError("User already exists") from exc
        session.refresh(user)    # подхватить БД-дефолты/триггеры
        return user

    @classmethod
    def update(
        cls, session: Session, user_id: int, payload: UserUpdate
    ) -> User:
        user = cls.get_by_id(session, user_id)
        if not user:
            raise ValueError("User not found")
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)

        for key, value in changes.items():
            setattr(user, key, value)

        session.flush()
        session.refresh(user)
        return user


class RecipeRepository(BaseRepository[Recipe]):
    model = Recipe

    @classmethod
    def create(cls, session: Session, recipe_create: RecipeCreate) -> Recipe:
        data = recipe_create.model_dump(exclude_unset=True)
        recipe = cls.model(**data)
        session.add(recipe)
        session.flush()          # получим PK/дефолты, но без коммита
        session.refresh(recipe)  # подхватить БД-дефолты/триггеры
        return recipe

    @classmethod
    def update(
        cls, session: Session, recipe_id: int, recipe_update: RecipeUpdate
    ) -> Recipe:
        recipe = cls.get_by_id(session, recipe_id)
        if not recipe:
            raise ValueError("Recipe not found")
        changes = recipe_update.model_dump(exclude_unset=True)

        for key, value in changes.items():
            setattr(recipe, key, value)

        session.flush()
        session.refresh(recipe)
        return recipe

    @classmethod
    def get_count_by_user(cls, session: Session, user_id: int) -> int:
        statement = select(func.count(Recipe.id)).where(
            Recipe.user_id == user_id
        )
        result = session.execute(statement).scalar_one_or_none()
        return result or 0

    @classmethod
    def get_recipes_id_by_category(
        cls, session: Session,
        user_id: int,
        category_id: int
    ) -> List[int]:
        statement = select(Recipe.id).where(
                Recipe.user_id == user_id,
                Recipe.category_id == category_id
        ).order_by(desc(Recipe.id))
        result = session.execute(statement)
        return result.scalars().all()

    @classmethod
    def get_recipe_with_connections(
        cls, session: Session, recipe_id: int
    ) -> Optional[Recipe]:
        """
        Получает рецепт с его ингредиентами и категорией.
        """
        statement = (
            select(Recipe)
            .where(Recipe.id == recipe_id)
            .options(
                joinedload(Recipe.ingredients),
                joinedload(Recipe.category),
                joinedload(Recipe.video),
            )
        )
        result = session.execute(statement)
        return result.unique().scalars().one_or_none()

    @classmethod
    def get_all_recipes_ids_and_titles(
        cls, session: Session, user_id: int, category_id: int
    ) -> List[dict]:
        """
        Получает все рецепты пользователя с их ID и заголовками.
        """
        statement = select(Recipe.id, Recipe.title).where(
                Recipe.user_id == user_id,
                Recipe.category_id == category_id
        ).order_by(Recipe.id)
        result = session.execute(statement).all()
        return [{"id": row.id, "title": row.title} for row in result]

    @classmethod
    def get_name_by_id(
        cls, session: Session, recipe_id: int
    ) -> Optional[str]:
        """
        Получает название рецепта по его ID.
        """
        statement = select(Recipe.title).where(Recipe.id == recipe_id)
        result = session.execute(statement).scalar_one_or_none()
        return result

    @classmethod
    def delete(
        cls, session: Session, recipe_id: int
    ) -> None:
        """
        Удаляет рецепт по его ID.
        """
        recipe = cls.get_by_id(session, recipe_id)
        if not recipe:
            raise ValueError("Recipe not found")
        session.delete(recipe)
        session.flush()


class CategoryRepository(BaseRepository[Category]):
    model = Category

    @classmethod
    def create(cls, session: Session, payload: CategoryCreate) -> Category:
        data = payload.model_dump(exclude_unset=True)
        category = cls.model(**data)
        session.add(category)
        try:
            session.flush()     # получим PK / дефолты
        except IntegrityError as exc:
            session.rollback()
            raise ValueError("Category already exists") from exc
        session.refresh(category)    # подхватить БД-дефолты/триггеры
        return category

    @classmethod
    def get_id_by_name(
        cls, session: Session, name: str
    ) -> List[int]:
        statement = select(cls.model.id).where(cls.model.name == name)
        result = session.execute(statement).scalar_one_or_none()
        return result


class VideoRepository(BaseRepository[Video]):
    model = Video

    @classmethod
    def get_video_url(
        cls, session: Session, recipe_id: int
    ) -> Optional[str]:
        statement = select(cls.model.video_url).where(
            cls.model.recipe_id == recipe_id
        )
        result = session.execute(statement).scalar_one_or_none()
        return result

    @classmethod
    def create(cls, session: Session, video_url: str, recipe_id: int) -> Video:
        video = cls.model(video_url=video_url, recipe_id=recipe_id)
        session.add(video)
        try:
            session.flush()  # получим PK / дефолты
        except IntegrityError as exc:
            session.rollback()
            raise ValueError("Video already exists") from exc
        session.refresh(video)  # подхватить БД-дефолты/триггеры
        return video


class IngredientRepository(BaseRepository[Ingredient]):
    model = Ingredient

    @classmethod
    def create(cls, session: Session, name: str) -> Ingredient:
        ingredient = cls.get_by_name(session, name)
        if not ingredient:
            ingredient = cls.model(name=name)
            session.add(ingredient)
            try:
                session.flush()  # получим PK / дефолты
            except IntegrityError as exc:
                session.rollback()
                raise ValueError("Ingredient already exists") from exc
            session.refresh(ingredient)
        return ingredient

    @classmethod
    def get_by_name(cls, session: Session, name: str) -> Optional[Ingredient]:
        statement = select(cls.model).where(cls.model.name == name)
        result = session.execute(statement).scalar_one_or_none()
        return result


class RecipeIngredientRepository(BaseRepository[RecipeIngredient]):
    model = RecipeIngredient

    @classmethod
    def create(
        cls, session: Session, recipe_id: int, ingredient_id: int
    ) -> RecipeIngredient:
        recipe_ingredient = cls.model(
            recipe_id=recipe_id, ingredient_id=ingredient_id
        )
        session.add(recipe_ingredient)
        try:
            session.flush()  # получим PK / дефолты
        except IntegrityError as exc:
            session.rollback()
            raise ValueError("RecipeIngredient already exists") from exc
        session.refresh(recipe_ingredient)  # подхватить БД-дефолты/триггеры
        return recipe_ingredient
