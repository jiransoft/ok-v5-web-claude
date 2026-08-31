---
name: setup
description: hud statusline을 사용자 Claude Code 설정에 활성화합니다. 플러그인은 메인 statusLine을 자동으로 켤 수 없으므로, 이 셋업이 안정 런처 설치와 settings.json 배선을 대신 수행합니다.
when_to_use: 사용자가 "hud 셋업", "hud 활성화", "상태줄 켜줘", "statusline 설정", "hud setup", "hud 상태줄 적용" 등을 요청하거나, hud 플러그인 설치 직후 활성화가 필요할 때 사용한다.
argument-hint: "[--help]"
allowed-tools: Bash(node *), Read
---

# hud 셋업

hud statusline을 사용자 환경에 활성화한다.

## 배경

Claude Code는 플러그인이 메인 `statusLine`을 자동으로 켜는 것을 지원하지 않는다(플러그인 `settings.json`에서는 `agent`·`subagentStatusLine`만 인정됨). 따라서 설치만으로는 statusline이 켜지지 않으며, 이 셋업이 사용자 `~/.claude/settings.json`을 대신 배선한다.

## --help 처리

`$ARGUMENTS`가 `--help`/`-h`이면 아래를 출력하고 종료:

```
/hud:setup — hud statusline 활성화
  안정 런처를 <configDir>/hud/hud.mjs 에 설치하고,
  <configDir>/settings.json 의 statusLine 을 그 런처로 설정한다.
  기존 settings.json 은 .bak 으로 백업된다. 재실행 안전(idempotent).
```

## 실행

1. 이 스킬 디렉터리 기준 플러그인 루트의 `setup.mjs`를 실행한다:

   ```bash
   node "${CLAUDE_PLUGIN_ROOT}/setup.mjs"
   ```

   `CLAUDE_PLUGIN_ROOT`이 없으면(개발 환경 등) 이 SKILL.md 기준 상위 2단계의 `setup.mjs` 절대경로로 실행한다.

2. 출력된 결과(런처 경로, settings 백업, statusLine 설정)를 사용자에게 그대로 요약 보고한다.

3. 활성화 확인을 위해 다음을 안내한다: "새 세션을 열거나, 실행 중이면 잠시 후 statusline이 갱신됩니다."

## 주의

- settings.json 파싱 실패 시 setup은 덮어쓰지 않고 수동 설정 안내를 출력한다 — 그 경우 사용자에게 수동 추가 방법을 그대로 전달한다.
- 사용량(usage) 세그먼트는 Claude 구독(OAuth) 로그인이 전제다. API 키/미로그인 환경에서는 usage가 조용히 생략된다고 안내한다.
