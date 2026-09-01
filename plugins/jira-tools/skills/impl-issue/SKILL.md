---
name: impl-issue
description: Jira 이슈를 조회하고, TDD 방식으로 코드를 구현한 뒤 결과를 댓글로 등록합니다
when_to_use: 사용자가 이슈 키나 URL(예: PROJ-123)과 함께 "이 이슈 구현해줘", "이슈 코드 작성해줘", "TDD로 만들어줘", "implement jira issue" 등 실제 코드 구현까지 요청할 때.
allowed-tools: Grep, Glob, Read, Edit, Write, Bash(${CLAUDE_SKILL_DIR}/../../scripts/jira-issue.sh *), Bash(git *), Bash(cd *), Bash(curl *), Bash(jq *), Bash(pandoc *), Bash(command *), Agent, AskUserQuestion
argument-hint: "Jira 이슈 키 또는 URL (예: PROJ-123)"
---

# Impl Issue Skill

Jira 이슈를 조회하고, 코드베이스를 분석하여 TDD 방식으로 구현한 뒤 결과를 Jira 댓글로 등록한다.

## --help 처리

`$ARGUMENTS`가 `--help` 또는 `-h` 면 [reference/usage.md](reference/usage.md) 의 사용법 블록을 그대로 출력하고 즉시 종료한다.

## Jira 설정

⚠️ **이 스킬의 모든 작업을 시작하기 전에 반드시 `.claude/plugins.json`을 Read 도구로 읽어야 한다. 이 단계를 건너뛰면 안 된다.**

> 📍 경로는 **본체 레포 루트의 `.claude/plugins.json`** 이다. worktree 경로를 대상으로
> 작업 중이어도 설정은 본체에서 읽는다 — `plugins.json` 은 gitignore 대상이라 worktree 에
> 체크아웃되지 않는다. worktree 에서 찾다 실패하면 설정이 있는데도 CLAUDE.md·질문으로
> 조용히 폴백한다.

설정 우선순위:
1. **Read 도구로 `.claude/plugins.json`** 파일의 `jira-tools` 섹션을 직접 읽는다
2. plugins.json이 없거나 값이 누락되면 **프로젝트의 `CLAUDE.md`**에서 Jira 설정을 찾는다
3. 둘 다 실패하면 **AskUserQuestion으로 사용자에게 입력받는다**

시스템 컨텍스트에 이미 로드된 값을 사용하지 말고, 반드시 Read 도구로 파일을 직접 읽어서 설정을 가져온다.

- **cloudId** — Jira Cloud 인스턴스 ID
- (프로젝트 키 설정은 필요 없다 — 인자로 받은 이슈 키/URL 이 프로젝트를 결정하고, 인증은 사이트 단위다)
- **baseUrl** — Atlassian URL (예: `https://xxx.atlassian.net`)
- **email** — Atlassian 계정 이메일 (REST API 인증용)
- **apiTokenFile** — API 토큰 파일 경로 (예: `~/.jira-token`)

> **토큰 생성**: https://id.atlassian.com/manage-profile/security/api-tokens 에서 API 토큰을 생성한 뒤, `apiTokenFile` 경로에 저장한다.

### Jira REST API 인증 헬퍼

이 스킬의 모든 Jira API 호출에서 아래 변수를 사용한다. 각 단계에서 curl 실행 전에 이 변수들을 설정한다:

```bash
eval "$("${CLAUDE_SKILL_DIR}/../../scripts/jira-issue.sh" env)"
token=$(tr -d '\n\r' < "$tokenFile")
```

`env` 는 `baseUrl`·`email`·`tokenFile`·`projects`·`pluginsJson` 을 셸 대입문으로 낸다
(토큰 값은 내지 않는다 — stdout 은 트랜스크립트에 남는다).

⚠️ **`.claude/plugins.json` 을 상대경로로 직접 읽지 않는다.** `--source` 로 worktree 를 만들면
그 안에는 `plugins.json` 이 없다 — gitignore 대상이라 체크아웃되지 않기 때문이다. cwd 가
worktree 로 옮겨간 뒤 상대경로로 읽으면 인증 정보가 조용히 빈 값이 된다. 위 스크립트가
`git rev-parse --git-common-dir` 로 항상 본체 레포를 찾으므로 cwd 와 무관하게 동작한다.

## 절차

