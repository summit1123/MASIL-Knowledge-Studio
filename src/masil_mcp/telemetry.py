from __future__ import annotations

import hashlib
import logging
import os
import secrets
import sqlite3
import time
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext


logger = logging.getLogger(__name__)


def default_runtime_dir() -> Path:
    configured = os.getenv("MASIL_RUNTIME_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".local" / "share" / "masil-mcp"


class TelemetryStore:
    """Privacy-preserving aggregate tool telemetry.

    Tool arguments, prompts, answer bodies, evidence bodies, and credentials are
    deliberately absent from the schema.
    """

    def __init__(self, path: Path | None = None):
        self.path = path or default_runtime_dir() / "telemetry.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.path.parent.chmod(0o700)
        except OSError:
            pass
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tool_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurred_at TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    route TEXT,
                    status TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    result_count INTEGER,
                    capture_count INTEGER NOT NULL DEFAULT 0,
                    session_hash TEXT,
                    corpus_fingerprint TEXT,
                    server_version TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_tool_events_time ON tool_events(occurred_at);
                CREATE INDEX IF NOT EXISTS idx_tool_events_tool ON tool_events(tool_name);
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurred_at TEXT NOT NULL,
                    rating TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    session_hash TEXT
                );
                """
            )
            row = connection.execute("SELECT value FROM metadata WHERE key='session_salt'").fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO metadata(key, value) VALUES('session_salt', ?)",
                    (secrets.token_hex(32),),
                )
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    def _session_salt(self) -> str:
        with self._connect() as connection:
            row = connection.execute("SELECT value FROM metadata WHERE key='session_salt'").fetchone()
        return str(row["value"])

    def hash_session(self, session_id: str | None) -> str | None:
        if not session_id:
            return None
        return hashlib.sha256(f"{self._session_salt()}:{session_id}".encode()).hexdigest()[:16]

    def record_tool_event(
        self,
        *,
        tool_name: str,
        route: str | None,
        status: str,
        duration_ms: float,
        result_count: int | None,
        capture_count: int,
        session_id: str | None,
        corpus_fingerprint: str | None,
        server_version: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tool_events(
                    occurred_at, tool_name, route, status, duration_ms,
                    result_count, capture_count, session_hash, corpus_fingerprint, server_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    tool_name,
                    route,
                    status,
                    round(duration_ms, 3),
                    result_count,
                    capture_count,
                    self.hash_session(session_id),
                    corpus_fingerprint,
                    server_version,
                ),
            )

    def record_feedback(self, rating: str, reason: str, session_id: str | None = None) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO feedback(occurred_at, rating, reason, session_hash) VALUES (?, ?, ?, ?)",
                (
                    datetime.now(timezone.utc).isoformat(),
                    rating,
                    reason,
                    self.hash_session(session_id),
                ),
            )

    def summary(self, days: int = 7) -> dict[str, Any]:
        if days < 1 or days > 90:
            raise ValueError("days must be between 1 and 90")
        cutoff = datetime.fromtimestamp(time.time() - days * 86400, timezone.utc).isoformat()
        with self._connect() as connection:
            totals = connection.execute(
                """
                SELECT COUNT(*) AS calls,
                       SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) AS successes,
                       ROUND(AVG(duration_ms), 1) AS average_duration_ms,
                       SUM(capture_count) AS captures_shown,
                       COUNT(DISTINCT session_hash) AS anonymous_sessions
                FROM tool_events WHERE occurred_at >= ?
                """,
                (cutoff,),
            ).fetchone()
            tools = connection.execute(
                """
                SELECT tool_name, COUNT(*) AS calls,
                       SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) AS errors,
                       ROUND(AVG(duration_ms), 1) AS average_duration_ms,
                       SUM(capture_count) AS captures_shown
                FROM tool_events WHERE occurred_at >= ?
                GROUP BY tool_name ORDER BY calls DESC, tool_name
                """,
                (cutoff,),
            ).fetchall()
            routes = connection.execute(
                """
                SELECT route, COUNT(*) AS calls
                FROM tool_events WHERE occurred_at >= ? AND route IS NOT NULL
                GROUP BY route ORDER BY calls DESC, route
                """,
                (cutoff,),
            ).fetchall()
            feedback = connection.execute(
                """
                SELECT rating, reason, COUNT(*) AS count
                FROM feedback WHERE occurred_at >= ?
                GROUP BY rating, reason ORDER BY count DESC, rating, reason
                """,
                (cutoff,),
            ).fetchall()
        calls = int(totals["calls"] or 0)
        successes = int(totals["successes"] or 0)
        return {
            "window_days": days,
            "calls": calls,
            "success_rate": round(successes / calls, 4) if calls else None,
            "average_duration_ms": totals["average_duration_ms"],
            "captures_shown": int(totals["captures_shown"] or 0),
            "anonymous_sessions": int(totals["anonymous_sessions"] or 0),
            "tools": [dict(row) for row in tools],
            "routes": [dict(row) for row in routes],
            "feedback": [dict(row) for row in feedback],
            "privacy": "No prompts, tool arguments, answer text, evidence body, credentials, or personal identity are stored.",
        }


def _structured_payload(result: Any) -> Mapping[str, Any]:
    payload = getattr(result, "structured_content", None)
    return payload if isinstance(payload, Mapping) else {}


def _count_captures(payload: Mapping[str, Any]) -> int:
    for key in ("captures", "evidence_captures", "recommended_captures"):
        value = payload.get(key)
        if isinstance(value, list):
            return len(value)
    return 0


class PrivacyTelemetryMiddleware(Middleware):
    def __init__(
        self,
        store: TelemetryStore,
        *,
        corpus_fingerprint: str,
        server_version: str,
    ):
        self.store = store
        self.corpus_fingerprint = corpus_fingerprint
        self.server_version = server_version

    @staticmethod
    def _session_id(context: MiddlewareContext) -> str | None:
        fastmcp_context = context.fastmcp_context
        if fastmcp_context is None or fastmcp_context.request_context is None:
            return None
        try:
            return fastmcp_context.session_id
        except RuntimeError:
            return None

    async def on_call_tool(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        tool_name = str(getattr(context.message, "name", "unknown"))
        started = time.perf_counter()
        try:
            result = await call_next(context)
        except Exception:
            try:
                self.store.record_tool_event(
                    tool_name=tool_name,
                    route=None,
                    status="error",
                    duration_ms=(time.perf_counter() - started) * 1000,
                    result_count=None,
                    capture_count=0,
                    session_id=self._session_id(context),
                    corpus_fingerprint=self.corpus_fingerprint,
                    server_version=self.server_version,
                )
            except Exception:
                logger.exception("Failed to record privacy telemetry for an errored tool call")
            raise

        payload = _structured_payload(result)
        routing = payload.get("routing")
        route = routing.get("route") if isinstance(routing, Mapping) else None
        result_count = payload.get("result_count")
        try:
            self.store.record_tool_event(
                tool_name=tool_name,
                route=str(route) if route else None,
                status="success",
                duration_ms=(time.perf_counter() - started) * 1000,
                result_count=int(result_count) if isinstance(result_count, int) else None,
                capture_count=_count_captures(payload),
                session_id=self._session_id(context),
                corpus_fingerprint=self.corpus_fingerprint,
                server_version=self.server_version,
            )
        except Exception:
            logger.exception("Failed to record privacy telemetry for a successful tool call")
        return result
