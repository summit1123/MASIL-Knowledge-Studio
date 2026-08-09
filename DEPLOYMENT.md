# MASIL MCP deployment

## Public connector

- Name: `MASIL Knowledge Studio`
- MCP URL: `https://masil-mcp.summit1123.co.kr/mcp`
- Authentication: OAuth 2.0 Authorization Code, confidential client, PKCE S256
- OAuth client ID: `masil-claude-team`
- OAuth client secret: local `.env` value `MASIL_OAUTH_CLIENT_SECRET`
- Claude callback: `https://claude.ai/api/mcp/auth_callback`

비밀값과 Cloudflare 터널 토큰은 저장소에 넣지 않는다. `.env`와 `~/.cloudflared/masil-mcp.token`은 각각 권한 600으로 로컬에만 보관한다.

## Local services

두 LaunchAgent가 로그인 시 자동 실행되고 종료 시 다시 시작한다.

- `co.summit.masil-mcp.server` — FastMCP, port 8000
- `co.summit.masil-mcp.cloudflared` — dedicated `masil-mcp` tunnel

설정 파일:

- `~/Library/LaunchAgents/co.summit.masil-mcp.server.plist`
- `~/Library/LaunchAgents/co.summit.masil-mcp.cloudflared.plist`

로그:

- `~/Library/Logs/MASIL/mcp.out.log`
- `~/Library/Logs/MASIL/mcp.err.log`
- `~/Library/Logs/MASIL/cloudflared.out.log`
- `~/Library/Logs/MASIL/cloudflared.err.log`

재시작:

```bash
launchctl kickstart -k gui/$(id -u)/co.summit.masil-mcp.server
launchctl kickstart -k gui/$(id -u)/co.summit.masil-mcp.cloudflared
```

포트 8000을 사용하던 기존 `com.gimdonghyeon.diary-api-8000` LaunchAgent는 충돌을 막기 위해 disable 상태다. 복구가 필요하면 MASIL 서버를 먼저 내린 뒤 다음 명령으로 다시 활성화한다.

```bash
launchctl enable gui/$(id -u)/com.gimdonghyeon.diary-api-8000
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.gimdonghyeon.diary-api-8000.plist
```

## Verification

```bash
ruby knowledge/scripts/verify_knowledge.rb
.venv/bin/pytest
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS https://masil-mcp.summit1123.co.kr/healthz
.venv/bin/python scripts/check_oauth.py https://masil-mcp.summit1123.co.kr
```

`check_oauth.py`는 OAuth code 교환, client secret, PKCE, MCP 도구 목록, 검색, 답변 재료, 실제 캡처 이미지 반환을 한 번에 확인한다.

## Operational boundary

현재 OAuth authorization code와 access token 저장소는 프로세스 메모리 안에 있다. 서버 재시작 후 이미 연결된 Claude 커넥터가 재인증을 요구할 수 있다. 단기 발표 준비에는 충분하지만 장기 상시 운영 전에는 영속 저장소와 토큰 폐기 정책을 추가해야 한다.
