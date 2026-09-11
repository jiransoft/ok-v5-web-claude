---
name: complete-issue
description: 구현이 끝난 Jira 이슈를 실제로 기동해 동작을 검증하고, 원인·수정·결과 세 항목으로 압축한 보고용 댓글에 스크린샷 증거를 첨부해 등록한 뒤 검증 결과에 따라 이슈 상태를 전환합니다
when_to_use: 사용자가 이슈 키와 함께 "구현한 거 검증하고 마무리해줘", "동작 확인하고 이슈 완료 처리", "검증 결과 보고용으로 댓글 달아줘", "complete issue" 등 구현 이후의 실동작 확인과 이슈 정리를 요청할 때. 코드 변경은 하지 않는다 — 구현은 impl-issue, 분석만은 resolve-issue 가 맡는다.
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/../../scripts/jira-issue.sh *), Bash(git *), Bash(curl *), Bash(jq *), Bash(pandoc *), Bash(command *), Bash(lsof *), Bash, Read, Grep, Glob, Agent, AskUserQuestion, TaskStop
# lint-skip: BASH — verify-stack 절차를 그대로 끌고 오므로 모듈 기동 명령이 plugins.json 사용자 설정에서 온다. 전체 스코핑 불가
argument-hint: "<이슈키> [--source <branch>]"
---

# Complete Issue Skill

구현이 끝난 이슈를 실제로 기동해 동작을 확인하고, **[원인] · [수정] · [결과]** 세 항목으로 압축한 보고용 댓글을 등록한 뒤 검증 결과에 따라 상태를 전환한다.

**역할 경계** — 이 스킬은 코드를 고치지 않는다. 검증에서 실패가 나오면 보고하고 멈춘다. 수정은 `impl-issue` 로 다시 돈다.

| 스킬 | 하는 일 | 댓글 독자 |
|------|--------|----------|
| `resolve-issue` | 분석만 (코드 변경 없음) | 엔지니어 |
| `impl-issue` | TDD 구현 + 커밋 | 엔지니어 |
| `complete-issue` | 실동작 검증 + 보고 + 상태 전환 | 보고 라인 |

## --help 처리

`$ARGUMENTS` 가 `--help` 또는 `-h` 면 [reference/usage.md](reference/usage.md) 의 사용법 블록을 그대로 출력하고 즉시 종료한다.

## 진행 체크리스트

**아래 체크리스트를 응답에 복사해두고 단계마다 갱신한다.**

```
- [ ] 0. 사전 점검 (pandoc · runtime-verify 설정)
- [ ] 1. 인자 파싱
- [ ] 2. 검증 대상 브랜치 결정 (자동 추론 → 승인)
- [ ] 3. 이슈·댓글 조회 (원인·수정 원본 수집)
- [ ] 4. 커밋 diff 교차 검증
- [ ] 5. 런타임 기동 (verify-stack 절차)
- [ ] 6. 브라우저 검증 + 증거 수집
- [ ] 7. 댓글 초안 작성
- [ ] 8. 초안 사용자 확인
- [ ] 9. 증거 첨부 업로드
- [ ] 10. 댓글 등록
- [ ] 11. 상태 전환 (검증 결과로 분기)
- [ ] 12. AI 라벨 추가
- [ ] 13. 정리 및 결과 출력
```

## Jira 설정

⚠️ **이 스킬의 모든 작업을 시작하기 전에 반드시 `.claude/plugins.json` 을 Read 도구로 읽어야 한다.**

> 📍 경로는 **본체 레포 루트의 `.claude/plugins.json`** 이다. worktree 를 대상으로 작업 중이어도
> 설정은 본체에서 읽는다 — gitignore 대상이라 worktree 에 체크아웃되지 않는다.

이 스킬은 두 섹션을 모두 읽는다:

- **`jira-tools`** — `baseUrl`, `email`, `apiTokenFile` (이슈 조회·댓글·첨부). 선택 키 `transitions` 는 상태 전환 이름을 고정한다 (11단계)
- **`runtime-verify`** — `modules`, `ui`, `credentialsFile`, `portBase`, `worktreeBase`, `prepare` (런타임 기동)

설정 우선순위는 plugins.json → 프로젝트 `CLAUDE.md` → AskUserQuestion 순이다. 시스템 컨텍스트에 이미 로드된 값을 쓰지 말고 Read 도구로 파일을 직접 읽는다.

### 인증 헬퍼

```bash
eval "$("${CLAUDE_SKILL_DIR}/../../scripts/jira-issue.sh" env)"
token=$(tr -d '\n\r' < "$tokenFile")
```

