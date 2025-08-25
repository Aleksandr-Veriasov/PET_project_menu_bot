from enum import IntEnum


class EditRecipeState(IntEnum):
    CHOOSE_FIELD = 1
    WAIT_TITLE = 2
    CONFIRM = 3


class DeleteRecipeState(IntEnum):
    CONFIRM = 1
    CANCEL = 2


class SaveRecipeState(IntEnum):
    CHOOSE_CATEGORY = 0
    WAIT_SAVE = 1
    WAIT_CANCEL = 2
