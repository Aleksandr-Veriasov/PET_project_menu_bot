from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Optional, TypeAlias, TypedDict

from telegram.ext import Application, CallbackContext, ExtBot, JobQueue

from app.db.database import Database


@dataclass(slots=True)
class AppState:
    db: Database
    cleanup_task: Optional[asyncio.Task[None]] = None


class BotData(TypedDict):
    state: AppState


PTBContext: TypeAlias = CallbackContext[
    ExtBot[None],
    dict[Any, Any],
    dict[Any, Any],
    BotData,
]

PTBApp: TypeAlias = Application[
    ExtBot[None],
    PTBContext,
    dict[Any, Any],           # user_data
    dict[Any, Any],           # chat_data
    BotData,                  # bot_data
    JobQueue[PTBContext],
]