15단계 중 하나라도 건너뛰면 "구현은 됐는데 Jira 는 그대로"인 상태가 남는다.
**아래 체크리스트를 응답에 복사해두고 단계마다 갱신한다.**

```
- [ ] 0. 사전 점검 (pandoc·jq·인증)
- [ ] 1. 인자 파싱  ( [ ] 1-1. Worktree 생성 — --source 시 )
- [ ] 2. Jira 이슈 조회  ( [ ] 2-1. 댓글 조회 )
- [ ] 3. 정보 충분성 판단  → 부족하면 여기서 중단·보고
- [ ] 4. 코드베이스 분석
- [ ] 5. 구현 계획 수립 및 사용자 확인  → 승인 전 코드 수정 금지
- [ ] 6. 이슈 상태 전환 ('진행 중')
- [ ] 7. TDD 구현
- [ ] 8. 코드 리뷰
- [ ] 9. 커밋
- [ ] 10. Jira 댓글 등록  ( [ ] 10-1. 댓글 초안 사용자 확인 → 승인 전 등록 금지 )
- [ ] 11. 이슈 상태 전환 ('확인중')
- [ ] 12. AI 라벨 추가
- [ ] 13. Worktree 정리 — --source 시
- [ ] 14. 결과 출력
```

3단계에서 중단한 경우 4~14 는 수행하지 않는다. 그 외에는 앞 단계를 완료하지 않은 채
다음 단계로 넘어가지 않는다.

### 0. 사전 점검 (Preflight)

구현 결과 댓글은 Jira v2 엔드포인트에 wiki markup으로 전송한다. 마크다운 → wiki markup 변환에는 `pandoc`이 필요하므로, 본격적인 구현을 시작하기 전에 설치 여부를 확인한다.

```bash
command -v pandoc >/dev/null 2>&1 && echo "PANDOC_OK" || echo "PANDOC_MISSING"
```

`PANDOC_MISSING`이면 다음 메시지를 사용자에게 전달하고, 응답을 받기 전까지 다음 단계로 진행하지 않는다:

> ⚠ pandoc이 설치되어 있지 않습니다.
> 구현 결과 댓글이 마크다운으로 정상 렌더링되지 않고 `{code}` 블록으로 감싸 등록됩니다 (모노스페이스, 서식 없음).
>
> 깔끔한 렌더링을 원하면 먼저 설치해주세요:
> - macOS: `brew install pandoc`
> - Ubuntu/Debian: `sudo apt install pandoc`
> - 기타: https://pandoc.org/installing.html
>
> 이대로 진행할까요? (진행 / 설치 후 다시 실행)

`PANDOC_OK`이면 안내 없이 다음 단계로 진행한다.

### 1. 인자 파싱

- `$ARGUMENTS`에서 이슈 키와 옵션을 추출한다
  - 이슈 키:
    - URL 형태: `https://{JIRA_BASE_URL}/browse/PROJ-123` → `PROJ-123`
    - 키 형태: `PROJ-123` → 그대로 사용
    - 없으면 AskUserQuestion으로 입력받는다
  - `--source <브랜치명>`: worktree 격리 구현용 브랜치 (선택)

### 1-1. Worktree 생성 (--source 지정 시)

`--source`가 지정된 경우, 격리된 worktree를 생성하여 해당 브랜치 코드 기준으로 구현한다.
미지정 시 이 단계를 건너뛰고 현재 디렉토리에서 구현한다 (기존 동작).

```bash
# 스테일 worktree 자기 치유 (이전 실행이 중단돼 남아 있으면 제거)
git worktree remove --force /tmp/wt-{이슈키} 2>/dev/null; git worktree prune; rm -rf /tmp/wt-{이슈키}
# 1) detached HEAD로 worktree 생성 (브랜치 잠금 충돌 방지)
git worktree add --detach /tmp/wt-{이슈키} {브랜치명}

# 2) worktree로 이동하여 작업 브랜치 생성
cd /tmp/wt-{이슈키}
git checkout -b {prefix}/{이슈키}
```

- `{prefix}`는 이슈유형에 따라 결정: 버그→`fix`, 새 기능→`feat`, 리팩토링→`refactor`
- 이후 모든 작업(분석, 구현, 테스트, 커밋)은 worktree 경로(`/tmp/wt-{이슈키}`)에서 수행한다

### 2. Jira 이슈 조회