`env` 는 `baseUrl`·`email`·`tokenFile`·`projects`·`pluginsJson` 을 셸 대입문으로 낸다 (토큰 값은 내지 않는다 — stdout 은 트랜스크립트에 남는다). 이 스크립트가 `git rev-parse --git-common-dir` 로 항상 본체 레포를 찾으므로 cwd 와 무관하게 동작한다.

## 절차

### 0. 사전 점검

두 가지를 확인하고 부족하면 **진행하기 전에** 사용자에게 알린다.

```bash
command -v pandoc >/dev/null 2>&1 && echo "PANDOC_OK" || echo "PANDOC_MISSING"
```

- **pandoc 없음** — 댓글이 마크다운으로 렌더링되지 않고 `{code}` 블록으로 감싸 등록된다. 보고용 댓글에서는 치명적이므로 설치를 권한 뒤 진행 여부를 확인받는다 (`brew install pandoc`).
- **`runtime-verify.modules` 없음** — 런타임 기동이 불가능하다. `/runtime-verify:setup` 을 안내하고, 그대로 진행하면 6단계의 증거 사다리 맨 아래(테스트·로그)로만 검증하게 된다는 점을 알린 뒤 확인받는다.

### 1. 인자 파싱

- 이슈 키: URL 형태(`https://{baseUrl}/browse/PROJ-123`)와 키 형태(`PROJ-123`) 모두 받는다. 없으면 AskUserQuestion 으로 받는다
- `--source <브랜치명>`: 검증할 브랜치. 미지정 시 2단계에서 추론한다

### 2. 검증 대상 브랜치 결정

`--source` 가 없으면 다음 순서로 후보를 찾아 **사용자에게 제시하고 승인받는다.** 임의로 확정하지 않는다.

1. 이슈 키를 포함한 로컬·원격 브랜치
2. `impl-issue` 가 남긴 댓글의 `작업 상태` 항목에 적힌 브랜치명
3. 이슈 키를 커밋 메시지에 포함한 브랜치

```bash
git branch -a --list "*{이슈키}*"
git log --all --oneline --grep="{이슈키}" -20
```

후보가 하나면 그것을 제안하고, 여러 개면 목록으로 물어본다. 하나도 없으면 브랜치명을 직접 받는다.

### 3. 이슈·댓글 조회

이슈 본문과 댓글 전체를 조회한다. 댓글이 **[원인]·[수정] 의 1차 원본**이다.

```bash
curl -s -u "$email:$token" "$baseUrl/rest/api/3/issue/{이슈키}?expand=renderedFields"
curl -s -u "$email:$token" "$baseUrl/rest/api/3/issue/{이슈키}/comment?orderBy=-created&maxResults=30"
```

**원본 식별 규칙** — 댓글은 wiki markup 으로 저장돼 있으므로 마크다운 제목이 아니라 wiki 제목(`h2.`)으로 찾는다:

| 찾을 것 | 쓰임 |
|---------|------|
| `분석 요약` · `확인 근거` 를 포함한 댓글 | [원인] 원본 |
| `구현 결과` · `수정 내용` 을 포함한 댓글 | [수정] 원본 |
| `남은 검증` · `추가 확인 필요` 항목 | 7단계 미검증 후보 |

같은 종류가 여러 건이면 **가장 최근 것**을 쓴다. 원본 댓글이 하나도 없으면(수동 작업한 이슈) 4단계의 커밋 diff 단독으로 원인·수정을 도출하고, 그 사실을 사용자에게 알린다.

### 4. 커밋 diff 교차 검증

댓글 내용을 그대로 믿지 않는다. 실제 커밋과 대조해 어긋나면 사용자에게 알린다.

```bash
base=$(git merge-base origin/HEAD {브랜치명})
git log --oneline "$base".."{브랜치명}"
git diff --stat "$base".."{브랜치명}"
```

- 댓글의 `변경 파일` 목록과 실제 diff 의 파일 목록을 대조한다
- 댓글에 적힌 수정 내용이 diff 에 없거나, diff 에만 있는 중요한 변경이 댓글에 없으면 **양쪽 차이를 사용자에게 보고하고** 어느 쪽을 기준으로 쓸지 확인받는다
- 일치하면 조용히 통과한다

### 5. 런타임 기동

`verify-stack` 의 기동 절차를 그대로 수행한다. 상세 규칙은 [runtime-verify 의 verify-stack SKILL.md](../../../runtime-verify/skills/verify-stack/SKILL.md) 를 읽고 따른다. 핵심만 옮기면:

