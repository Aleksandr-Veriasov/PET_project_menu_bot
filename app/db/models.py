from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    ''' Базовый класс. '''
    pass


class User(Base):
    ''' Модель пользователя. '''
    __tablename__ = 'users'

    # Используем Telegram user_id
    id = Column(BigInteger, primary_key=True, unique=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Связь с рецептами
    recipes = relationship('Recipe', backref='user', lazy='dynamic')


class Recipe(Base):
    ''' Модель рецепта. '''
    __tablename__ = 'recipes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Связь с видео
    video = relationship(
        'Video',
        backref='recipe',
        uselist=False,
        cascade='all, delete-orphan'
    )

    # Связь с ингредиентами через связь многие ко многим
    ingredients = relationship(
        'Ingredient',
        secondary='recipe_ingredients',
        back_populates='recipes',  # Добавлено back_populates
        passive_deletes=True
    )
    # Связь с категорией
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    category = relationship('Category', backref='recipes')


class Ingredient(Base):
    ''' Модель ингредиента. '''
    __tablename__ = 'ingredients'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)

    # Связь с рецептами через связь многие ко многим
    recipes = relationship(
        'Recipe',
        secondary='recipe_ingredients',
        back_populates='ingredients'  # Добавлено back_populates
    )


class RecipeIngredient(Base):
    ''' Модель связи между рецептом и ингредиентами. '''
    __tablename__ = 'recipe_ingredients'

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_id = Column(
        Integer, ForeignKey('recipes.id', ondelete='CASCADE'), nullable=False
    )
    ingredient_id = Column(
        Integer,
        ForeignKey('ingredients.id', ondelete='CASCADE'),
        nullable=False
    )


class Video(Base):
    ''' Модель видео. '''
    __tablename__ = 'videos'

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_id = Column(
        Integer,
        ForeignKey('recipes.id', ondelete='CASCADE'),
        nullable=False
    )
    video_url = Column(String, nullable=False)


class Category(Base):
    ''' Модель категории. '''
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
