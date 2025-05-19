import logging
import random

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import ContextTypes

from app.db.models import Recipe
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
    update: Update, category: str, recipes: list[Recipe]
) -> None:
    '''Отправляет случайный рецепт из категории.'''
    random_recipe = random.choice(recipes)
    video = random_recipe.video
    message = get_safe_message_from_update(update)

    if video:
        # Отправляем видео пользователю
        await message.reply_video(video.video_url)

    ingredients_text = '\n'.join(
        f'- {ingredient.name}' for ingredient in random_recipe.ingredients
    )

    text = (
        f'Вот случайный рецепт из категории "{category}":\n\n'
        f'🍽 *{random_recipe.title}*\n\n'
        f'📝 {random_recipe.description}\n\n'
        f'🥦 *Ингредиенты:*\n{ingredients_text}'
    )

    await message.reply_text(text, parse_mode='Markdown')


async def send_recipe_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    recipes: list[Recipe],
    page=0,
    edit=False
):
    '''Отправляет список рецептов с кнопками, поддерживая пагинацию.'''
    # Сохраняем список рецептов в context.user_data
    user_data = get_safe_user_data(context)
    user_data['recipes'] = recipes

    recipes_per_page = RECIPES_PER_PAGE
    start = page * recipes_per_page
    end = start + recipes_per_page
    current_recipes = recipes[start:end]

    # Создаём кнопки для текущей страницы
    keyboard = [
        [InlineKeyboardButton(
            str(recipe.title),
            callback_data=(
                f'edit_recipe_{recipe.id}' if edit else f'recipe_{recipe.id}'
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

    message = get_safe_message_from_update(update)
    if message:
        await message.reply_text(
            'Выберите рецепт:',
            reply_markup=reply_markup
        )
    elif update.callback_query:
        await message.edit_text(
            'Выберите рецепт:',
            reply_markup=reply_markup
        )
