"""defaults, fk cascade, m2m unique & indexes

Revision ID: 9fa0fd5b2493
Revises: d0aaaedee870
Create Date: 2025-08-30 14:47:31.058651

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9fa0fd5b2493'
down_revision: Union[str, Sequence[str], None] = 'd0aaaedee870'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # --- created_at: DEFAULT now() ---
    for table in ("users", "admins", "recipes"):
        op.alter_column(
            table,
            "created_at",
            server_default=sa.text("now()"),
            existing_type=sa.DateTime(),  # тип не меняем
            existing_nullable=False,
        )

    # --- recipe_ingredients: удалить возможные дубли и добавить UNIQUE ---
    # (на всякий случай чистим дубли, если их нет — просто no-op)
    op.execute(
        """
        DELETE FROM recipe_ingredients a
        USING recipe_ingredients b
        WHERE a.id < b.id
          AND a.recipe_id = b.recipe_id
          AND a.ingredient_id = b.ingredient_id
        """
    )
    # добавить уникальность
    op.create_unique_constraint(
        "uq_recipe_ingredient",
        "recipe_ingredients",
        ["recipe_id", "ingredient_id"],
    )

    # индексы для связки
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_recipe_ingredients_recipe_id ON recipe_ingredients (recipe_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_recipe_ingredients_ingredient_id ON recipe_ingredients (ingredient_id)"
    )

    # --- полезные индексы, если их нет ---
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_videos_recipe_id ON videos (recipe_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_categories_slug ON categories (slug)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_recipes_title ON recipes (title)"
    )

    # --- recipes.user_id: перевешиваем FK на ON DELETE CASCADE ---
    # Находим имя текущего FK динамически
    fks = insp.get_foreign_keys("recipes")
    old_fk_name = None
    for fk in fks:
        if fk.get("referred_table") == "users" and fk.get("constrained_columns") == ["user_id"]:
            old_fk_name = fk.get("name")
            break
    if old_fk_name:
        op.drop_constraint(old_fk_name, "recipes", type_="foreignkey")

    op.create_foreign_key(
        "fk_recipes_user_id_users",
        source_table="recipes",
        referent_table="users",
        local_cols=["user_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # вернуть FK без CASCADE (NO ACTION)
    fks = insp.get_foreign_keys("recipes")
    for fk in fks:
        if fk.get("referred_table") == "users" and fk.get("constrained_columns") == ["user_id"]:
            op.drop_constraint(fk.get("name"), "recipes", type_="foreignkey")
            break
    op.create_foreign_key(
        "fk_recipes_user_id_users",
        source_table="recipes",
        referent_table="users",
        local_cols=["user_id"],
        remote_cols=["id"],
        ondelete=None,
    )

    # снять полезные индексы
    op.execute("DROP INDEX IF EXISTS ix_recipes_title")
    op.execute("DROP INDEX IF EXISTS ix_categories_slug")
    op.execute("DROP INDEX IF EXISTS ix_videos_recipe_id")
    op.execute("DROP INDEX IF EXISTS ix_recipe_ingredients_ingredient_id")
    op.execute("DROP INDEX IF EXISTS ix_recipe_ingredients_recipe_id")

    # снять UNIQUE с m2m
    op.drop_constraint("uq_recipe_ingredient", "recipe_ingredients", type_="unique")

    # убрать DEFAULT now() (типы не трогаем)
    for table in ("users", "admins", "recipes"):
        op.alter_column(
            table,
            "created_at",
            server_default=None,
            existing_type=sa.DateTime(),
            existing_nullable=False,
        )
