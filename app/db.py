"""数据库引擎与会话。"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine

from .config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def init_db() -> None:
    # 确保模型已注册（auth 里的账号/会话表也要建出来）
    from . import auth, models  # noqa: F401

    SQLModel.metadata.create_all(engine)


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
