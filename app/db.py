"""数据库引擎与会话。"""
from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine, text

from .config import settings

logger = logging.getLogger("bambu-spool")

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def _migrate_columns() -> None:
    """给已存在的表补加新列（SQLite 下 create_all 不会自动加列）。

    只动数据结构、不动现有数据；列已存在则跳过。服务于「老库升级」场景。
    """
    try:
        from sqlalchemy import inspect
    except Exception:  # pragma: no cover - sqlalchemy 必然可用
        return

    inspector = inspect(engine)
    if "spool" not in inspector.get_table_names():
        return

    # 需要补的列：表 -> [(列名, 类型, 默认值)]
    wanted = {
        "spool": [("price", "REAL NOT NULL DEFAULT 0.0")],
    }
    with engine.begin() as conn:
        for table, columns in wanted.items():
            existing = {c["name"] for c in inspector.get_columns(table)}
            for col, ddl in columns:
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))
                    logger.info("迁移：%s 表新增列 %s", table, col)


def init_db() -> None:
    # 确保模型已注册（auth 里的账号/会话表也要建出来）
    from . import auth, models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _migrate_columns()


@contextmanager
def session_scope() -> Iterator[Session]:
    """短事务。用 expire_on_commit=False，保证会话关闭后仍能安全读取对象属性。

    默认的 expire_on_commit=True 会让对象在 commit 后全部过期，一旦脱离会话
    再访问属性就会抛 DetachedInstanceError —— 而本项目的接口层正是把库里读出的
    对象直接序列化返回的。
    """
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """FastAPI 依赖注入用。"""
    with Session(engine, expire_on_commit=False) as session:
        yield session