**포트 산식** — 슬롯 N 포트 = `portBase + N × 1000 + (이슈번호 % 1000)`. Bash 호출은 매번 새 셸이므로 계산한 포트를 **리터럴 숫자로 모든 명령에 직접 삽입**한다.

**선점 검사** — 기동 전에 사용할 슬롯 포트를 전부 확인하고, 물려 있으면 점유 프로세스를 보고한 뒤 확인받는다.

```bash
lsof -nP -iTCP -sTCP:LISTEN | grep -E ":(<슬롯 포트를 |로 나열>)\b"
```

**worktree** — 사용자의 작업 트리를 건드리지 않는다. 대상 브랜치를 checkout 하지 않고 detached worktree 에서만 실행한다.

```bash
git worktree remove --force <PATH> 2>/dev/null; git worktree prune; rm -rf <PATH>
git worktree add --detach <PATH> {브랜치명}
```

worktree 에는 gitignore 된 로컬 설정과 설치 산출물이 없다. `prepare` 명령들을 worktree 루트에서 순서대로 실행한다 (`$MAIN` → 본체 레포 루트).

**기동·헬스** — 모듈마다 **별도의 Bash 호출**로 `run_in_background: true` 기동한다 (한 호출에 묶으면 첫 모듈에서 블로킹된다). 각 모듈 `health` 를 10초 간격으로 폴링하고 기본 타임아웃은 5분이다. JVM 계열은 첫 1분의 연결 실패가 정상이다.

### 6. 브라우저 검증 및 증거 수집

3단계에서 읽은 이슈 설명·댓글의 재현 절차와 기대 결과로 항목별 체크리스트를 만들고, 브라우저 자동화로 사람이 하듯 조작하며 항목마다 통과·실패를 판정한다.

- 격리 단위는 browser context 다. 탭을 격리 단위로 쓰지 않는다
- 로그인이 필요하면 `credentialsFile` 에서 계정을 읽고 **로그·출력·코드에 평문으로 남기지 않는다**
- mutation 검증은 응답만이 아니라 **새로고침 후 재렌더링된 데이터**로 영구 반영을 확인한다

**증거 사다리** — 위에서부터 시도하고, 불가능하면 한 칸 내려간다. 어디까지 내려갔는지 7단계 [결과]에 그대로 적는다.

| 순위 | 증거 | 수집 방법 |
|:--:|------|----------|
| 1 | 화면 스크린샷 | `mcp__playwright__browser_take_screenshot` 으로 검증 전·후 각각 |
| 2 | API 응답 기록 | `mcp__playwright__browser_network_requests` 로 저장·조회 응답 |
| 3 | 테스트·로그 출력 | 런타임 기동 자체가 불가능할 때만 |

**DB 는 직접 조회하지 않는다.** 화면과 API 응답으로 확인되지 않는 항목은 증거를 지어내지 말고 7단계의 미검증으로 넘긴다. 영상 녹화는 현재 브라우저 도구로 불가능하므로 시도하지 않는다.

**파일명 규칙** — 첨부는 이슈 단위로 쌓이므로 같은 이름이 겹치면 구분이 안 된다. `{이슈키}-{항목}-{before|after}.png` 로 짓는다.

### 7. 댓글 초안 작성

세 항목으로 압축한다. 독자는 코드를 읽지 않는 보고 라인이므로 파일 경로·심볼·라인 번호를 넣지 않는다.

```markdown
**[원인]**

{어떤 조건에서 무엇이 기대와 다르게 동작했는지, 그 원인이 무엇이었는지. 2~3문장}

**[수정]**

{무엇을 어떻게 바꿨는지. 코드가 아니라 동작의 변화로 쓴다. 2~3문장}

**[결과]**

{실제로 기동해서 무엇을 확인했는지. 검증한 화면·절차와 확인된 값}

![{항목} 검증 후](이슈키-항목-after.png)

*미검증*

- {항목}: {확인하지 못한 이유} → {확인에 필요한 것}
```

**작성 규칙 — 압축하면서 지켜야 할 것:**

- **미검증 항목을 절대 생략하지 않는다.** 이 스킬의 가장 비싼 실패는 확인하지 못한 것을 확인한 것처럼 쓰는 것이다. 원본 댓글의 `남은 검증`·`추가 확인 필요` 중 이번에 해소되지 않은 항목은 전부 살린다. 미검증이 하나도 없을 때만 `*미검증*` 블록을 생략한다
- 증거 사다리에서 아래로 내려갔으면 그 사실을 [결과]에 적는다. "화면으로 확인" 과 "API 응답으로 확인" 은 다른 강도다
- [원인]·[수정] 은 원본 댓글을 압축한 것이지 새로 판단한 것이 아니다. 원본에 없던 주장을 넣지 않는다
- 검증에 실패한 항목이 있으면 [결과] 첫 문장에 실패 사실을 적는다. 통과 항목으로 문단을 시작해 실패를 묻지 않는다
- 추측을 단정으로 바꾸지 않는다. 원본이 "추정" 으로 표기한 원인은 압축해도 추정으로 남긴다

