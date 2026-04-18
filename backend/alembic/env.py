"""
Alembic 环境配置

用于数据库迁移
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# 导入应用配置和模型
from app.config import settings

# 导入 AI 配置模型（确保表被注册到 metadata）
from app.infrastructure.database import models_ai_config  # noqa: F401
from app.infrastructure.database.models import Base

# Alembic Config 对象
config = context.config

# 设置数据库 URL
config.set_main_option("sqlalchemy.url", settings.database_url_sync)

# 配置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 目标元数据（用于 autogenerate）
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    在"离线"模式下运行迁移

    这将直接生成 SQL 而不连接数据库
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    在"在线"模式下运行迁移

    创建引擎并关联连接
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"client_encoding": "utf8"},
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
