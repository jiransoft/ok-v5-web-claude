# hud

Claude Code statusline. 구독 사용량(rate limit) 윈도우 + 컨텍스트/모델/비용 + 네이티브 Task 진행률을 한 줄로 보여준다. 전부 Node 내장 모듈만 쓰는 clean-room 구현 — 외부 코드/패키지 의존성 없음.

```
5h:22%(3h3m) wk:19%(1h43m) sn:0% │ ctx:34% │ Opus 4.8 │ git:(main) │ $0.12 │ 📋 ▓▓▓░░░░░░░ 1/3 33% · 대기 1 · 테스트 실행 중
```

## 구성

- `bin/statusline.mjs` — 엔트리. stdin의 statusline JSON을 읽어 각 세그먼트를 조립해 출력.
- `lib/usage.mjs` — 로컬 Claude OAuth 자격증명(키체인/`.credentials.json`)을 읽어 Anthropic usage API(`api.anthropic.com/api/oauth/usage`)로 5h/주간/모델별 윈도우를 조회. 만료 시 `platform.claude.com/v1/oauth/token`으로 리프레시. 90초 캐시(`<configDir>/plugins/hud/.usage-cache.json`)로 렌더 비용 최소화.
- `lib/render.mjs` — ANSI 색상 + 세그먼트 포매터.
- `lib/progress.mjs` — `<configDir>/tasks/session-<short>/N.json` (CC 네이티브 Task 상태)을 읽어 진행률 바 렌더.

## 요구사항

- Node >= 20
- 사용량 표시는 Claude 구독(OAuth) 로그인이 전제. API 키 사용자/미로그인 환경에서는 usage 세그먼트가 조용히 생략된다.

## statusLine 배선

`settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "node ${CLAUDE_PLUGIN_ROOT}/plugins/hud/bin/statusline.mjs"
  }
}
```

## 동작 원칙

- 모든 I/O는 실패 시 조용히 degrade — statusline 자체는 절대 죽지 않는다.
- 색상: 사용량/컨텍스트는 높을수록 경고(≥90 빨강·≥70 노랑·else 초록), 진행률은 높을수록 양호(<20 빨강·~70 노랑·~100 시안·100 초록).
- 진행률은 task가 없으면 표시되지 않으며, `Math.floor`로 전부 끝나기 전엔 100%가 뜨지 않는다.

## 동작 사양 출처

사용량 API의 엔드포인트·인증 흐름·응답 형태는 [oh-my-claudecode](https://github.com/) HUD를 **동작 레퍼런스**로 참고해 독자 재구현했다(코드 복제 없음). API 자체는 Claude Code가 쓰는 공개 OAuth usage 엔드포인트다.
