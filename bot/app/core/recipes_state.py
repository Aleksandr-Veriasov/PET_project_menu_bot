from enum import IntEnum


class EDRState(IntEnum):  # EditDeleteRecipeState
    CHOOSE_FIELD = 0
    WAIT_TITLE = 1
    CONFIRM_TITLE = 2
    CONFIRM_DELETE = 3
    CONFIRM_CHANGE_CATEGORY = 4


class SaveRecipeState(IntEnum):
    CHOOSE_CATEGORY = 0
