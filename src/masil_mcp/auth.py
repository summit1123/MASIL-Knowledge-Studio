from __future__ import annotations

import os
from typing import Any

from fastmcp.server.auth import StaticTokenVerifier
from fastmcp.server.auth.providers.github import GitHubProvider
from fastmcp.server.auth.providers.in_memory import InMemoryOAuthProvider
from mcp.server.auth.settings import ClientRegistrationOptions
from mcp.shared.auth import OAuthClientInformationFull


def build_auth(mode: str | None = None) -> Any | None:
    """Build a FastMCP 2 auth provider from environment settings.

    ``oauth_client`` is deliberately small and restart-local. It uses a fixed
    confidential OAuth client for the Claude callback, so only teammates with
    the configured client secret can exchange an authorization code. GitHub is
    available for deployments that need durable user identity.
    """

    mode = (mode or os.getenv("MASIL_AUTH_MODE", "none")).strip().lower()
    if mode == "none":
        return None

    if mode == "static":
        token = os.getenv("MASIL_STATIC_TOKEN", "").strip()
        if len(token) < 24:
            raise ValueError("MASIL_STATIC_TOKEN must contain at least 24 characters")
        return StaticTokenVerifier(
            tokens={
                token: {
                    "client_id": "masil-team",
                    "scopes": ["masil:read"],
                }
            },
            required_scopes=["masil:read"],
        )

    public_url = os.getenv("MASIL_PUBLIC_URL", "https://masil-mcp.summit1123.co.kr").rstrip("/")

    if mode == "oauth_client":
        client_id = os.getenv("MASIL_OAUTH_CLIENT_ID", "").strip()
        client_secret = os.getenv("MASIL_OAUTH_CLIENT_SECRET", "").strip()
        redirect_uri = os.getenv(
            "MASIL_OAUTH_REDIRECT_URI",
            "https://claude.ai/api/mcp/auth_callback",
        ).strip()
        if not client_id or len(client_secret) < 24:
            raise ValueError(
                "MASIL_OAUTH_CLIENT_ID and a 24+ character MASIL_OAUTH_CLIENT_SECRET are required"
            )
        provider = InMemoryOAuthProvider(
            base_url=public_url,
            client_registration_options=ClientRegistrationOptions(
                enabled=False,
                valid_scopes=["masil:read"],
                default_scopes=["masil:read"],
            ),
            required_scopes=["masil:read"],
        )
        provider.clients[client_id] = OAuthClientInformationFull(
            client_id=client_id,
            client_secret=client_secret,
            client_name="MASIL Claude Team",
            redirect_uris=[redirect_uri],
            token_endpoint_auth_method="client_secret_post",
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            scope="masil:read",
        )
        return provider

    if mode == "github":
        client_id = os.getenv("MASIL_GITHUB_CLIENT_ID", "").strip()
        client_secret = os.getenv("MASIL_GITHUB_CLIENT_SECRET", "").strip()
        if not client_id or not client_secret:
            raise ValueError("MASIL_GITHUB_CLIENT_ID and MASIL_GITHUB_CLIENT_SECRET are required")
        return GitHubProvider(
            client_id=client_id,
            client_secret=client_secret,
            base_url=public_url,
            issuer_url=public_url,
            required_scopes=["user"],
            allowed_client_redirect_uris=[
                "https://claude.ai/api/mcp/auth_callback",
                "http://localhost:*",
                "http://127.0.0.1:*",
            ],
        )

    raise ValueError("MASIL_AUTH_MODE must be one of: none, static, oauth_client, github")