### 8. 초안 사용자 확인

작성한 초안 **전문을 먼저 일반 텍스트로 출력**한 뒤 AskUserQuestion 으로 등록 여부를 확인한다. 초안을 출력하지 않은 채 AskUserQuestion 을 호출하지 않는다 — 다이얼로그에는 긴 초안이 담기지 않아 사용자가 내용을 보지 못한 채 승인하게 된다. 수정 요청을 받으면 반영한 초안을 다시 출력하고 재확인받는다.

### 9. 증거 첨부 업로드

댓글보다 **먼저** 올린다. 댓글의 이미지 참조는 같은 이슈에 이미 붙어 있는 첨부를 파일명으로 찾는다.

```bash
"${CLAUDE_SKILL_DIR}/../../scripts/jira-issue.sh" attach --key {이슈키} \
  --file {스크린샷 경로} --file {스크린샷 경로}
```

성공하면 첨부된 파일명이 한 줄씩 출력된다. 7단계 초안의 `![...](파일명)` 이 이 파일명과 정확히 일치하는지 대조한다. 어긋나면 댓글에 깨진 이미지가 뜬다.

### 10. 댓글 등록

v2 엔드포인트는 wiki markup 을 받는다. pandoc 으로 변환한 뒤 보낸다. 마크다운 이미지 문법은 `!파일명!` 로 변환돼 Jira 가 같은 이슈의 첨부를 인라인 렌더링한다.

```bash
if command -v pandoc >/dev/null 2>&1; then
  body=$(printf '%s' "$markdown_text" | pandoc -f gfm -t jira)
else
  body="{code}
${markdown_text}
{code}"
fi
payload=$(jq -n --arg b "$body" '{body: $b}')
curl -s -u "$email:$token" -X POST "$baseUrl/rest/api/2/issue/{이슈키}/comment" \
  -H "Content-Type: application/json" -d "$payload"
```

### 11. 상태 전환

**전환 이름을 문자열로 가정하지 않는다.** 워크플로우마다 이름이 다르고(`해결됨` · `해결함` · `완료` · `Done`) 나중에 바뀔 수도 있다. 이름으로 찾아 못 찾으면 조용히 전환을 건너뛰게 되므로, 언어·워크플로우와 무관한 **상태 카테고리**로 고른다.

Jira 의 모든 상태는 세 카테고리 중 하나에 속하고, 이 값은 고정이다:

| `statusCategory.key` | 뜻 | 이름 예시 |
|----------------------|-----|----------|
| `new` | 시작 전 | 열림 · 다시 열림 · To Do |
| `indeterminate` | 진행 중 | 진행 중 · 확인중 · In Progress |
| `done` | 완료 | 해결됨 · 해결함 · 완료 · Done |

전환 목록 조회 응답에 각 전환의 **도착 상태 카테고리**가 함께 들어온다.

```bash
curl -s -u "$email:$token" "$baseUrl/rest/api/3/issue/{이슈키}/transitions" \
  | jq -r '.transitions[] | "\(.id)\t\(.name)\t\(.to.name)\t\(.to.statusCategory.key)"'
```

**목표 카테고리** — 검증 결과로 정한다.

| 검증 결과 | 목표 카테고리 | 근거 |
|-----------|--------------|------|
| 전 항목 통과 | `done` | 실동작까지 확인됐다 |
| 실패 항목 있음 | `indeterminate` | 되돌려서 재작업 대상임을 드러낸다 |
| 기동 불가로 검증 못 함 | 전환하지 않음 | 판단 근거가 없다 |

**전환 선택 사다리** — 위에서부터 내려가며 하나로 좁혀지면 멈춘다.

1. **설정에 지정된 이름** — `jira-tools.transitions` 에 이름이 있고 그 이름이 조회 결과에 실제로 있으면 그것을 쓴다. 가장 결정론적이다

   ```json
   "transitions": { "done": "해결함", "inProgress": "진행 중" }
   ```

