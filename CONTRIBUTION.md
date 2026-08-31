# Contributing to okep-butler

이 저장소는 Claude Code 플러그인 마켓플레이스다. 새 스킬·에이전트·플러그인을 추가하거나
고칠 때 아래 컨벤션을 따른다. 이 문서는 기존 25개 스킬 / 9개 에이전트에서 **이미 지켜지고 있는
암묵적 규칙을 명문화한 것**이다 — 새 코드가 기존 손맛에서 벗어나지 않게 하는 것이 목적이다.

## 저장소 구조

```
.claude-plugin/marketplace.json   # 마켓플레이스 매니페스트 (플러그인 목록 + 버전)
README.md                         # 사용자용 설치/설정 가이드
scripts/lint-skills.py            # SKILL.md 구조 린터 (아래 "테스트/검증" 참고)
plugins/<plugin>/
  .claude-plugin/plugin.json      # 플러그인 매니페스트
  reference/*.md                  # 플러그인 내 여러 스킬이 공유하는 자료
  templates/*.md                  # 플러그인 내 여러 스킬이 공유하는 출력 템플릿
  skills/<skill>/SKILL.md         # 스킬 (디렉토리명 = 스킬명)
  skills/<skill>/reference/*.md   # 그 스킬만 쓰는 상세 자료 (progressive disclosure)
  agents/<agent>.md               # 서브에이전트
```

스킬·에이전트·커맨드는 **디렉토리 구조로 자동 발견**된다. plugin.json에 따로 나열하지 않는다.

### reference 를 어디에 둘 것인가

- **한 스킬만 쓴다** → `skills/<skill>/reference/` (`../` 없이 `reference/x.md` 로 참조)
- **한 플러그인의 여러 스킬이 쓴다** → `plugins/<plugin>/reference/`
  (`../../reference/x.md` 로 참조). 예: `config-recommendation.md`, `naming-strategy.md`
- 참조는 **SKILL.md 에서 한 단계 깊이**로만 건다. reference 가 또 다른 reference 를 가리키면
  모델이 부분 읽기(`head -100`)로 끝내 정보가 잘린다.
- **100줄을 넘는 reference 는 상단에 `## 목차`** 를 둔다 (부분 읽기에서 범위가 보이도록).

### 무엇을 분리하고 무엇을 남기는가

스킬 본문은 **로드되면 세션이 끝날 때까지 컨텍스트에 남는다**. 실행마다 쓰이지 않는 텍스트는
분리 대상이다. 다만 분리에는 Read 호출 1회 비용이 붙으므로 **10줄 이상**일 때만 이득이다.

| 분리 | 유지 |
|------|------|
| `--help` 사용법 블록 (13~61줄) | setup 스킬의 8~9줄짜리 `--help` |
| `plugins.json 설정 권고` 출력 규약 (플러그인 공유) | 스킬별 "권고 대상" 키 목록 2줄 |
| 긴 질문 템플릿·출력 템플릿·예시 모음 | worktree self-heal 같은 3~4줄 스니펫 |

## 스킬 작성 규칙

### frontmatter (필수 형태)

```yaml
---
name: skill-name                  # 디렉토리명과 동일, kebab-case
description: ...                   # 무엇을 하는지 1~2문장. 끝에 트리거 키워드 예시 포함
when_to_use: 사용자가 "..." 등 ... 할 때.   # 자동 호출 판단 기준 (모델이 읽음)
allowed-tools: Bash(git *), Read, Grep, Glob, Agent, AskUserQuestion
argument-hint: "[--opt <val>]"     # 인자 힌트
---
```

- **`when_to_use`** 와 **`description`** 에만 트리거 키워드를 둔다. 본문에 `## 트리거` 섹션을
  중복으로 두지 않는다 — 모델 호출 판단은 frontmatter만 본다.
- 사용자가 명시적으로만 부르게 하려면(모델 자동 호출 금지) `when_to_use` 대신
  `disable-model-invocation: true` 를 쓴다 (예: `commit`, `showme`).
