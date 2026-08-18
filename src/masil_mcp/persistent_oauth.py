from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from fastmcp.server.auth.providers.in_memory import InMemoryOAuthProvider
from mcp.server.auth.provider import AccessToken, AuthorizationCode, RefreshToken
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from .telemetry import default_runtime_dir


class PersistentOAuthProvider(InMemoryOAuthProvider):
    """FastMCP's small OAuth provider with restart-safe bearer-token storage.

    Authorization codes stay short-lived in memory. Access and refresh tokens
    are persisted in a mode-0600 SQLite file so an already connected Claude
    client can continue after routine server restarts.
    """

    def __init__(self, *args: Any, storage_path: Path | None = None, **kwargs: Any):
        self.storage_path = storage_path or default_runtime_dir() / "oauth.sqlite3"
        self._state_ready = False
        super().__init__(*args, **kwargs)
        self._initialize_storage()
        self._load_tokens()
        self._state_ready = True

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.storage_path, timeout=5)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _initialize_storage(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.storage_path.parent.chmod(0o700)
        except OSError:
            pass
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS oauth_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        try:
            self.storage_path.chmod(0o600)
        except OSError:
            pass

    def _load_tokens(self) -> None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM oauth_state WHERE key='tokens'"
            ).fetchone()
        if row is None:
            return
        payload = json.loads(row[0])
        self.access_tokens = {
            token: AccessToken.model_validate(value)
            for token, value in payload.get("access_tokens", {}).items()
        }
        self.refresh_tokens = {
            token: RefreshToken.model_validate(value)
            for token, value in payload.get("refresh_tokens", {}).items()
        }
        self._access_to_refresh_map = dict(payload.get("access_to_refresh", {}))
        self._refresh_to_access_map = dict(payload.get("refresh_to_access", {}))

    def _persist_tokens(self) -> None:
        if not self._state_ready:
            return
        payload = {
            "access_tokens": {
                token: value.model_dump(mode="json")
                for token, value in self.access_tokens.items()
            },
            "refresh_tokens": {
                token: value.model_dump(mode="json")
                for token, value in self.refresh_tokens.items()
            },
            "access_to_refresh": self._access_to_refresh_map,
            "refresh_to_access": self._refresh_to_access_map,
        }
        serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO oauth_state(key, value) VALUES('tokens', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
                """,
                (serialized,),
            )

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: AuthorizationCode,
    ) -> OAuthToken:
        token = await super().exchange_authorization_code(client, authorization_code)
        self._persist_tokens()
        return token

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        token = await super().exchange_refresh_token(client, refresh_token, scopes)
        self._persist_tokens()
        return token

    def _revoke_internal(
        self,
        access_token_str: str | None = None,
        refresh_token_str: str | None = None,
    ) -> None:
        super()._revoke_internal(
            access_token_str=access_token_str,
            refresh_token_str=refresh_token_str,
        )
        self._persist_tokens()