```bash
curl -s -u "$email:$token" "$baseUrl/rest/api/3/issue/{이슈키}?expand=renderedFields"
```

이슈의 **요약(summary)**, **설명(description)**, **이슈유형(issuetype)**을 확인한다.

### 2-1. 댓글 조회

이슈에 달린 댓글을 조회하여 추가 컨텍스트를 수집한다.

```bash
curl -s -u "$email:$token" "$baseUrl/rest/api/3/issue/{이슈키}/comment?orderBy=-created&maxResults=20"
```

댓글에는 담당자 간 논의, 추가 요구사항, 재현 방법, 스크린샷 등 구현에 필요한 중요 정보가 포함되어 있을 수 있다.

**처리 규칙:**
- 댓글이 없으면 이 단계를 건너뛴다
- 댓글이 있으면 내용을 요약하여 이후 분석에 활용한다
- 댓글의 첨부 파일이나 외부 링크는 별도 조회하지 않는다

### 3. 정보 충분성 판단

이슈의 요약 + 설명 + 댓글을 종합하여 구현이 가능한 수준인지 판단한다.

**구현 가능 조건** (하나 이상 충족):
- API 경로 또는 HTTP 메서드가 명시되어 있다
- 에러 메시지, 스택 트레이스가 포함되어 있다
- 재현 시나리오(어떤 동작에서 어떤 결과가 나오는지)가 기술되어 있다
- 관련 엔티티/서비스/화면명이 특정 가능하다
- 구현할 기능의 요구사항이 명확하다

**정보 부족 시**: 구현을 진행하지 않는다. 아래 템플릿으로 댓글 초안을 작성하고, **10-1단계(댓글 초안 사용자 확인)와 동일하게 초안 전문을 출력한 뒤 등록 여부를 확인받는다.** 승인 후 댓글을 등록하고 11단계(상태 전환), 12단계(AI 라벨)를 수행하고 종료한다.

```markdown
## 구현 보류 — 정보 부족

이슈 내용만으로는 구현을 진행하기 어렵습니다.
다음 정보가 보충되면 구현을 재시도할 수 있습니다:

- [ ] {부족한 정보 1 (예: 재현 시나리오)}
- [ ] {부족한 정보 2 (예: 에러 메시지 또는 스크린샷)}
- [ ] {부족한 정보 3 (필요 시)}
```

### 4. 코드베이스 분석

이슈 내용(요약 + 설명)을 기반으로 관련 코드를 탐색한다:

1. **키워드 추출**: 이슈에서 API 경로, 엔티티명, 서비스명, 에러 메시지 등 핵심 키워드를 추출
2. **코드 탐색**: Grep, Glob, Read를 사용하여 관련 코드를 찾는다
   - API 경로가 있으면 Controller부터 추적
   - 엔티티/서비스명이 있으면 해당 파일을 직접 탐색
   - 필요시 Agent(Explore)로 깊이 탐색
3. **원인/구현 방향 파악**: 코드를 읽고 버그의 근본 원인 또는 기능 구현 방향을 분석한다
4. **서브에이전트 결과 검증**: Explore 등 서브에이전트의 분석 결과를 그대로 수용하지 않는다. 핵심 주장은 반드시 코드를 직접 읽어서 검증한다. 검증되지 않은 내용은 "확인된 사실"과 구분하여 "추정 — 추가 확인 필요"로 표기한다

### 5. 구현 계획 수립 및 사용자 확인

분석 결과를 바탕으로 구현 계획을 작성하여 사용자에게 보여준다:

```
## 구현 계획

### 이슈 요약
{이슈 요약}

### 원인 분석 (버그인 경우)
{근본 원인 설명}

### 구현 방향
{어떻게 구현/수정할 것인지}

### 수정 대상 파일
| 파일 | 변경 내용 |
|------|----------|
| `{파일 경로}` | {변경 내용} |

### TDD 순서
1. {테스트 1}: {테스트 설명}
2. {테스트 2}: {테스트 설명}
...
```

AskUserQuestion으로 계획 승인을 받는다. 사용자가 수정을 요청하면 반영한다.

### 6. 이슈 상태 전환 ('진행 중')

구현 시작 전에 이슈 상태를 '진행 중'으로 전환한다.

가능한 전환 목록을 조회한다:

```bash
curl -s -u "$email:$token" "$baseUrl/rest/api/3/issue/{이슈키}/transitions"
```