- **`allowed-tools` 는 최소 권한으로 스코핑한다.** `Bash` 전체 대신 `Bash(git *)`,
  `Bash(gh *)` 처럼 명령 단위로 제한한다. 권한이 모자라면 프롬프트가 뜰 뿐 실패하지 않으니
  좁게 잡는다. 원리적으로 스코핑이 불가능하면 `# lint-skip: BASH — 사유` 로 면제한다.

### description 과 when_to_use 의 역할

공식 규격상 `description` 은 **"무엇을 하는가"와 "언제 쓰는가"를 모두** 담아야 하고,
Claude Code 에서는 뒷부분을 `when_to_use` 로 뺄 수 있다. 이 저장소는 후자를 쓴다.

| 필드 | 담는 것 | 상한 |
|------|---------|------|
| `description` | **무엇을 하는지** — 동작·산출물·자매 스킬과의 경계 | 1,024자 |
| `when_to_use` | **언제 부르는지** — 사용자 발화 예시 | 둘의 합 1,536자 (초과분은 목록에서 잘림) |

- **3인칭 서술로 쓴다.** `"~합니다"` / `"~한다"` 는 되고, `"제가 도와드립니다"` 는 안 된다.
- **스킬 자신을 지칭하지 않는다.** `"이 skill은 사용자가 ... 할 때 사용한다"` 는 when 만 있고
  what 이 없어 `when_to_use` 와 통째로 중복된다 (`mr-comments` 가 그렇게 샜다).
- `helper`·`utils` 같은 모호한 이름과, `"문서 관련 작업을 돕습니다"` 류의 모호한 설명을 피한다.
  모델은 100개가 넘는 스킬 중에서 이 두 필드만 보고 고른다.

### 도구 이름은 실존하는 것만 쓴다

`allowed-tools` 에 없는 이름을 적으면 **그 도구는 차단된다** — 스킬이 조용히 동작하지 않는다.

- 서브에이전트 도구는 **`Agent`** 다. `Task` 는 폐기된 옛 이름이고, 본문에서도 "Task tool" 이
  아니라 "Agent 도구" 로 쓴다. (`TaskCreate`/`TaskUpdate` 는 별개의 할일 추적 도구다.)
- **MCP 도구는 `mcp__<server>__<tool>` 로 완전 정규화한다.** `browser_navigate`,
  `get_design_context` 처럼 접두사를 빼면 "tool not found" 가 난다. 본문 산문에서도 마찬가지다.
- 단, 외부 연동은 가급적 MCP 대신 CLI/REST 를 쓴다 (아래 "MCP 비의존").

### 코드블록 안에 코드블록

출력 템플릿 안에 예시 코드블록을 넣을 때는 **바깥 펜스를 백틱 4개**로 한다.

`````markdown
````
## 보고서 템플릿

```bash
실제 예시 명령
```
````
`````

(이 예시 자체도 4개짜리 블록을 보여주려고 바깥을 백틱 **5개**로 감쌌다 — 규칙은 재귀적이다.)

