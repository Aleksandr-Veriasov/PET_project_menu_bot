import logging
from typing import Optional
from contextlib import suppress
from redis.asyncio import Redis

from packages.db.repository import RecipeRepository
from packages.redis.repository import (
    RecipeCacheRepository
)
from packages.redis.utils import acquire_lock, release_lock
from packages.redis.keys import RedisKeys
from packages.redis import ttl
from packages.db.database import Database

logger = logging.getLogger(__name__)


class RecipeService:
    def __init__(self, db: Database, redis: Redis):
        self.db = db
        self.redis = redis

    async def get_all_recipes_ids_and_titles(
        self, user_id: int, category_id: int
    ) -> list[dict[str, int | str]]:
        """
        Получить все id и названия рецептов пользователя.
        """
        # 1) пробуем Redis
        cached = await RecipeCacheRepository.get_all_recipes_ids_and_titles(
            self.redis, user_id, category_id
        )
        logger.info(f'👉 User {user_id} category {category_id} '
                    f'recipes ids and titles from cache: {cached}')
        if cached is not None:
            return cached

        # 2) БД
        lock_key = RedisKeys.user_init_lock(user_id=user_id)
        token: Optional[str] = await acquire_lock(
                self.redis, lock_key, ttl.LOCK
            )
        try:
            async with self.db.session() as self.session:
                rows = await RecipeRepository.get_all_recipes_ids_and_titles(
                    self.session, user_id, category_id
                )
                await RecipeCacheRepository.set_all_recipes_ids_and_titles(
                    self.redis, user_id, category_id, rows
                )
        finally:
            if token:
                with suppress(Exception):
                    await release_lock(self.redis, lock_key, token)
        return rows
