"""数据库服务，负责连接测试与基础查询。"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Iterable, List

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from ..state import DatabaseSettings


class DatabaseError(Exception):
    """数据库操作异常。"""


def build_engine(settings: DatabaseSettings) -> Engine:
    """根据配置创建 SQLAlchemy Engine。"""

    return create_engine(settings.dsn, future=True)


@contextmanager
def session_scope(engine: Engine):
    """提供一个简单的连接上下文。"""

    connection = engine.connect()
    try:
        yield connection
    finally:
        connection.close()


def test_connection(settings: DatabaseSettings) -> bool:
    """测试数据库连接是否成功。"""

    engine = build_engine(settings)
    try:
        with session_scope(engine) as conn:
            conn.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError as exc:  # pragma: no cover - 依赖外部服务
        raise DatabaseError(str(exc)) from exc


def initialize_schema(engine: Engine, statements: Iterable[str]) -> None:
    """执行建表语句或迁移。"""

    try:
        with session_scope(engine) as conn:
            for statement in statements:
                conn.execute(text(statement))
            conn.commit()
    except SQLAlchemyError as exc:  # pragma: no cover
        raise DatabaseError(str(exc)) from exc


def fetch_recent_runs(engine: Engine, *, limit: int = 20) -> List[Dict[str, Any]]:
    """获取最近的 Runs 记录。"""

    sql = text(
        """
        SELECT id, created_at, prompt, status, output_path
        FROM runs
        ORDER BY created_at DESC
        LIMIT :limit
        """
    )
    try:
        with session_scope(engine) as conn:
            result = conn.execute(sql, {"limit": limit})
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result]
    except SQLAlchemyError as exc:  # pragma: no cover - 外部数据库
        raise DatabaseError(str(exc)) from exc


def fetch_recent_uploads(engine: Engine, *, limit: int = 20) -> List[Dict[str, Any]]:
    """获取最近的上传记录。"""

    sql = text(
        """
        SELECT id, created_at, platform, status, response_payload
        FROM uploads
        ORDER BY created_at DESC
        LIMIT :limit
        """
    )
    try:
        with session_scope(engine) as conn:
            result = conn.execute(sql, {"limit": limit})
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result]
    except SQLAlchemyError as exc:  # pragma: no cover
        raise DatabaseError(str(exc)) from exc


__all__ = [
    "DatabaseError",
    "build_engine",
    "test_connection",
    "initialize_schema",
    "fetch_recent_runs",
    "fetch_recent_uploads",
]
