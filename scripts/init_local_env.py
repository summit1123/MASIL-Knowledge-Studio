from __future__ import annotations

import secrets
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"


def main() -> None:
    if ENV_FILE.exists():
        print(".env already exists; no changes made")
        return
    client_secret = secrets.token_urlsafe(42)
    static_token = secrets.token_urlsafe(42)
    content = f"""MASIL_HOST=0.0.0.0
MASIL_PORT=8000
MASIL_MCP_PATH=/mcp
MASIL_AUTH_MODE=oauth_client
MASIL_PUBLIC_URL=https://masil-mcp.summit1123.co.kr
MASIL_OAUTH_CLIENT_ID=masil-claude-team
MASIL_OAUTH_CLIENT_SECRET={client_secret}
MASIL_OAUTH_REDIRECT_URI=https://claude.ai/api/mcp/auth_callback
MASIL_STATIC_TOKEN={static_token}
"""
    ENV_FILE.write_text(content, encoding="utf-8")
    ENV_FILE.chmod(0o600)
    print("Created .env with mode oauth_client and private client credentials")


if __name__ == "__main__":
    main()

