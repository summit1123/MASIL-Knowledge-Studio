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

## Runtime state

- OAuth authorization code는 5분 동안 프로세스 메모리에만 존재한다.
- 발급된 access/refresh token은 기본적으로 `~/.local/share/masil-mcp/oauth.sqlite3`에 저장한다. 파일 권한은 600, 상위 디렉터리는 700이다.
- 익명 도구 사용 통계는 `~/.local/share/masil-mcp/telemetry.sqlite3`에 저장한다. 질문·답변·도구 인자는 저장하지 않는다.
- 위치를 바꾸려면 `MASIL_RUNTIME_DIR`, `MASIL_OAUTH_DB_PATH` 환경 변수를 사용한다.
- 서버 재시작은 기존 access/refresh token을 무효화하지 않는다. connector URL과 OAuth client가 같으면 팀원은 커넥터를 다시 등록하지 않는다.
- 도구 스키마가 바뀐 직후 Claude의 현재 대화가 옛 목록을 보유하면 새 대화를 열어 재발견한다. 커넥터 삭제·재등록과는 다르다.
- 운영자가 연결을 강제로 폐기할 때는 서버를 내린 상태에서 OAuth DB를 별도 백업한 뒤 해당 token row를 폐기하는 운영 절차를 사용한다.
