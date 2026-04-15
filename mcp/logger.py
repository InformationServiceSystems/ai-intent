"""MCPMessage model and SQLite persistence for the audit log."""

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel


class _SafeEncoder(json.JSONEncoder):
    """JSON encoder that converts sets to lists and handles other non-serializable types."""

    def default(self, obj):
        if isinstance(obj, set):
            return sorted(obj)
        if isinstance(obj, frozenset):
            return sorted(obj)
        return super().default(obj)


class MCPMessage(BaseModel):
    """A single inter-agent message in the MCP log."""

    id: str
    session_id: str
    timestamp: datetime
    direction: Literal["outbound", "inbound", "internal"]
    from_agent: str
    to_agent: str
    method: str
    payload: dict[str, Any]
    response_status: Literal["pending", "ok", "error", "constraint_violation", "forced_pass", "forced_block", "approved", "blocked"]
    constraint_flags: list[str]


class MCPLogger:
    """SQLite-backed logger for MCP messages."""

    def __init__(self, db_path: str = "data/sessions.db") -> None:
        """Initialize SQLite connection and create table if not exists."""
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS mcp_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                direction TEXT NOT NULL,
                from_agent TEXT NOT NULL,
                to_agent TEXT NOT NULL,
                method TEXT NOT NULL,
                payload TEXT NOT NULL,
                response_status TEXT NOT NULL,
                constraint_flags TEXT NOT NULL
            )"""
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_session ON mcp_messages(session_id)"
        )
        self._conn.commit()

    def log(self, message: MCPMessage) -> None:
        """Persist a single MCPMessage to the database."""
        with self._lock:
            self._conn.execute(
                "INSERT INTO mcp_messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    message.id,
                    message.session_id,
                    message.timestamp.isoformat(),
                    message.direction,
                    message.from_agent,
                    message.to_agent,
                    message.method,
                    json.dumps(message.payload, cls=_SafeEncoder, default=str),
                    message.response_status,
                    json.dumps(message.constraint_flags),
                ),
            )
            self._conn.commit()

    def get_session(self, session_id: str) -> list[MCPMessage]:
        """Return all messages for a session, ordered by timestamp ascending."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM mcp_messages WHERE session_id = ? ORDER BY timestamp ASC",
                (session_id,),
            ).fetchall()
        return [
            MCPMessage(
                id=r[0],
                session_id=r[1],
                timestamp=datetime.fromisoformat(r[2]),
                direction=r[3],
                from_agent=r[4],
                to_agent=r[5],
                method=r[6],
                payload=json.loads(r[7]),
                response_status=r[8],
                constraint_flags=json.loads(r[9]),
            )
            for r in rows
        ]

    def get_all_sessions(self) -> list[str]:
        """Return list of distinct session IDs, most recent first."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT DISTINCT session_id FROM mcp_messages ORDER BY timestamp DESC"
            ).fetchall()
        return [r[0] for r in rows]

    def clear_session(self, session_id: str) -> None:
        """Delete all messages for a given session ID."""
        with self._lock:
            self._conn.execute(
                "DELETE FROM mcp_messages WHERE session_id = ?", (session_id,)
            )
            self._conn.commit()


_logger_instance: MCPLogger | None = None
_logger_lock = threading.Lock()


def get_logger() -> MCPLogger:
    """Return the singleton MCPLogger instance."""
    global _logger_instance
    if _logger_instance is None:
        with _logger_lock:
            if _logger_instance is None:
                _logger_instance = MCPLogger()
    return _logger_instance


def build_message(
    session_id: str,
    direction: str,
    from_agent: str,
    to_agent: str,
    method: str,
    payload: dict,
    status: str = "ok",
    constraint_flags: list[str] | None = None,
) -> MCPMessage:
    """Construct an MCPMessage with auto-generated id and current timestamp."""
    return MCPMessage(
        id=str(uuid4()),
        session_id=session_id,
        timestamp=datetime.now(timezone.utc),
        direction=direction,
        from_agent=from_agent,
        to_agent=to_agent,
        method=method,
        payload=payload,
        response_status=status,
        constraint_flags=constraint_flags or [],
    )
