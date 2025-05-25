import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.handlers.buttons import (
    handle_button_click,
    handle_button_click_recipe,
    handle_confirm_changes,
)
from app.handlers.pagination import handle_recipe_pagination
from app.handlers.recipes import (
    handle_category_choice,
    handle_confirm_delete,
    handle_edit_delete_recipe,
    handle_recipe_choice,
)
from app.handlers.start import handle_help, start
from app.handlers.video import handle_video_link
from app.utils.recipe_edit import edit_recipe_conv

logger = logging.getLogger(__name__)

video_link_pattern = (
    r'(https?://)?(www\.)?'
    r'(youtube\.com|youtu\.be|tiktok\.com|instagram\.com|vimeo\.com)/\S+'
)


def setup_handlers(app: Application) -> None:
    ''' Регистрирует все обработчики в приложении. '''

    logger.info('Регистрация обработчиков...')

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', handle_help))
    app.add_handler(edit_recipe_conv)

    app.add_handler(MessageHandler(
        filters.Regex(video_link_pattern) & filters.TEXT,
        handle_video_link
    ))

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(
            '^(Рецепты|Загрузить|Случайное блюдо|Редактировать рецепты)$'
        ),
        handle_button_click
    ))

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(
            r'^(Завтрак|Основное блюдо|Салат|Случайный завтрак|'
            r'Случайное горячее|Случайный салат|Изменить завтрак|'
            r'Изменить основное блюдо|Изменить салат)$'
        ),
        handle_button_click_recipe
    ))

    app.add_handler(CallbackQueryHandler(
        handle_confirm_changes,
        pattern='^(save_recipe|discard_recipe)$'
    ))

    app.add_handler(CallbackQueryHandler(
        handle_category_choice,
        pattern='^(breakfast|main_course|salad)$'
    ))

    app.add_handler(CallbackQueryHandler(
        handle_recipe_choice,
        pattern='^recipe_|edit_recipe_'
    ))

    app.add_handler(CallbackQueryHandler(
        handle_recipe_pagination,
        pattern='^(next|prev)_'
    ))

    app.add_handler(CallbackQueryHandler(
        handle_edit_delete_recipe,
        pattern='^(redact_recipe_|delete_recipe_)'
    ))

    app.add_handler(CallbackQueryHandler(
        handle_confirm_delete,
        pattern='^(confirm_delete_|cancel_delete_)'
    ))

    logger.info('Все хендлеры зарегистрированы.')
