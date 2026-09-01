# runtime-verify 설정 스키마와 예시

`.claude/plugins.json` 의 `runtime-verify` 섹션 상세. SKILL.md 0단계에서 참조한다.

## 목차

- [modules 스키마](#modules-스키마)
- [포트 치환 규칙](#포트-치환-규칙)
- [전체 예시 — Spring 멀티모듈 + Next.js](#전체-예시--spring-멀티모듈--nextjs)
- [슬롯 설계 가이드](#슬롯-설계-가이드)

## modules 스키마

| 필드 | 필수 | 설명 |
|------|:--:|------|
| `name` | ✅ | 모듈 표시명 (보고·로그 라벨) |
| `dir` | ✅ | worktree 루트 기준 상대 경로. 이 디렉터리에서 `start` 를 실행한다 |
| `start` | ✅ | 기동 명령. `{sN}` 자리에 슬롯 N 포트가 치환된다. 환경변수 주입도 이 문자열 안에서 한다 |
| `health` | ✅ | `{url, expect}` — 준비 완료 판정. `url` 에도 `{sN}` 치환이 적용되고, `expect` 는 기대 HTTP 코드 |

## 포트 치환 규칙

```
{sN} = portBase + N × 1000 + (이슈번호 % 1000)
```

- 모든 `start`·`health.url`·`ui` 문자열에서 치환된다
- 슬롯 번호는 0부터 연속으로 쓴다. **슬롯 0은 다른 모듈이 참조할 대표 포트**(예: 프론트가 연결할 API web)로 두면, 참조하는 쪽이 `{s0}` 으로 확정 계산할 수 있다
- 결과 포트 범위: portBase 10000, 슬롯 0~7 기준 `10000~17999` (유효 포트, 보정 불필요)

## 전체 예시 — Spring 멀티모듈 + Next.js

```jsonc
{
  "runtime-verify": {
    "projectKey": "PROJ",                        // 생략 시 jira-tools.projects 의 유일한 키 폴백
    "credentialsFile": "~/.admin-credentials",   // "id:pw" 한 줄
    "portBase": 10000,
    "worktreeBase": "/tmp",
    "modules": [
      {
        "name": "api",
        "dir": "apps/api",
        "start": "./gradlew :dev-tools:bootRun --args=\"--server.port={s0} --management.server.port={s1} --spring.grpc.server.port={s2} --spring.profiles.active=local\"",
        "health": { "url": "http://localhost:{s1}/actuator/health", "expect": "200" }
      },
      {
        "name": "worker",
        "dir": "apps/api",
        "start": "./gradlew :worker:bootRun --args=\"--management.server.port={s6} --spring.profiles.active=local\"",
        "health": { "url": "http://localhost:{s6}/actuator/health", "expect": "200" }
      },
      {
        "name": "checkout",
        "dir": "apps/checkout",
        // ⚠ 프레임워크·버전에 따라 gRPC 인자명이 다를 수 있다 (--grpc.server.port vs --spring.grpc.server.port)
        "start": "./gradlew bootRun --args=\"--server.port={s3} --management.server.port={s4} --grpc.server.port={s5} --spring.profiles.active=local\"",
        "health": { "url": "http://localhost:{s4}/actuator/health", "expect": "200" }
      },
      {
        "name": "site",
        "dir": "apps/site",
        "start": "API_HOST=http://localhost:{s0} NEXTAUTH_URL=http://localhost:{s7} npm run dev -- -p {s7}",
        "health": { "url": "http://localhost:{s7}", "expect": "200|307" }
      }
    ],
    "ui": { "module": "site", "slot": 7, "signinPath": "/signin" },
    "prepare": [
      "npm --prefix apps/site install",
      "cp $MAIN/apps/site/.env apps/site/.env"
    ]
  }
}
```

- 인증이 걸리지 않은 web 엔드포인트가 없으면 `expect` 에 `401` 을 쓰는 것도 유효한 준비 완료 신호다 (연결 자체는 됐다는 뜻)
- `expect` 에 `|` 로 복수 코드를 허용한다 (예: `200|307`)

## 슬롯 설계 가이드

- **모듈 수 × 포트 종류만큼 슬롯을 잡는다.** 위 예시는 8슬롯 (api web/mgmt/grpc, checkout web/mgmt/grpc, worker mgmt, site web)
- management 포트를 web 포트에 합치면 슬롯을 줄일 수 있으나, web 에 인증이 걸린 모듈은 actuator 접근 설정을 먼저 확인한다. 기본은 분리 권장
- 같은 프로젝트를 검증하는 이슈들끼리는 **이슈번호 마지막 3자리가 같을 때만** 포트가 충돌한다 — 그 경우 한쪽 검증 시점을 미루거나 사용자와 조정한다