응답에서 name이 "진행 중"인 전환의 `id`를 찾아 전환을 실행한다:

```bash
curl -s -u "$email:$token" -X POST "$baseUrl/rest/api/3/issue/{이슈키}/transitions" \
  -H "Content-Type: application/json" \
  -d '{"transition": {"id": "{진행 중 전환 id}"}}'
```

"진행 중" 전환이 없으면 (이미 진행 중이거나 전환 불가) 경고를 출력하고 다음 단계로 진행한다.

### 7. TDD 구현

CLAUDE.md의 TDD 규칙을 따라 구현한다:

```
Red → Green → Refactor → 반복
```

**레이어별 진행 순서:**
```
Repository 테스트 → Repository 구현
    ↓
Service 테스트 → Service 구현
    ↓
Controller 테스트 → Controller 구현
```

**각 사이클마다:**

1. **Red** — 실패하는 테스트를 먼저 작성한다
   - 테스트 실행하여 실패 확인 (CLAUDE.md의 테스트 실행 명령 사용)
2. **Green** — 테스트를 통과하는 최소한의 코드를 구현한다
   - 테스트 실행하여 통과 확인
3. **Refactor** — 코드를 정리한다
   - 중복 제거, 네이밍 개선, 패턴 정리
   - 리팩토링 후 테스트가 여전히 통과하는지 확인

**TDD 적용 제외 대상** (해당 시 테스트 없이 바로 구현):
- 설정 변경 (application.yml, build.gradle 등)
- 단순 DTO 추가/수정
- 마이그레이션 SQL 추가
- 리팩토링 (기존 테스트가 이미 있는 경우)

### 8. 코드 리뷰

구현 완료 후 code-reviewer Agent로 코드 리뷰를 수행한다:

```
Agent(subagent_type: "code-reviewer", prompt: "변경된 코드를 리뷰해주세요")
```

리뷰 지적사항이 있으면 반영한 후 테스트를 재실행한다.

### 9. 커밋

`git-workflow:commit` 스킬이 있으면 그 스킬로 커밋한다 — 이슈 키를 인자로 넘긴다:

```
Skill(skill: "git-workflow:commit", args: "{이슈키} {구현 요약}")
```

없으면 변경 파일을 스테이징하고 직접 커밋한다. 어느 쪽이든 이슈 키 `{이슈키}` 를
커밋 메시지에 포함한다.

메시지 형식·type 선택·분리 판단은 스킬 또는 저장소의 커밋 컨벤션을 따른다 — 여기서
규격을 다시 정의하지 않는다.

### 10. Jira 댓글 등록

커밋 후 현재 브랜치명과 commit hash를 조회한다:

```bash
git rev-parse --abbrev-ref HEAD   # 브랜치명
git rev-parse --short HEAD         # commit hash
```

구현 결과 댓글 초안을 다음 템플릿으로 작성한다:

```markdown
## 구현 완료

**브랜치**: `{브랜치명}`
**커밋**: `{commit hash}`

### 변경 요약
{무엇을 어떻게 변경했는지 간결하게}

### 변경 파일
| 파일 | 변경 내용 |
|------|----------|
| `{파일 경로 1}` | {변경 내용} |
| `{파일 경로 2}` | {변경 내용} |

### 테스트
- {테스트 클래스 1}: {테스트 내용 요약}
- {테스트 클래스 2}: {테스트 내용 요약}

### 영향 범위
- {이 수정이 영향을 줄 수 있는 다른 기능/모듈}

### 검증 포인트
- [ ] {QA가 확인해야 할 시나리오 1}
- [ ] {QA가 확인해야 할 시나리오 2}
```

### 10-1. 댓글 초안 사용자 확인

작성한 댓글 초안 **전문을 먼저 일반 텍스트로 출력**한 뒤, AskUserQuestion으로 등록 여부를 확인한다.

- 초안을 출력하지 않은 채 AskUserQuestion을 호출하지 않는다 — AskUserQuestion 다이얼로그에는 긴 초안이 담기지 않으므로, 사용자가 내용을 보지 못한 상태로 승인하게 된다
- 사용자가 수정을 요청하면 반영한 초안을 다시 출력하고 재확인받는다

승인을 받은 후 등록을 진행한다. v2 엔드포인트를 사용한다. v2의 `comment.body`는 **Jira wiki markup**을 받으므로, 마크다운을 그대로 보내면 서식이 깨져 보인다. `pandoc`으로 wiki markup으로 변환한 뒤 전송한다 (Step 0에서 설치 여부를 사전 확인).

