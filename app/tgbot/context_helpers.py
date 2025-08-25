from app.db.database import Database
from app.types import AppState, PTBContext


def get_db(context: PTBContext) -> Database:
    """
    Извлекает объект базы данных из состояния приложения.
    Если состояние некорректно, вызывает RuntimeError.
    """
    state = context.bot_data.get('state')
    if not isinstance(state, AppState):
        raise RuntimeError(
            'Некорректный или отсутствующий AppState в bot_data.'
        )
    return state.db
