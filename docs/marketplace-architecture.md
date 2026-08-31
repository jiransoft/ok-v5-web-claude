# okep-butler 마켓플레이스 구조

> 이 저장소(Claude Code 플러그인 마켓플레이스)의 전체 구조와 배포·소비 흐름.
> 기준: v3.1.0 (2026-07-28)

## 전체 구조

```mermaid
graph TB
    subgraph REPO["📦 이 저장소 (배포 원천)"]
        MP[".claude-plugin/marketplace.json<br/>플러그인 인덱스 · 버전 · 태그"]

        subgraph DEV["개발 인프라"]
            LINT["scripts/lint-skills.py<br/>SKILL.md 구조 린터"]
            BUMP[".claude/commands/bump-version.md<br/>버전 일괄 범프 + 태그 + 푸시"]
            CONTRIB["CONTRIBUTION.md<br/>저장소 컨벤션"]
        end

        subgraph PLUGINS["플러그인 (plugins/*)"]
            subgraph GW["git-workflow — 스킬 4"]
                GW1["create-pr · dev-report"]
                GW2["commit"]
            end
            RT["release-tools — 스킬 2<br/>release-note<br/>(gh CLI 사용)"]
            AT["arch-tools — 스킬 2<br/>adr · diagram<br/>(설정·외부 연동 없음)"]
            subgraph CRS["code-review-suite"]
                CRS1["code-review 스킬<br/>4인 병렬 오케스트레이션"]
                CRS2["에이전트 5<br/>design·logic·perf·test<br/>+ 단독 code-reviewer"]
            end
            JT["jira-tools — 스킬 4<br/>create·resolve·impl-issue<br/>+ scripts/jira-issue.sh"]
            FT["figma-tools — 스킬 2<br/>figma-comment"]
            PT["postman-tools — 스킬 4<br/>request·example·docs-review"]
            HUD["hud — statusline<br/>launcher.mjs + bin/lib"]
            VIS["visualize — showme"]
        end
    end

    subgraph CONSUMER["👤 소비자 프로젝트"]
        CACHE["~/.claude/plugins/cache/<br/>설치된 플러그인 사본"]
        PJ[".claude/plugins.json<br/>플러그인별 설정 섹션"]
        TOKENS["~/.jira-token · ~/.figma-token<br/>· credentials"]
        CMD["CLAUDE.md<br/>프로젝트 리뷰 규칙·컨벤션"]
    end

    subgraph EXT["🌐 외부 시스템 (MCP 불필요 — CLI/REST)"]
                GH["GitHub<br/>gh CLI"]
        JR["Jira REST API"]
        FG["Figma REST<br/>+ playwright(멘션)"]
        PM["Postman API"]
    end

    MP -->|"claude plugin install /<br/>marketplace update"| CACHE
    CACHE -->|"setup 스킬이 생성/병합"| PJ
    CACHE -.->|"발급 안내"| TOKENS
    PJ --> GW & RT & JT & FT & PT & CRS
    CMD -.->|"리뷰 규칙·커밋 규칙 훅"| CRS & GW

    GW --> GH
    RT --> GH
    JT --> JR
    FT --> FG
    PT --> PM
    HUD -->|"statusLine 배선<br/>~/.claude/settings.json"| CONSUMER

    LINT -.->|"검사"| PLUGINS
    BUMP -.->|"버전 동기화"| MP
```

## 배포 파이프라인

```mermaid
flowchart LR
    A["스킬 수정"] --> B["lint-skills.py<br/>에러 0 확인"]
    B --> C["commit 스킬<br/>컨벤션 커밋"]
    C --> D["bump-version<br/>버전 표기 일괄 치환<br/>(marketplace + plugin.json + README)"]
    D --> E["git tag vX.Y.Z<br/>+ push --tags"]
    E --> F["사용자:<br/>claude plugin<br/>marketplace update"]
```

## 구성요소 설명

| 구성요소 | 역할 | 비고 |
|----------|------|------|
| `marketplace.json` | 플러그인 인덱스 — 이름·경로·버전·태그 | 버전은 전 플러그인 단일 버전 정책 |
| `plugins/*/skills/*/SKILL.md` | 스킬 본체 (모델이 읽는 지침) | `when_to_use`로 자동 호출 조건 명시 |
| `plugins/*/skills/*/reference/` | `--help` usage 등 온디맨드 로드 문서 | 컨텍스트 절약용 점진 공개 |
| `plugins/*/agents/*.md` | 서브에이전트 시스템 프롬프트 | code-review-suite만 보유 (5개) |
| setup 스킬 (플러그인별) | `.claude/plugins.json` 섹션 생성/병합 + 토큰 안내 | visualize 제외 전 플러그인 제공 |
| `.claude/plugins.json` (소비자) | 플러그인별 설정 — ID·경로 등 비밀 아닌 값 | gitignore 대상, 토큰은 `*File` 경로로 분리 |
| `CLAUDE.md` (소비자) | 팀 공유 규칙 — 리뷰 규칙·커밋 규칙 | 스킬들이 훅으로 참조 (설정보다 우선순위 낮음) |
| `scripts/lint-skills.py` | 프론트매터·구조·MCP 표기 검사 | 에러 시 릴리즈 차단, 경고는 무방 |
| `bump-version` 커맨드 | 버전 치환 → README 동기화 → 태그 → 푸시 | 이 저장소 전용 (.claude/commands) |

## 설계 특징

- **MCP 서버 불필요** — 모든 외부 연동은 CLI(gh, playwright) 또는 REST API. 설치 장벽 최소화
- **설정의 소유 분리** — 각 플러그인이 자기 setup으로 자기 섹션만 관리. 통합 setup-all 없음
- **지식과 행동의 분리** — 스킬/에이전트는 절차·출력 계약·팀 우선순위만 담고, 도메인 지식(무엇이 문제인가)은 모델 판단에 위임. 스택별 체크리스트 하드코딩 금지 (v3.0.0-M1에서 확립)
- **없으면 기본값** — 설정 키 부재 = 기본 동작. placeholder 뼈대 생성 금지 (jq 파싱 스크립트가 가짜 값을 실제 값으로 오인하는 사고 방지)

## 파일 위치 참조

| 경로 | 내용 |
|------|------|
| `.claude-plugin/marketplace.json` | 마켓플레이스 인덱스 |
| `plugins/<name>/.claude-plugin/plugin.json` | 플러그인 메타 (버전·설명·키워드) |
| `plugins/git-workflow/skills/` | commit, create-pr, dev-report, setup |
| `plugins/release-tools/skills/` | release-note, setup (gh CLI — 태그 간 diff 분석·GitHub Release 등록) |
| `plugins/arch-tools/skills/` | adr, diagram (외부 연동 무관 — 코드 분석 → 문서 생성) |
| `plugins/code-review-suite/agents/` | design/logic/performance/test/code-reviewer |
| `plugins/jira-tools/scripts/jira-issue.sh` | Jira 이슈 생성 셸 스크립트 (jq 기반 설정 파싱) |
| `plugins/hud/launcher.mjs` | statusline 안정 런처 (`~/.claude/hud/`에 설치됨) |
| `scripts/lint-skills.py` | SKILL.md 린터 |
| `.claude/commands/bump-version.md` | 릴리즈 커맨드 |
