import logging
import random
from typing import cast

from sqlalchemy.orm import joinedload
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import ContextTypes

from app.db.db import get_session_context
from app.db.db_utils import Recipe
from app.utils.helpers import get_safe_message_from_update, get_safe_user_data
from app.utils.state import user_data_tempotary

logger = logging.getLogger(__name__)

RECIPES_PER_PAGE = 5  # Количество рецептов на странице


async def send_recipe_confirmation(
        message: Message,
        title: str,
        recipe: str,
        ingredients: str,
        video_file_id: str,
):
    '''
    Функция отправляет пользователю сообщение с рецептом и кнопками для
    подтверждения или редактирования.
    '''
    if message.from_user is None:
        logger.warning('Пользователь не найден (from_user is None)')
        return
    user_id = message.from_user.id
    user_data_tempotary[user_id] = {
        'title': title,
        'recipe': recipe,
        'ingredients': ingredients
    }

    keyboard = [
        [InlineKeyboardButton(
            '✅ Сохранить рецепт',
            callback_data='save_recipe'
        )],
        [InlineKeyboardButton(
            '❌ Не сохранять рецепт',
            callback_data='discard_recipe'
        )]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем видео с file_id
    logger.info(f'Отправляем видео с file_id: {video_file_id}')
    await message.reply_video(video_file_id)
    logger.info('Видео успешно отправлено')

    logger.info('Отправляем текст с рецептом и кнопками подтверждения.')
    await message.reply_text(
        f'🍽 <b>Название рецепта:</b>\n{title}\n\n'
        f'📝 <b>Рецепт:</b>\n{recipe}\n\n'
        f'🥦 <b>Ингредиенты:</b>\n{ingredients}\n\n',
        parse_mode='HTML',  # Включаем HTML для форматирования
        reply_markup=reply_markup
    )
    logger.info('Сообщение с рецептом успешно отправлено.')


async def send_random_recipe(
    update: Update, category: str, recipes: list[dict]
) -> None:
    '''Отправляет случайный рецепт из категории.'''
    message = get_safe_message_from_update(update)

    # Выбираем случайный ID рецепта
    random_recipe_info = random.choice(recipes)
    recipe_id = random_recipe_info['id']

    with get_session_context() as session:
        # Загружаем рецепт с нужными связями
        recipe = (
            session.query(Recipe)
            .filter_by(id=recipe_id)
            .options(
                joinedload(Recipe.ingredients),
                joinedload(Recipe.video),
                joinedload(Recipe.category),
            )
            .first()
        )

        if not recipe:
            await message.reply_text('❌ Рецепт не найден.')
            return

        # Отправляем видео, если есть
        if recipe.video and recipe.video.video_url:
            await message.reply_video(recipe.video.video_url)

        # Формируем список ингредиентов
        ingredients_text = '\n'.join(
            f"- {ingredient.name}" for ingredient in recipe.ingredients
        )

        # Формируем текст сообщения
        text = (
            f'Вот случайный рецепт из категории "{category}":\n\n'
            f'🍽 *{recipe.title}*\n\n'
            f'📝 {recipe.description or ""}\n\n'
            f'🥦 *Ингредиенты:*\n{ingredients_text}'
        )

        await message.reply_text(text, parse_mode='Markdown')


def get_message_from_update(update: Update) -> Message:
    if update.message:
        message = get_safe_message_from_update(update)
        return message
    elif update.callback_query and update.callback_query.message:
        return cast(Message, update.callback_query.message)
    else:
        raise ValueError("❌ Невозможно получить message из update.")


async def send_recipe_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    recipes: list[dict],
    page: int = 0,
    edit: bool = False
):
    '''Отправляет список рецептов с кнопками, поддерживая пагинацию.'''
    # Сохраняем список рецептов в context.user_data
    message = get_message_from_update(update)
    user_data = get_safe_user_data(context)
    user_data['recipes'] = recipes
    user_data['is_editing'] = edit

    recipes_per_page = RECIPES_PER_PAGE
    start = page * recipes_per_page
    end = start + recipes_per_page
    current_recipes = recipes[start:end]

    # Создаём кнопки для текущей страницы
    keyboard = [
        [InlineKeyboardButton(
            str(recipe['title']),
            callback_data=(
                f'edit_recipe_{recipe["id"]}' if edit
                else f'recipe_{recipe["id"]}'
            )
        )] for recipe in current_recipes
    ]

    # Добавляем кнопку 'Далее', если есть ещё рецепты
    logger.info(f'Отправляем список рецептов. Текущая страница: {page}')
    if end < len(recipes):
        keyboard.append(
            [InlineKeyboardButton('Далее', callback_data=f'next_{page + 1}')]
        )
        logger.debug('Добавлена кнопка "Далее".')
    # Добавляем кнопку 'Назад', если это не первая страница
    if page > 0:
        keyboard.append(
            [InlineKeyboardButton('Назад', callback_data=f'prev_{page - 1}')]
        )
        logger.debug('Добавлена кнопка "Назад".')
    reply_markup = InlineKeyboardMarkup(keyboard)

    if message:
        await message.reply_text(
            'Выберите рецепт:',
            reply_markup=reply_markup
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            'Выберите рецепт:',
            reply_markup=reply_markup
        )
