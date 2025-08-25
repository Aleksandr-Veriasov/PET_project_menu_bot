import logging
import re
from typing import List, Tuple

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.tgbot.keyboards.builders import InlineKB
from app.tgbot.recipes_modes import RecipeMode

logger = logging.getLogger(__name__)

_CB_RE = re.compile(
    r'^(?P<category>breakfast|main|salad)_recipes(?:_(?P<mode>random|edit))?$'
)


def start_keyboard(new_user: bool) -> InlineKeyboardMarkup:
    """ Создание кнопок для стартового сообщения и домой."""
    if new_user:
        keyboard = [
            [InlineKeyboardButton(
                    '🍳 Загрузить рецепт', callback_data='upload_recipe'
                )],
            [InlineKeyboardButton('❓ Помощь', callback_data='help')],
        ]
    else:
        keyboard = [
            [InlineKeyboardButton('📖 Рецепты', callback_data='recipes')],
            [InlineKeyboardButton(
                    '🎲 Случайные рецепты', callback_data='recipe_random'
                )],
            [InlineKeyboardButton(
                '🍳 Загрузить рецепт', callback_data='upload_recipe'
                )],
            [InlineKeyboardButton(
                '✏️ Редактировать рецепт', callback_data='recipe_edit'
                )]
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


def help_keyboard() -> InlineKeyboardMarkup:
    """ Создание кнопок для помощи."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton('🏠 На главную', callback_data='start')],
        [InlineKeyboardButton(
            '🍳 Загрузить рецепт', callback_data='upload_recipe'
            )]
    ])
    return keyboard


def home_keyboard() -> InlineKeyboardMarkup:
    """ Создание кнопок для домашнего меню."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton('🏠 На главную', callback_data='start')]
    ])
    return keyboard


def category_keyboard(
        mode: RecipeMode = RecipeMode.DEFAULT
) -> InlineKeyboardMarkup:
    """ Создание кнопок для выбора категории рецептов."""
    if mode is RecipeMode.RANDOM:
        row = [
            [InlineKeyboardButton(
                '🌅 Завтрак', callback_data='breakfast_recipes_random'
            )],
            [InlineKeyboardButton(
                '🍲 Основное блюдо',
                callback_data='main_recipes_random'
            )],
            [InlineKeyboardButton(
                '🥗 Салат', callback_data='salad_recipes_random'
            )]
        ]
    elif mode is RecipeMode.DEFAULT or mode is RecipeMode.SAVE:
        row = [
            [InlineKeyboardButton(
                '🌅 Завтрак', callback_data='breakfast_recipes'
            )],
            [InlineKeyboardButton(
                '🍲 Основное блюдо', callback_data='main_recipes'
            )],
            [InlineKeyboardButton('🥗 Салат', callback_data='salad_recipes')]
        ]
    else:
        row = [
            [InlineKeyboardButton(
                '🌅 Завтрак', callback_data='breakfast_recipes_edit'
            )],
            [InlineKeyboardButton(
                '🍲 Основное блюдо', callback_data='main_recipes_edit'
            )],
            [InlineKeyboardButton(
                '🥗 Салат', callback_data='salad_recipes_edit'
            )]
        ]
    if mode is RecipeMode.SAVE:
        row.append([InlineKeyboardButton(
            '❌ Отмена', callback_data='cancel_save_recipe'
        )])
    else:
        row.append([InlineKeyboardButton('🔙 Назад', callback_data='start')])
    reply_markup = InlineKeyboardMarkup(row)
    return reply_markup


def build_recipes_list_keyboard(
    items: List[Tuple[int, str]],
    page: int = 0,
    *,
    per_page: int = 5,
    edit: bool = False,
    category_slug: str
) -> InlineKeyboardMarkup:
    """ Создание клавиатуры для списка рецептов с пагинацией."""
    total = len(items)
    start = max(0, page) * per_page
    end = min(total, start + per_page)
    current = items[start:end]

    rows = [[InlineKeyboardButton(
            text=(f'▪️ {recipe["title"]}'),
            callback_data=(
                f'{category_slug}_edit_recipe_{recipe["id"]}'
                if edit else f'{category_slug}_recipe_{recipe["id"]}'
            )
            )] for recipe in current]

    # пагинация
    if end < total:
        rows.append([InlineKeyboardButton(
            'Далее ⏩', callback_data=f'next_{page + 1}'
        )])
    if page > 0:
        rows.append([InlineKeyboardButton(
            '⏪ Назад', callback_data=f'prev_{page - 1}'
        )])

    # домой/меню (если нужно)
    rows.append([InlineKeyboardButton('🏠 В меню', callback_data='start')])

    return InlineKeyboardMarkup(rows)


def recipe_edit_keyboard(recipe_id: int, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
                '✏️ Редактировать рецепт',
                callback_data=f'edit_recipe_{recipe_id}'
            )],
        [InlineKeyboardButton(
                '🗑 Удалить рецепт',
                callback_data=f'delete_recipe_{recipe_id}'
            )],
        [InlineKeyboardButton('⏪ Назад', callback_data=f'next_{page}')],
        [InlineKeyboardButton('🏠 На главную', callback_data='start')]
    ])


def choice_recipe_keyboard(page: int) -> InlineKeyboardMarkup:
    """ Создание клавиатуры для выбора рецепта."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            '⏪ Назад',
            callback_data=f'next_{page}'
        )],
        [InlineKeyboardButton('🏠 На главную', callback_data='start')]
    ])


def keyboard_choose_field() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Изменить название", callback_data="f:title")],
        [InlineKeyboardButton("❌ Отмена",   callback_data="cancel")],
    ])


def keyboard_save() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Сохранить", callback_data="save_changes")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
    ])


def keyboard_delete() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑 Удалить", callback_data="delete")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
    ])


def keyboard_save_cancel_delete(func: str = None) -> InlineKeyboardMarkup:
    """ Создание клавиатуры для сохранения, отмены и удаления."""
    kb = InlineKB()
    if func == 'start_edit':
        kb.button(text='📝 Изменить название', callback_data='f:title')
    elif func == 'handle_title':
        kb.button(text='✅ Сохранить', callback_data='save_changes')
    elif func == 'delete_recipe':
        kb.button(text='🗑 Удалить', callback_data='delete')
    kb.button(text='❌ Отмена', callback_data='cancel')
    return kb.adjust(1)


def keyboard_save_recipe() -> InlineKeyboardMarkup:
    """ Создание клавиатуры для сохранения рецепта."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "✅ Сохранить рецепт", callback_data="save_recipe"
        )],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_save_recipe")],
    ])
