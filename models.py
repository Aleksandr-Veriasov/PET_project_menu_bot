from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker


class Base(DeclarativeBase):
    ''' Базовый класс. '''
    pass


class User(Base):
    ''' Модель пользователя. '''
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Связь с рецептами
    recipes = relationship('Recipe', backref='user', lazy='dynamic')


class Recipe(Base):
    ''' Модель рецепта. '''
    __tablename__ = 'recipes'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Связь с видео
    video = relationship('Video', backref='recipe', uselist=False)

    # Связь с ингредиентами через связь многие ко многим
    ingredients = relationship('Ingredient', secondary='recipe_ingredients')

    # Связь с категорией
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    category = relationship('Category', backref='recipes')


class Ingredient(Base):
    ''' Модель ингредиента. '''
    __tablename__ = 'ingredients'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    # Связь с рецептами через связь многие ко многим
    recipes = relationship('Recipe', secondary='recipe_ingredients')


class RecipeIngredient(Base):
    ''' Модель связи между рецептом и ингредиентами. '''
    __tablename__ = 'recipe_ingredients'

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey('recipes.id'), nullable=False)
    ingredient_id = Column(
        Integer,
        ForeignKey('ingredients.id'),
        nullable=False
    )


class Video(Base):
    ''' Модель видео. '''
    __tablename__ = 'videos'

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey('recipes.id'), nullable=False)
    video_url = Column(String, nullable=False)


class Category(Base):
    ''' Модель категории. '''
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


# Создание движка базы данных
engine = create_engine('sqlite:///smart_menu.db', echo=True)

# Создание всех таблиц в базе данных
Base.metadata.create_all(engine)

# Создание сессии
Session = sessionmaker(bind=engine)
session = Session()