2. **목표 카테고리로 후보를 좁힌다** — 위 조회 결과에서 `to.statusCategory.key` 가 목표와 같은 전환만 남긴다. 후보가 1개면 그것을 쓴다
3. **후보가 2개 이상이면 관용 이름으로 한 번 더 좁힌다** — `done` 은 해결·완료·Done·Resolved 를, `indeterminate` 는 진행·In Progress 를 이름에 포함한 것을 우선한다. 여기서 1개로 좁혀지면 그것을 쓴다
4. **그래도 2개 이상이면 사용자에게 묻는다** — 후보 목록(전환 이름 → 도착 상태)을 보여주고 AskUserQuestion 으로 고르게 한다. 임의로 하나를 집지 않는다
5. **후보가 0개면 전환하지 않는다** — 현재 상태에서 목표 카테고리로 가는 길이 없다는 뜻이다. 경고를 출력하고 13단계 결과에 사유를 적는다

고른 전환의 `id` 로 실행한다.

```bash
curl -s -u "$email:$token" -X POST "$baseUrl/rest/api/3/issue/{이슈키}/transitions" \
  -H "Content-Type: application/json" -d '{"transition": {"id": "{전환 id}"}}'
```

전환 후에는 **실제로 바뀐 상태를 다시 읽어 확인한다.** 전환 API 는 화면 필수 필드가 비면 204 를 주고도 상태를 바꾸지 않는 경우가 있다.

```bash
curl -s -u "$email:$token" "$baseUrl/rest/api/3/issue/{이슈키}?fields=status" \
  | jq -r '.fields.status | "\(.name) [\(.statusCategory.key)]"'
```

읽어온 카테고리가 목표와 다르면 전환 실패로 보고한다. 성공으로 적지 않는다.

4·5단계로 빠졌거나 검증 자체가 불가능했다면, 사용자에게 `jira-tools.transitions` 설정을 권고해 다음 실행부터 묻지 않도록 안내한다 (13단계의 설정 권고 블록).

### 12. AI 라벨 추가

```bash
"${CLAUDE_SKILL_DIR}/../../scripts/jira-issue.sh" label --key {이슈키} --add AI
```

### 13. 정리 및 결과 출력

1. 백그라운드 task 를 TaskStop 으로 종료한다
2. 슬롯 포트에 잔존 리스너가 없는지 확인한다 (5단계 lsof 재사용)
3. 이 스킬이 만든 worktree 는 **사용자 확인 후** `git worktree remove` 로 정리한다. detached 이므로 브랜치는 남는다

```
이슈 검증 완료!

- 이슈: {이슈키} ({baseUrl}/browse/{이슈키})
- 검증 브랜치: {브랜치명}
- 검증 결과: {통과 n건 / 실패 m건 / 미검증 k건}
- 증거: 스크린샷 {n}건 첨부
- 댓글: 등록 완료
- 상태: {전환 결과 또는 전환하지 않은 사유}
- 라벨: AI 추가
```

## 주의사항

- **코드를 고치지 않는다.** 검증 실패는 보고하고 멈춘다. 수정은 `impl-issue` 로 다시 돈다
- 사용자의 현재 작업 트리·브랜치에 영향을 주지 않는다 — checkout 금지, detached worktree 만 사용
- credential 을 로그·출력·코드에 평문으로 남기지 않는다
- 확인하지 못한 것을 확인한 것처럼 쓰지 않는다. 보고용으로 짧게 쓰는 것과 불확실성을 지우는 것은 다르다
- 서브에이전트 분석 결과를 그대로 수용하지 않는다 — 핵심 주장은 직접 확인하고, 미검증분은 "추정" 으로 표기한다
- 여러 이슈를 동시에 검증하면 공유 DB 를 통해 서로의 데이터 검증에 간섭할 수 있다. mutation 검증은 시점을 겹치지 않게 한다

## plugins.json 설정 권고 (작업 후)

이번 실행에서 AskUserQuestion 으로 받은 값이 있었다면, 작업 완료 후 [../../reference/config-recommendation.md](../../reference/config-recommendation.md) 의 출력 포맷대로 안내 블록을 출력한다. 모든 값을 plugins.json 에서 얻었으면 생략한다.

- **포함**: AskUserQuestion 으로 받은 값 (예: `baseUrl`, `email`, `apiTokenFile`, `runtime-verify` 의 `modules`·`ui`). 11단계에서 전환을 사용자가 골랐거나 후보를 못 찾았다면 `transitions` 를 함께 권고한다
- **제외**: CLI 인자(이슈 키, `--source`), 추론 후 승인받은 브랜치명, AI 가 판단한 값(검증 결과, 댓글 본문)
