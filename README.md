# okep-butler

Claude Code 플러그인 마켓플레이스 — GitHub·Jira·Figma·Postman 연동, 코드 리뷰 워크플로우, 상태줄 등.

> **대부분 MCP 서버 없이 동작합니다.** 외부 연동은 기본적으로 CLI·REST API를 씁니다. 예외는 한 곳입니다 — `runtime-verify` 의 `verify-stack`(playwright MCP). 설치 상태는 `/doctor:check` 로 확인할 수 있습니다.

## Plugins

### 팀 필수 5종

팀원 모두 설치합니다 — [Install §4](#4-플러그인-설치) 참고.

| Plugin | 설명 | 주요 스킬 | Version |
|--------|------|-----------|---------|
| **git-workflow** | GitHub PR 생성·커밋·개발 리포트 등 워크플로우 자동화 | `create-pr`, `dev-report`, `commit` | 0.2.0 |
| **jira-tools** | Jira 이슈 자동 생성·분석·구현 | `create-jira-issue`, `resolve-issue`, `impl-issue` | 0.2.0 |
| **code-review-suite** | 4인 병렬 코드 리뷰 (Design/Logic/Performance/Test) 에이전트 + 통합 리뷰 스킬 | `code-review` | 0.2.0 |
| **runtime-verify** | Jira 이슈·브랜치별 포트 블록으로 애플리케이션 모듈을 병렬 기동하고 브라우저로 검증 시나리오를 확인 (detached worktree, context 격리) | `verify-stack` | 0.2.0 |
| **doctor** | 설치된 플러그인의 설정·토큰·CLI·MCP·훅 배선을 진단하고 조치를 안내 (플러그인별 `doctor.json` 기반) | `check` | 0.2.0 |

### 개인 선택 6종

필요한 사람만 골라 설치합니다.

| Plugin | 설명 | 주요 스킬 | Version |
|--------|------|-----------|---------|
| **hud** | Claude 구독 사용량(rate limit) + 컨텍스트/모델/비용 + 네이티브 Task 진행률 상태줄 (clean-room, 의존성 0) | `setup` | 0.2.0 |
| **release-tools** | git 태그 간 변경 분석으로 FE팀 공유용 릴리즈 노트를 작성하고 GitHub Release에 등록 (릴리즈 담당자용) | `release-note` | 0.2.0 |
| **visualize** | 기술 개념을 공식 문서 근거 + 레포 실측으로 설명하고 인터랙티브 HTML로 시연 (`--text` 시 텍스트만) | `showme` | 0.2.0 |
| **arch-tools** | 코드 분석 기반 아키텍처 문서화 (ADR·Mermaid 다이어그램/PDF) | `adr`, `diagram` | 0.2.0 |
| **postman-tools** | Postman 컬렉션 request 생성/수정, example 자동 생성, docs/request 검증 | `postman-request`, `postman-example`, `postman-docs-review` | 0.2.0 |
| **figma-tools** | Figma 코멘트 조회·작성·삭제 | `figma-comment` | 0.2.0 |

> 위 표의 "주요 스킬"은 핵심 스킬만 표기했습니다. `visualize`·`arch-tools`를 제외한 모든 플러그인은 설정/활성화용 `setup` 스킬도 함께 제공합니다 — [Setup](#setup) 참고.

---

## Install

신규 팀원 온보딩 순서 그대로입니다 — 위에서 아래로 따라가면 끝납니다. 1~4는 터미널에서, 5~6은 Claude Code 안에서 실행합니다.

### 1. CLI 준비

macOS 기본 도구(git·curl·python3) 외에, 팀 필수 5종 기준으로 새로 설치할 것은 둘뿐입니다:

```bash
brew install gh jq
```

나머지 도구는 설치한 플러그인에 따라 다릅니다 — 6단계의 `/doctor:check` 가 부족한 것만 짚어주니 미리 외울 필요 없습니다. 전체 목록은 [Requirements](#requirements) 참고.

### 2. GitHub 인증 (private repo)

이미 이 레포를 `git clone` 할 수 있는 상태라면 건너뜁니다. 아래 둘 중 하나만 되어 있으면 됩니다.

**SSH (권장)** — GitHub 계정에 SSH 키가 등록되어 있으면 끝입니다.

```bash
ssh -T git@github.com    # "Hi <username>!" 이 나오면 성공
```

키가 없으면 [github.com/settings/keys](https://github.com/settings/keys) 에서 등록합니다.

**HTTPS (gh CLI)**

```bash
gh auth login        # 브라우저 로그인
gh auth setup-git    # git credential 연동
```

확인 — ref 목록이 나오면 성공입니다.

```bash
git ls-remote git@github.com:jiransoft/ok-v5-web-claude.git | head -3
```

### 3. 마켓플레이스 등록

```bash
claude plugin marketplace add git@github.com:jiransoft/ok-v5-web-claude.git
```

HTTPS 사용자는 `https://github.com/jiransoft/ok-v5-web-claude.git` 을 대신 씁니다. 2단계의 인증이 자동 적용됩니다.

### 4. 플러그인 설치

**팀 필수 5종** — 팀원 모두 설치합니다. 제품 레포 디렉터리에서 실행하세요.

```bash
claude plugin install git-workflow@okep-butler -s local
claude plugin install jira-tools@okep-butler -s local
claude plugin install code-review-suite@okep-butler -s local
claude plugin install runtime-verify@okep-butler -s local
claude plugin install doctor@okep-butler -s local
```

**개인 선택 6종** — 필요한 것만 골라 설치합니다.

```bash
claude plugin install hud@okep-butler -s user            # 상태줄 — 레포 무관, 전역 추천
claude plugin install release-tools@okep-butler -s local # 릴리즈 담당자만 — 레포별 개인 설치(local) 추천
claude plugin install visualize@okep-butler -s local
claude plugin install arch-tools@okep-butler -s local
claude plugin install postman-tools@okep-butler -s local
claude plugin install figma-tools@okep-butler -s local
```

스코프 정리 — `-s local` 은 **현재 레포에서만 + 개인 설정**(`.claude/settings.local.json`, git 미공유), `-s user` 는 개인 전역,
`-s project` 는 `.claude/settings.json` 에 기록되어 **커밋하면 팀 전체 공유**됩니다. 팀 차원 강제가 필요해지면
필수 5종을 `-s project` 로 설치해 커밋하는 방식으로 전환하면 됩니다.

### 5. 셋업 — 설치한 플러그인마다 1회

Claude Code를 열고, 설치한 플러그인마다 셋업을 한 번씩 실행합니다. 필수 5종 기준:

```
/git-workflow:setup
/jira-tools:setup
/code-review-suite:setup
/runtime-verify:setup
```

`doctor` 는 설정이 없어 셋업이 필요 없고, 개인 선택 플러그인은 [Setup](#setup) 표에서 자기 것만 찾아 돌리면 됩니다.

> 셋업 없이도 동작은 합니다 — 대신 스킬이 실행 중에 필요한 값을 매번 물어봅니다. 셋업은 그 질문을
> 미리 한 번에 끝내두고, Jira Cloud ID처럼 사람이 모르는 값을 API에서 자동 조회해주는 편의 기능입니다.

### 6. 설치 확인

```
/doctor:check
```

설정·토큰·CLI·MCP·훅 배선을 전부 점검하고, 문제가 있으면 조치(어느 setup을 돌릴지, 뭘 설치할지)까지 알려줍니다. **전부 ✅ 면 온보딩 끝.**

---

## 업데이트

이후 플러그인이 갱신되면 (README 공지 또는 팀 공지 시):

```bash
claude plugin marketplace update
```

---

## Setup

[Install §5](#5-셋업--설치한-플러그인마다-1회)에서 실행하는 셋업의 상세 레퍼런스입니다. 셋업은 서로 독립적이라 순서는 상관없고, **설치한 것만** 돌리면 됩니다(통합 setup-all은 없음 — 각 플러그인이 자기 설정을 소유하는 구조).

셋업은 손으로 쓰는 [Configuration](#configuration)을 대신해, `.claude/plugins.json` 섹션 생성/병합·토큰 파일 안내·`.gitignore` 등록까지 처리하고, **사람이 모르는 ID성 값은 API·git에서 자동 조회**합니다.

| 플러그인 | 셋업 명령 | 셋업이 해주는 일 (자동 조회 포함) |
|----------|-----------|-----------------------------------|
| **hud** | `/hud:setup` | statusLine 배선 — [아래 참고](#hud-statusline-활성화) |
| **jira-tools** | `/jira-tools:setup` | baseUrl·토큰으로 **issueType/component/customField ID·Cloud ID 자동 조회** |
| **postman-tools** | `/postman-tools:setup` | apiKey로 **워크스페이스·컬렉션 목록 조회 → 선택**해 ID 채움 |
| **git-workflow** | `/git-workflow:setup` | `git remote`→`project`, 레포 구조→`moduleRoot` 유추 |
| **release-tools** | `/release-tools:setup` | `git remote`→`project`, 레포 구조→`modules` 유추, 기존 `git-workflow` 섹션 값 이전 |
| **figma-tools** | `/figma-tools:setup` | `~/.figma-token` 안내 + `GET /v1/me` 유효성 검증 |
| **code-review-suite** | `/code-review-suite:setup` | 레포 매니페스트 스캔으로 **techStack 자동 감지** |
| **runtime-verify** | `/runtime-verify:setup` | 레포 스캔으로 **모듈 후보 제안** + 포트 슬롯 설계·`prepare` 구성 |
| **visualize** | — | 설정 불필요 |
| **arch-tools** | — | 설정 불필요 |
| **doctor** | — | 설정 불필요 (`/doctor:check` 로 나머지 플러그인을 진단) |

### hud statusline 활성화

Claude Code는 플러그인이 메인 `statusLine`을 자동으로 켜지 못합니다(플러그인 설정은 `agent`·`subagentStatusLine`만 인정). 따라서 설치 후 셋업 한 번이 필요합니다:

```
/hud:setup
```

버전에 안 묶이는 안정 런처를 `~/.claude/hud/hud.mjs`에 설치하고 `~/.claude/settings.json`의 `statusLine`을 그 런처로 배선합니다(기존 설정은 `.bak` 백업). 마켓플레이스를 업데이트해도 다시 셋업할 필요가 없습니다.

수동 설정을 원하면 `~/.claude/settings.json`에 직접 추가:

```json
{ "statusLine": { "type": "command", "command": "node ~/.claude/hud/hud.mjs" } }
```

표시 예시:

```
5h:22%(3h3m) wk:19%(1h43m) sn:0% │ ctx:34% │ Opus 4.8 │ git:(main) │ $0.12 │ 📋 ▓▓▓░░░░░░░ 1/3 33% · 대기 1 · 테스트 실행 중
```

| 세그먼트 | 의미 |
|---------|------|
| `5h:22%(3h3m)` | 5시간 사용량 윈도우 (리셋까지 남은 시간) |
| `wk:19% sn:0% op:..` | 주간 / 모델별(Sonnet·Opus) 사용량 |
| `ctx:34%` | 컨텍스트 윈도우 사용률 |
| `Opus 4.8` | 활성 모델 |
| `git:(main)` | Git 브랜치 |
| `$0.12` | 세션 비용 |
| `📋 1/3 33% · …` | 네이티브 Task 진행률 (완료/전체, 대기 수, 진행 중 작업) |

> 사용량(5h/wk/sn) 세그먼트는 **Claude 구독(OAuth) 로그인**이 전제입니다. API 키/미로그인 환경에서는 조용히 생략됩니다. 요구사항: Node ≥ 20.

---

## Configuration

> 대부분의 경우 [Setup](#setup)의 셋업 마법사를 쓰면 이 섹션을 손댈 필요가 없습니다. 아래는 **수동 구성·키 레퍼런스**입니다.

각 플러그인(`hud`·`visualize`·`arch-tools` 제외)은 프로젝트의 `.claude/plugins.json`에서 설정을 읽습니다. 파일이 없거나 값이 누락되면 사용자에게 질문합니다.

> ⚠️ `.claude/plugins.json`에는 Cloud ID·URL 등 민감 정보가 포함될 수 있으니 `.gitignore`에 추가하세요(셋업이 자동 처리). 토큰·비밀번호 같은 민감 값은 파일에 **직접 넣지 말고** `*File`/`credentialsFile` 경로로 분리하세요.

```bash
echo '.claude/plugins.json' >> .gitignore
```

### 플러그인별 필요 설정

| 플러그인 | 필수 키 | 선택 키 |
|----------|---------|---------|
| **jira-tools** | `baseUrl`, `email`, `apiTokenFile`, `projects` | `cloudId` — 프로젝트별 값(assignee·issueTypes·components·customFields)은 `projects.<키>` 안에 |
| **git-workflow** | — | `defaultAssignee`, `defaultReviewer`, `defaultLabels`, `moduleRoot`, `project`, `commit` |
| **release-tools** | — | `project`, `swaggerBaseUrl`, `modules` |
| **postman-tools** | `workspaceId`, `workspaceName`, `apiKey` | `backendStack`, `services`, `collectionUid` |
| **figma-tools** | — | `tokenFile` |
| **code-review-suite** | — | `techStack` |
| **runtime-verify** | `modules` | `projectKey`, `credentialsFile`, `portBase`, `worktreeBase`, `ui`, `prepare` |

### 설정 파일 예시

```jsonc
// .claude/plugins.json
{
  "jira-tools": {
    "baseUrl": "https://your-domain.atlassian.net",
    "email": "you@example.com",
    "apiTokenFile": "~/.jira-token",
    "cloudId": "xxxxxxxx-xxxx-...",              // setup이 자동 조회 (선택)
    "projects": {                                // 프로젝트별 설정 — 쓰는 프로젝트마다 한 항목
      "PROJ": {
        "assignee": "username",
        "issueTypes": { "결함": "10004", "작업": "10002" },
        "components": { "Backend": "10001", "Frontend": "10002" },
        "customFields": {
          "issueCategory": { "fieldId": "customfield_10038", "value": { "id": "10022" } }
        }
      }
    }
  },
  "git-workflow": {
    "defaultAssignee": "username",
    "defaultReviewer": "username",
    "defaultLabels": ["D-5"],
    "moduleRoot": "apps",
    "project": "owner/repo",                       // GitHub 저장소 경로
    "commit": {                                    // 커밋 컨벤션 오버라이드 — 기본값과 다른 것만
      "subjectLanguage": "en",                     // ko(기본) | en
      "issueKeyPosition": "suffix"                 // prefix(기본) | suffix | none
    }
  },
  "release-tools": {
    "project": "owner/repo",                       // GitHub 레포 경로 (없으면 gh가 git remote에서 유추)
    "swaggerBaseUrl": "https://api.example.com/swagger-ui/index.html",
    "modules": {                                   // release-note 모듈 그루핑 (경로 prefix → 모듈명)
      "apps/api/": "API",
      "apps/admin/": "Admin"
    }
  },
  "postman-tools": {
    "workspaceId": "your-workspace-id",
    "workspaceName": "your-workspace-name",
    "apiKey": "PMAK-...",                          // Postman API Key
    "backendStack": "Kotlin Spring Boot",
    "services": { "api": "{{API-HOST}}", "checkout": "{{CHECKOUT-HOST}}" },
    "collectionUid": "owner-uuid"
  },
  "figma-tools": {
    "tokenFile": "~/.figma-token"
  },
  "code-review-suite": {
    "techStack": ["Java", "Spring Boot", "Kotlin"]
  },
  "runtime-verify": {
    "projectKey": "PROJ",                            // 생략 시 jira-tools.projects 의 유일한 키 폴백
    "credentialsFile": "~/.admin-credentials",       // "id:pw" 한 줄
    "portBase": 10000,
    "worktreeBase": "/tmp",
    "modules": [                                     // {sN} = portBase + N×1000 + 이슈번호%1000
      {
        "name": "api",
        "dir": "apps/api",
        "start": "./gradlew bootRun --args=\"--server.port={s0} --management.server.port={s1} --spring.profiles.active=local\"",
        "health": { "url": "http://localhost:{s1}/actuator/health", "expect": "200" }
      },
      {
        "name": "site",
        "dir": "apps/site",
        "start": "API_HOST=http://localhost:{s0} npm run dev -- -p {s2}",
        "health": { "url": "http://localhost:{s2}", "expect": "200|307" }
      }
    ],
    "ui": { "module": "site", "slot": 2, "signinPath": "/signin" },
    "prepare": [                                     // fresh worktree 준비 ($MAIN = 본체 루트)
      "npm --prefix apps/site install",
      "cp $MAIN/apps/site/.env apps/site/.env"
    ]
  }
}
```

### 토큰/크리덴셜 파일

민감한 값은 `plugins.json`에 직접 넣지 말고 로컬 파일로 분리하세요(셋업이 생성 명령을 안내).

| 파일 | 발급처 / 형식 | 용도 |
|------|---------------|------|
| `~/.jira-token` | https://id.atlassian.com/manage-profile/security/api-tokens | Jira REST API Basic Auth |
| `~/.figma-token` | https://www.figma.com/settings (Personal access token) | Figma REST API |

```bash
# 예시 (생성 후 항상 chmod 600)
echo "ATATT3xF..." > ~/.jira-token && chmod 600 ~/.jira-token
```

---

## Requirements

아래는 **11개 플러그인 전체의 합집합** 레퍼런스입니다. 각자 설치할 것은 자기 플러그인 몫뿐이고
(팀 필수 5종 기준 `brew install gh jq` — [Install §1](#1-cli-준비)), 실제 필요 여부는 `/doctor:check` 가 판정합니다.

| 도구 | 용도 | 설치 |
|------|------|------|
| `git` | git-workflow, commit, worktree | 기본 |
| `curl` | REST API 호출 (Jira·Slack·Postman·Figma) | 기본 |
| `jq` | JSON 파싱 | `brew install jq` |
| `gh` | GitHub CLI — git-workflow 의 PR 생성, release-tools 의 릴리즈 등록 | `brew install gh` |
| `playwright-cli` | figma-comment(멘션) | `npm install -g @playwright/cli` |
| `python3` | Postman 컬렉션 JSON 편집, SKILL.md 린터 | 기본 |
| `pandoc` | jira-tools 댓글 마크다운 → wiki markup (미설치 시 `{code}` 폴백) | `brew install pandoc` |
| `node` | hud statusline (≥ 20) | 기본 |

### MCP 서버

| 서버 | 필요한 곳 | 없으면 |
|------|-----------|--------|
| `playwright` | `runtime-verify` 의 `verify-stack` (브라우저 검증) | `verify-stack` 사용 불가 — 다른 스킬은 무관 |

`figma-tools` 의 @멘션 자동화는 MCP 가 아니라 `playwright-cli` 를 쓴다. 선언 상태는 `/doctor:check` 가 점검한다.