CommonMark 상 **info string 이 붙은 펜스(` ```bash `)는 블록을 닫지 못한다.** 바깥도 백틱
3개면 그 다음에 오는 ` ``` ` 가 바깥 블록을 조기에 닫아버리고, 이후 ` ``` ` 가 새 블록을 열어
파일 끝까지 안 닫힌다 — 뒤따르는 섹션이 통째로 코드블록에 삼켜진다. 실제로 8개 파일 17곳이
이 이유로 깨져 있었다.

### 본문 구조 (관례)

1. `# <Skill> Skill` + 한 줄 요약
2. `## --help 처리` — `$ARGUMENTS` 가 `--help`/`-h` 면 사용법 출력 후 종료
3. `## 절차` — 번호 매긴 결정적 단계. 각 단계에 실행할 bash/도구를 명시
4. `## 출력 형식` / 템플릿 (코드블록)
5. `## 주의사항`

### 필수 행동 규칙

- **출력·주석·커밋 메시지는 한글로 작성한다.**
- **설정은 3단 폴백으로 읽는다**: ① `.claude/plugins.json` 의 `<plugin>` 섹션을 **Read 도구로 직접**
  읽기 → ② 프로젝트 `CLAUDE.md` → ③ `AskUserQuestion`. "시스템 컨텍스트에 이미 로드된 값을
  쓰지 말고 반드시 Read 로 파일을 직접 읽어라"를 명시한다 (stale config 방지).
- **설정 경로는 본체 레포 루트 기준으로 해석한다.** `plugins.json` 은 gitignore 대상이라
  **worktree 에는 존재하지 않는다.** worktree 로 `cd` 하거나 worktree 경로를 대상으로 작업하는
  중에 상대경로로 읽으면 파일을 못 찾고, 인증 정보가 **조용히 빈 값**이 된다(실패가 아니라
  빈 값이라 발견이 늦다). 읽기든 쓰기든 마찬가지다 — 상대경로로 `.gitignore` 를 수정하면
  worktree 의 트래킹된 `.gitignore` 에 써서 작업 브랜치를 오염시킨다.
  - bash 에서는 본체 루트를 먼저 구한다. `--git-common-dir` 는 worktree 안에서도 본체의
    `.git` 을 준다(`--git-dir` 은 worktree 전용을 준다):
    ```bash
    gcd=$(git rev-parse --git-common-dir); case $gcd in /*) ;; *) gcd=$PWD/$gcd ;; esac
    root=$(cd "$gcd/.." && pwd -P)
    ```
    `--path-format=absolute` 는 git 2.31+ 이므로 쓰지 않는다.
  - **인라인 `jq` 로 설정을 파싱하지 않는다.** 플러그인에 스크립트가 있으면 그쪽에 경로
    해석을 맡긴다 (예: `jira-issue.sh env`). 경로 규칙이 여러 SKILL.md 에 흩어지면 한 곳만
    고쳐도 나머지가 남는다.
  - Read 도구로 읽으라고 지시할 때도 **"본체 레포 루트의"** 를 문장에 명시한다. worktree
    작업 지시가 앞에 있으면 상대 표기가 worktree 로 해석될 수 있다.
- **민감 값은 plugins.json 에 직접 넣지 않는다.** `~/.xxx-token` 파일 경로 키(`*File`)로 분리한다.
- **외부 도구 의존 시 preflight 점검**을 둔다. 시작 전에 `command -v <tool>` 로 확인하고,
  없으면 폴백 경로를 안내하거나 사용자 확인을 받는다 (예: `impl-issue` 의 pandoc 점검).
- **AskUserQuestion 으로 받은 값이 있으면** 작업 후 "plugins.json 구성 권고" 블록을 출력한다
  (CLI 인자·자동판단 값은 제외).
- **서브에이전트 결과를 맹신하지 않는다.** 핵심 주장은 직접 코드를 읽어 검증하고, 미검증분은
  "추정"으로 표기한다.

### 진행 체크리스트 (선별 적용)

단계가 많고 **건너뛰면 조용히 반쪽 상태가 남는** 스킬에만 넣는다. 짧은 스킬에 넣으면
매 실행 토큰만 먹는 순비용이다 — 전면 적용하지 않는다.

기준: **10단계 이상** + **후반 단계가 외부 상태를 정리**하는가.

```
- [ ] 6. 이슈 상태 전환 ('진행 중')
- [ ] 7. TDD 구현
- [ ] 8. 코드 리뷰
```

현재 적용: `impl-issue`(15단계 — 빠뜨리면 "구현은 됐는데 Jira 는 그대로"),
`team`(11단계 — 9단계를 빠뜨리면 팀이 남아 다음 실행이 이름 충돌로 막힘).

### 피드백 루프 (검증·생성 스킬)

무언가를 **검증하거나 생성해서 고치는** 스킬은 "고쳤다"로 끝내지 않는다. 재검증 없이 끝내면
"수정했다고 보고했지만 여전히 틀린" 상태가 남는다.

1. 수정한다
2. **원본을 다시 읽어** 같은 검사를 돌린다 (기억이나 직전 응답에 의존하지 않는다)
3. 남았고 회차 < N → 1로. **N회차(보통 3)에도 남으면 멈추고 "자동 수정 실패"로 분류**해 보고한다
4. 반복 실패는 대개 사람 판단이 필요한 신호다 — 임의로 더 고치지 않는다

현재 적용: `postman-docs-review` 5단계.

### 번들 스크립트 (`scripts/`)

셸 변수를 **다른 언어의 소스 문자열에 보간하지 않는다.** 아래는 금지 패턴이다:

```bash
python3 -c "text = '''$description'''"      # description 에 ''' · $ · \ 가 오면 깨진다
curl -d '{"summary": "'$summary'"}'          # summary 에 ' 가 하나만 있어도 깨진다
```

한 줄로 안전하게 만들 수 있으면 `jq` 에 위임한다:

```bash
payload=$(jq -n --arg s "$summary" --arg b "$body" '{fields:{summary:$s, description:$b}}')
```

페이로드 구성이 복잡해 그걸로 부족하면 **`plugins/<plugin>/scripts/` 에 스크립트를 두고
값은 인자·파일로 넘긴다.** 스크립트는 실행만 되고 내용이 컨텍스트에 올라가지 않아 토큰도 아낀다.

- 경로 변수는 **`${CLAUDE_SKILL_DIR}` 하나뿐**이고 SKILL.md 가 있는 디렉토리를 가리킨다.
  플러그인 공유 스크립트는 `${CLAUDE_SKILL_DIR}/../../scripts/x.sh` 로 참조한다.
- **본문과 `allowed-tools` 에 같은 문자열을 쓰면 권한 프롬프트가 뜨지 않는다**:
  ```yaml
  allowed-tools: Bash(${CLAUDE_SKILL_DIR}/../../scripts/jira-issue.sh *)
  ```
- 스크립트는 **에러를 스스로 처리한다.** 실패를 모델에게 떠넘기지 말고 종료 코드와
  사람이 읽을 수 있는 메시지를 낸다.
- 상수에 근거를 남긴다. `TIMEOUT=47` 처럼 이유 없는 숫자를 두지 않는다.

### worktree 격리 (브랜치 대상 작업)

다른 브랜치를 대상으로 하는 스킬(`--source`)은 임시 worktree 에서 작업한다.

- **`git worktree add` 직전에 self-heal 가드를 둔다.** 고정 경로는 이전 실행이 중간에
  중단되면 stale worktree 로 남아 다음 실행을 막는다 — add 전에 항상 정리하면 자가 복구된다:
  ```bash
  # 스테일 worktree 자기 치유 (이전 실행이 중단돼 남아 있으면 제거)
  git worktree remove --force <PATH> 2>/dev/null; git worktree prune; rm -rf <PATH>
  git worktree add --detach <PATH> <source>
  ```
  `<PATH>` 는 `/tmp/wt-<skill>` 처럼 스킬별 고정 경로를 쓴다 (가드가 있으므로 누수돼도 안전).
- 작업 종료 시 `git worktree remove` 로 정리하되, 정리가 누락돼도 위 가드가 다음 실행에서
  복구하므로 안전망이 이중으로 걸린다.
- git 명령(`log`/`diff`/`push`)은 원래 repo 에서 ref 를 직접 지정해 실행하고, 코드 읽기
  (Read/Grep/Glob)만 worktree 경로에서 한다.

### base 브랜치 폴백

자동 감지가 실패했을 때 `develop` 같은 브랜치명을 하드코딩하지 않는다. 저장소의 실제 기본
브랜치를 감지한다: `git symbolic-ref --short refs/remotes/origin/HEAD`(예: `origin/main`)에서
`origin/` 을 떼어 쓰고, 이마저 없을 때만 `develop` 을 최종 폴백으로 한다.

## 에이전트 작성 규칙

```yaml
---
name: agent-name
description: 한 줄 역할 설명
tools: Read, Grep, Glob, Bash      # 리뷰어/분석가는 Edit·Write 제외
model: opus | sonnet | haiku       # 깊은 분석 opus, 표준 sonnet, 단순 조회 haiku
---
```

- **리뷰·검증 에이전트는 코드를 수정하지 않는다.** `tools` 에서 Edit/Write 를 빼서
  저자/검토자 패스를 물리적으로 분리한다.
- 단일 책임을 명시하고 다른 관점은 명시적으로 배제한다 (예: logic-reviewer 는 "성능·설계·
  가독성은 내 범위가 아니다"라고 선언).
- 결과는 한글, 심각도 이모지 스킴을 따른다.

## 공용 규약

### 심각도 표기 (코드 리뷰 계열)

```
🔴 Critical (즉시 수정) | 🟠 Major (수정 권장) | 🟡 Minor (개선 가능) | 💡 Suggestion (제안)
```
이슈 없는 레벨의 섹션은 생략한다.

### 모델 문자열을 스킬 본문에 하드코딩하지 않는다

스킬·에이전트 **본문**에 `Claude Opus 4.x` 같은 모델명을 박지 않는다 — 환경 모델이 바뀌면
부패한다. 런타임에서 받은 모델명을 쓰거나 버전 무관 문구를 사용한다.
에이전트 frontmatter 의 `model:` 은 `opus`/`sonnet`/`haiku` 같은 **별칭**만 쓴다.

**커밋 trailer 는 예외다.** `Co-Authored-By: Claude Opus N ...` 처럼 그 시점 모델을 남긴다 —
이력상 어느 모델이 작업했는지가 유용하고, 과거 커밋은 어차피 그 시점의 사실이라 부패하지 않는다.
(이 저장소의 기존 커밋도 전부 이 형태다.)

### MCP 비의존

모든 외부 연동(Jira/GitHub/Slack/Figma/Postman)은 CLI 또는 REST(curl)로 한다. MCP 서버를
전제하지 않는다. 신규 연동도 이 원칙을 따른다.

## 새 스킬/플러그인 추가 체크리스트

스킬 추가 시 **세 곳을 동시에 갱신**한다 (드리프트 방지):

- [ ] `plugins/<plugin>/skills/<skill>/SKILL.md` 작성 (위 frontmatter 규칙)
- [ ] `README.md` 의 플러그인 표 Skills 컬럼에 추가
- [ ] `.claude-plugin/marketplace.json` 의 해당 플러그인 description/tags 갱신
- [ ] 새 설정 키가 생기면 README 의 "플러그인별 필요 설정" 표 + 설정 예시 갱신
- [ ] 새 외부 도구 의존이 생기면 README 의 Requirements 표 갱신

신규 **플러그인** 추가 시:

- [ ] `plugins/<plugin>/.claude-plugin/plugin.json` 생성 (name/version/description/author/keywords)
- [ ] `marketplace.json` 의 `plugins[]` 에 항목 추가 (source/version/category/tags)
- [ ] README 표 + Install 섹션에 추가

## 버전 관리

- 버전은 **`marketplace.json`(상단 metadata + 각 plugin 항목)과 각 `plugin.json` 에 이중 기재**된다.
  손으로 고치지 말고 `/bump-version` 커맨드로 일괄 변경·커밋한다 (둘을 동기화함).
- 현재 정책은 **전 플러그인 동반 버전 상승**(lockstep)이다. 개별 플러그인만 올리고 싶다면
  bump-version 정책부터 바꿔야 한다.
- 커밋 메시지는 한글, Conventional Commits prefix(`feat`/`fix`/`refactor`/`chore`/`test`)를 쓴다.

## 테스트/검증

- **구조는 린터로 검증한다**: `python3 scripts/lint-skills.py` (에러가 있으면 exit 1).
  펜스 균형·실존 도구명·MCP 접두사·프론트매터 필수/금지 필드·`worktree --detach`·무제한 Bash·
  단계 번호 중복·reference 목차·본문 500줄·name/description 규격·**셸 변수 문자열 보간**
  11종을 본다. 특정 파일만 보려면 경로를 인자로 준다.
  스코핑이 원리적으로 불가능한 경우에만 프론트매터에 `# lint-skip: CODE — 사유` 로 면제한다
  (사유가 없으면 면제되지 않는다).
- 린터가 못 잡는 것(설명 품질, 절차의 타당성)은 여전히 **실제 실행으로 검증**한다. 새 스킬은
  `--help` 출력과 정상 경로를 한 번 이상 돌려본다.
- hud 같은 코드 플러그인(`*.mjs`)은 의존성 0·Node 빌트인만 사용 원칙을 유지하고, 어떤 입력에도
  statusline 이 크래시하지 않도록 최상위 `catch` 로 빈 줄을 보장한다.
