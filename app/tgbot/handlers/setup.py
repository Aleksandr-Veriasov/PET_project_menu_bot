import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.tgbot.handlers.recipes.delete_recipe import conversation_delete_recipe
from app.tgbot.handlers.recipes.edit_recipe import conversation_edit_recipe
from app.tgbot.handlers.recipes.pagination import handler_pagination
from app.tgbot.handlers.recipes.recipes_menu import (
    recipe_choice,
    recipes_from_category,
    recipes_menu,
    upload_recipe,
)
from app.tgbot.handlers.recipes.save_recipe import save_recipe_handlers
from app.tgbot.handlers.user import user_help, user_start
from app.tgbot.handlers.video import video_link

logger = logging.getLogger(__name__)

video_link_pattern = (
    r'(https?://)?(www\.)?'
    r'(youtube\.com|youtu\.be|tiktok\.com|instagram\.com|vimeo\.com)/\S+'
)


def setup_handlers(app: Application) -> None:
    """ Регистрирует все обработчики в приложении. """

    logger.info('Регистрация обработчиков...')
    app.add_handler(CommandHandler('start', user_start))
    app.add_handler(CommandHandler('help', user_help))
    # pattern='^edit_recipe_(\d+)$'
    app.add_handler(conversation_edit_recipe())
    # pattern='^delete_recipe_\d+$'
    app.add_handler(conversation_delete_recipe())
    # pattern='^save_recipe$'
    app.add_handler(save_recipe_handlers())
    app.add_handler(MessageHandler(
        filters.Regex(video_link_pattern) & filters.TEXT,
        video_link
    ))
    app.add_handler(CallbackQueryHandler(
        user_help, pattern='^help$'
    ))
    app.add_handler(CallbackQueryHandler(
        user_start, pattern='^start$'
    ))
    app.add_handler(CallbackQueryHandler(
        upload_recipe, pattern='^upload_recipe$'
    ))
    app.add_handler(CallbackQueryHandler(
        recipes_menu,
        pattern=r'^(recipes|recipe_random|recipe_edit)$'
    ))
    app.add_handler(CallbackQueryHandler(
        handler_pagination, pattern=r'^(next|prev)_\d+$'
    ))
    app.add_handler(CallbackQueryHandler(
        recipes_from_category,
        pattern=r'^(?:breakfast|main|salad)_recipes(?:_(?:random|edit))?$'
    ))
    app.add_handler(CallbackQueryHandler(
        recipe_choice,
        pattern=r'^(?:breakfast|main|salad)_(?:recipe|edit_recipe)_\d+$'
    ))

    logger.info('Все хендлеры зарегистрированы.')
