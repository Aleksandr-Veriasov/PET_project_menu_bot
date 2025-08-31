from typing import Any

from bot.app.core.types import AppState, PTBContext


def get_db(context: PTBContext) -> Any:
    """
    Извлекает объект базы данных из состояния приложения.
    Если состояние некорректно, вызывает RuntimeError.
    """
    state = context.application.bot_data.get('state')
    if not isinstance(state, AppState):
        raise RuntimeError(
            'Некорректный или отсутствующий AppState в bot_data.'
        )
    return state.db
