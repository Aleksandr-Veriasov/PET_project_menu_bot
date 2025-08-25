from enum import Enum


class RecipeMode(str, Enum):
    DEFAULT = 'recipes'
    RANDOM = 'recipe_random'
    EDIT = 'recipe_edit'
    SAVE = 'recipe_save'
