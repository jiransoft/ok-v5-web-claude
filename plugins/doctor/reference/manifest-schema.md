# doctor.json 매니페스트 스키마 (v1)

각 플러그인이 **자기 요구사항을 자기 루트에 소유한다**. `doctor` 는 이 파일만 읽어 점검하며,
플러그인별 지식을 하드코딩하지 않는다 — 그래서 플러그인이 바뀌면 그 플러그인만 고치면 된다.

위치: `plugins/<플러그인>/doctor.json` (플러그인 루트, `.claude-plugin/` 밖)

## 목차

- [최소 형태](#최소-형태)
- [필드](#필드)
- [작성 규칙](#작성-규칙)

## 최소 형태

점검할 게 없는 플러그인도 매니페스트를 둔다. 없으면 `doctor` 가 "매니페스트 누락"으로 잡는다.

```json
{ "schema": 1, "plugin": "visualize", "setup": null }
```

## 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `schema` | number | 스키마 버전. 현재 `1` |
| `plugin` | string | 플러그인 이름. 디렉토리명·`plugin.json.name` 과 일치해야 한다 |
| `setup` | string\|null | 셋업 슬래시 명령. 조치 안내에 쓴다. 설정이 없는 플러그인은 `null` |
| `config` | object | `.claude/plugins.json` 섹션 요구사항. 설정을 읽지 않으면 생략 |
| `files` | array | 토큰·크리덴셜 등 로컬 파일 요구사항 |
| `commands` | array | 외부 CLI 의존성 |
| `mcp` | array | MCP 서버 의존성 |
| `hooks` | array | 플러그인이 배선하는 훅 |
| `settings` | array | `~/.claude/settings.json` 에 있어야 하는 값 |

### `config`

```json
"config": {
  "key": "jira-tools",
  "required": ["projectKey", "baseUrl"],
  "optional": ["cloudId", "assignee"]
}
```

`key` 는 섹션 이름이다. `required` 가 비면 설정 없이도 동작한다는 뜻이고, 이때 누락은 경고가 아니다.
`required`·`optional` 에 없는 키가 섹션에 있으면 오타·구 키로 보고 경고한다.

### `files`

```json
"files": [
  { "path": "~/.jira-token", "required": true, "mode": "600", "usedBy": "전체", "hint": "https://id.atlassian.com/manage-profile/security/api-tokens" }
]
```

`mode` 는 기대 권한(8진수 문자열). 더 느슨하면 경고한다 — 토큰 파일이 `644` 인 상태를 잡는 게 목적이다.

### `commands`

```json
"commands": [
  { "name": "jq", "required": true, "install": "brew install jq" },
  { "name": "node", "required": true, "minVersion": 20, "install": "brew install node" },
  { "name": "pandoc", "required": false, "install": "brew install pandoc", "note": "미설치 시 {code} 폴백" }
]
```

`minVersion` 은 정수 major 만 본다. `required: false` 는 없어도 폴백이 있다는 뜻이라 정보로만 표시한다.

### `mcp`

```json
"mcp": [ { "server": "playwright", "required": true, "usedBy": "verify-stack" } ]
```

`~/.claude.json` 의 `mcpServers`(전역·프로젝트)에 해당 이름이 있는지 본다.
**MCP 없이 CLI·REST 로 동작하는 스킬은 여기 쓰지 않는다** — 실제 `mcp__<server>__*` 도구를 쓰는 스킬만 적는다.

### `hooks`

```json
"hooks": [ { "event": "UserPromptSubmit", "script": "hooks/commit-router.sh", "selfTest": "hooks/test-commit-router.sh" } ]
```

경로는 플러그인 루트 기준 상대경로다. `selfTest` 가 있으면 `--deep` 에서 실행해 종료코드를 본다.

### `settings`

```json
"settings": [ { "path": "statusLine.command", "contains": "hud/hud.mjs", "fix": "/hud:setup" } ]
```

`path` 는 점 표기 경로다. 값에 `contains` 문자열이 없으면 `fix` 를 조치로 안내한다.

## 작성 규칙

- **문서를 베끼지 말고 스킬을 보고 쓴다.** README 표는 낡을 수 있다 — `allowed-tools` 와 SKILL.md 본문이 근거다
- 필수/선택 구분은 **그게 없을 때 스킬이 멈추는지**로 정한다. 물어보고 진행하면 선택이다
- 민감값은 매니페스트에 절대 넣지 않는다. 경로·이름만 쓴다
- 키를 추가·개명하면 이 파일과 `/preflight` 대조 대상이 함께 갱신되는지 확인한다