```bash
# 1) 마크다운 → Jira wiki markup 변환 (pandoc 미설치 시 {code} 블록으로 폴백)
if command -v pandoc >/dev/null 2>&1; then
  body=$(printf '%s' "$markdown_text" | pandoc -f gfm -t jira)
else
  body="{code}
${markdown_text}
{code}"
fi

# 2) jq로 JSON 페이로드 안전하게 빌드 (특수문자 이스케이프)
payload=$(jq -n --arg b "$body" '{body: $b}')

# 3) v2 엔드포인트로 등록
curl -s -u "$email:$token" -X POST "$baseUrl/rest/api/2/issue/{이슈키}/comment" \
  -H "Content-Type: application/json" \
  -d "$payload"
```

### 11. 이슈 상태 전환 ('확인중')

가능한 전환 목록을 조회한다:

```bash
curl -s -u "$email:$token" "$baseUrl/rest/api/3/issue/{이슈키}/transitions"
```

응답에서 name이 "확인중"인 전환의 `id`를 찾아 전환을 실행한다:

```bash
curl -s -u "$email:$token" -X POST "$baseUrl/rest/api/3/issue/{이슈키}/transitions" \
  -H "Content-Type: application/json" \
  -d '{"transition": {"id": "{확인중 전환 id}"}}'
```

"확인중" 전환이 없으면 (현재 상태에서 전환 불가) 경고를 출력하고 다음 단계로 진행한다.

### 12. AI 라벨 추가

`update` 동사의 `add` 연산을 사용하여 기존 라벨을 유지하면서 "AI"를 추가한다:

```bash
curl -s -u "$email:$token" -X PUT "$baseUrl/rest/api/3/issue/{이슈키}" \
  -H "Content-Type: application/json" \
  -d '{"update": {"labels": [{"add": "AI"}]}}'
```

### 13. Worktree 정리 (--source 사용 시)

`--source`로 worktree를 생성한 경우, 구현 완료 후 정리한다.

```bash
git worktree remove /tmp/wt-{이슈키}
```

- 커밋은 `{prefix}/{이슈키}` 브랜치에 남아 있으므로 worktree를 제거해도 작업이 유실되지 않는다
- push가 완료된 상태이므로 안전하게 제거 가능하다

### 14. 결과 출력

```
이슈 구현 완료!

- 이슈: {이슈키} ({JIRA_BASE_URL}/browse/{이슈키})
- 요약: {이슈 요약}
- 변경: {변경 요약 한 줄}
- 브랜치: {prefix}/{이슈키} (--source 사용 시)
- 테스트: 전체 통과
- 댓글: 등록 완료
- 상태: 진행 중 → 확인중 (또는 전환 불가 시 사유)
- 라벨: AI 추가
```

## 주의사항

- CLAUDE.md의 아키텍처/패키지 구조/코딩 컨벤션을 반드시 따른다
- TDD 사이클을 생략하지 않는다 (적용 제외 대상 제외)
- 구현 전 반드시 사용자에게 계획을 확인받는다
- 댓글 등록 전 반드시 10-1단계(댓글 초안 사용자 확인)를 거친다 — 초안 전문 출력 없이 등록하지 않는다
- 기존 코드의 패턴과 스타일을 따른다 — 새로운 패턴을 도입하지 않는다
- 이슈 범위를 벗어나는 리팩토링이나 개선은 하지 않는다
- 불확실한 부분이 있으면 AskUserQuestion으로 사용자에게 확인한다

## plugins.json 설정 권고 (작업 후)
이번 실행에서 AskUserQuestion 으로 받은 값이 있었다면, 작업 완료 후
[../../reference/config-recommendation.md](../../reference/config-recommendation.md) 의 출력 포맷대로
안내 블록을 출력한다. 모든 값을 plugins.json 에서 얻었으면 생략한다.

**권고 대상:**
- **포함**: AskUserQuestion 으로 받은 값 (다음부터 자동 처리되려면 plugins.json 에 저장 필요). 예: `baseUrl`, `email`, `apiTokenFile`
- **제외**: CLI 인자로 받은 값(이슈 키/URL), AI 가 자동 판단한 값 (구현 내용, 코드 변경, 커밋 메시지)

