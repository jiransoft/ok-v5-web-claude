---
name: resolve-issue
description: Jira 이슈를 분석하여 원인/수정방향/코드 예시를 정리한 댓글을 등록합니다
when_to_use: 사용자가 이슈 키나 URL(예: PROJ-123)과 함께 "이 이슈 분석해줘", "원인 파악해줘", "수정 방향 정리해서 댓글 달아줘", "resolve jira issue" 등 코드 변경 없이 분석·댓글 등록만 요청할 때.
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/../../scripts/jira-issue.sh *), Bash(git *), Bash(curl *), Bash(jq *), Bash(pandoc *), Bash(command *), Read, Grep, Glob, Agent, AskUserQuestion, WebFetch
argument-hint: "Jira 이슈 키 또는 URL (예: PROJ-123)"
---

# Resolve Issue Skill

Jira 이슈를 조회하고, 코드베이스를 분석하여 원인/수정방향/코드 예시를 정리한 댓글을 등록한다.

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

- **baseUrl** — Atlassian URL (예: `https://xxx.atlassian.net`)
- **projectKey** — 기본 프로젝트 키. **인자로 받은 이슈 키의 프로젝트가 이와 달라도(같은 사이트) 그대로 진행한다** — 인증은 사이트 단위다
- **email** — Atlassian 계정 이메일
- **apiTokenFile** — API 토큰 파일 경로 (예: `~/.jira-token`)

> **토큰 발급**: Atlassian API 토큰은 https://id.atlassian.com/manage-profile/security/api-tokens 에서 발급받아 `~/.jira-token` 파일로 저장한다.

### 인증 헬퍼

모든 Jira REST API 호출에서 아래 패턴으로 인증 정보를 가져온다. 이후 절차에서 `$email`, `$token`, `$baseUrl`을 참조한다.

```bash
eval "$("${CLAUDE_SKILL_DIR}/../../scripts/jira-issue.sh" env)"
token=$(tr -d '\n\r' < "$tokenFile")
```

`env` 는 `baseUrl`·`email`·`tokenFile`·`projectKey`·`pluginsJson` 을 셸 대입문으로 낸다
(토큰 값은 내지 않는다 — stdout 은 트랜스크립트에 남는다).

⚠️ **`.claude/plugins.json` 을 상대경로로 직접 읽지 않는다.** `--source` 로 worktree 를 만들면
그 안에는 `plugins.json` 이 없다 — gitignore 대상이라 체크아웃되지 않기 때문이다. cwd 가
worktree 로 옮겨간 뒤 상대경로로 읽으면 인증 정보가 조용히 빈 값이 된다. 위 스크립트가
`git rev-parse --git-common-dir` 로 항상 본체 레포를 찾으므로 cwd 와 무관하게 동작한다.

## 절차

### 0. 사전 점검 (Preflight)

댓글 등록은 Jira v2 엔드포인트에 wiki markup으로 전송한다. 마크다운 → wiki markup 변환에는 `pandoc`이 필요하므로, 본격적인 분석을 시작하기 전에 설치 여부를 확인한다.

```bash
command -v pandoc >/dev/null 2>&1 && echo "PANDOC_OK" || echo "PANDOC_MISSING"
```

`PANDOC_MISSING`이면 다음 메시지를 사용자에게 전달하고, 응답을 받기 전까지 다음 단계로 진행하지 않는다:

> ⚠ pandoc이 설치되어 있지 않습니다.
> 분석 결과 댓글이 마크다운으로 정상 렌더링되지 않고 `{code}` 블록으로 감싸 등록됩니다 (모노스페이스, 서식 없음).
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
  - `--source <브랜치명>`: worktree 격리 분석용 브랜치 (선택)

### 1-1. Worktree 생성 (--source 지정 시)

`--source`가 지정된 경우, 격리된 worktree를 생성하여 해당 브랜치 코드 기준으로 분석한다.
미지정 시 이 단계를 건너뛰고 현재 디렉토리에서 분석한다 (기존 동작).

```bash
# 스테일 worktree 자기 치유 (이전 실행이 중단돼 남아 있으면 제거)
git worktree remove --force /tmp/wt-{이슈키} 2>/dev/null; git worktree prune; rm -rf /tmp/wt-{이슈키}
git worktree add --detach /tmp/wt-{이슈키} {브랜치명}
```

- `--detach`를 사용하여 브랜치 잠금 충돌을 방지한다 (현재 체크아웃된 브랜치도 지정 가능)
- 이후 코드 분석(4단계)의 모든 Grep, Glob, Read는 worktree 경로(`/tmp/wt-{이슈키}`)를 대상으로 수행한다

### 2. Jira 이슈 조회

```bash
curl -s -u "$email:$token" "$baseUrl/rest/api/3/issue/{이슈키}?expand=renderedFields"
```

이슈의 **요약(summary)**, **설명(description)**, **이슈유형(issuetype)**을 확인한다.

### 2-1. 외부 링크 조회

이슈의 설명(description)에 외부 링크가 포함되어 있는지 확인한다.

**조회 대상 링크:**
- **Confluence** (`*.atlassian.net/wiki/...`) → `WebFetch`로 조회
- **Figma** (`figma.com/design/...`, `figma.com/board/...`) → `WebFetch`로 조회
- **기타 URL** → `WebFetch`로 조회

**처리 규칙:**
- 링크가 여러 개이면 병렬로 조회한다
- 조회 실패 시(권한 없음, 404 등) 해당 링크는 건너뛰고, 3단계에서 컨텍스트 부족 여부를 판단한다
- 조회한 내용은 이후 분석의 추가 컨텍스트로 활용한다

### 2-2. 기존 댓글 조회

이슈에 달린 기존 댓글을 조회하여 분석에 참고한다.

```bash
curl -s -u "$email:$token" "$baseUrl/rest/api/3/issue/{이슈키}/comment?orderBy=-created&maxResults=10" \
  | jq '.comments[] | {author: .author.displayName, body: .body, created: .created}'
```

**처리 규칙:**
- 댓글에 재현 시나리오, 추가 정보, 원인 추측 등 분석에 유용한 내용이 있으면 이후 단계의 컨텍스트로 활용한다
- 댓글이 없으면 건너뛴다

### 3. 정보 충분성 판단

이슈의 요약 + 설명 + 외부 링크 조회 결과 + 기존 댓글을 종합하여 코드 분석이 가능한 수준인지 판단한다.

**분석 가능 조건** (하나 이상 충족):
- API 경로 또는 HTTP 메서드가 명시되어 있다
- 에러 메시지, 스택 트레이스가 포함되어 있다
- 재현 시나리오(어떤 동작에서 어떤 결과가 나오는지)가 기술되어 있다
- 관련 엔티티/서비스/화면명이 특정 가능하다

**정보 부족 시**: 분석을 진행하지 않는다. 아래 템플릿으로 댓글 초안을 작성하고, **5-1단계(사용자 확인)와 동일하게 초안 전문을 출력한 뒤 등록 여부를 확인받는다.** 승인 후 댓글을 등록하고 절차를 종료한다.

```markdown
## 분석 보류 — 정보 부족

이슈 내용만으로는 원인 분석을 진행하기 어렵습니다.
다음 정보가 보충되면 분석을 재시도할 수 있습니다:

- [ ] {부족한 정보 1 (예: 재현 시나리오)}
- [ ] {부족한 정보 2 (예: 에러 메시지 또는 스크린샷)}
- [ ] {부족한 정보 3 (필요 시)}
```

정보 부족 댓글을 등록한 후에도 **7단계(상태 전환)**, **8단계(AI 라벨 추가)**는 동일하게 수행한다.

### 4. 코드베이스 분석

이슈 내용(요약 + 설명)을 기반으로 관련 코드를 탐색한다:

1. **키워드 추출**: 이슈에서 API 경로, 엔티티명, 서비스명, 에러 메시지 등 핵심 키워드를 추출
2. **코드 탐색**: Grep, Glob, Read를 사용하여 관련 코드를 찾는다
   - API 경로가 있으면 Controller부터 추적
   - 엔티티/서비스명이 있으면 해당 파일을 직접 탐색
   - 필요시 Agent(Explore)로 깊이 탐색
3. **원인 파악**: 코드를 읽고 버그의 근본 원인을 분석한다

### 5. 분석 결과 정리

다음 템플릿에 따라 댓글 내용을 구성한다:

```markdown
## 원인 분석

### 버그 위치
`{클래스명.메서드명}` (`{파일 경로}` line {시작}~{끝})

### 근본 원인
{왜 이 버그가 발생하는지 명확하게 설명}

{원인이 되는 코드 블록 인용}

### 재현 예시
{구체적인 시나리오로 버그 재현 과정과 기대값 vs 실제값 비교}

---

## 수정 방향

{어떻게 수정해야 하는지 방향 설명}

{수정 코드 예시 (Kotlin/SQL 등)}

### 수정 대상 파일
| 파일 | 변경 내용 |
|------|----------|
| `{파일 경로 1}` | {무엇을 어떻게 변경} |
| `{파일 경로 2}` | {무엇을 어떻게 변경} |

### 영향 범위
- {이 수정이 영향을 줄 수 있는 다른 기능/모듈}
- {캐시, 이벤트, 동기화 등 사이드이펙트 가능성}

### 테스트 포인트
- [ ] {검증해야 할 시나리오 1}
- [ ] {검증해야 할 시나리오 2}
```

**작성 규칙:**
- 원인은 코드 레벨에서 구체적으로 설명한다 (라인 번호 포함)
- 재현 예시는 비개발자도 이해할 수 있게 작성한다
- 수정 코드는 실제 적용 가능한 수준으로 작성한다
- 불확실한 부분이 있으면 추측하지 말고 "추가 확인 필요"로 표기한다
- **서브에이전트 결과 검증**: Explore 등 서브에이전트의 분석 결과를 그대로 수용하지 않는다. 핵심 주장은 반드시 코드를 직접 읽어서 검증한다. 검증되지 않은 내용은 "확인된 사실"과 구분하여 "추정 — 추가 확인 필요"로 표기한다

### 5-1. 사용자 확인

작성한 댓글 초안 **전문을 먼저 일반 텍스트로 출력**한 뒤, AskUserQuestion으로 등록 여부를 확인한다.

- 초안을 출력하지 않은 채 AskUserQuestion을 호출하지 않는다 — AskUserQuestion 다이얼로그에는 긴 초안이 담기지 않으므로, 사용자가 내용을 보지 못한 상태로 승인하게 된다
- 사용자가 수정을 요청하면 반영한 초안을 다시 출력하고 재확인받는다

### 6. Jira 댓글 등록

v2 엔드포인트를 사용한다. v2의 `comment.body`는 **Jira wiki markup**을 받으므로, 마크다운을 그대로 보내면 `**bold**`, `## heading` 등이 깨져 보인다. `pandoc`으로 wiki markup으로 변환한 뒤 전송한다.

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

### 7. 이슈 상태 전환 ('확인중')

댓글 등록 후 이슈 상태를 '확인중'으로 전환한다.

먼저 가능한 전환 목록을 조회한다:

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

### 8. AI 라벨 추가

기존 라벨을 유지하면서 "AI"를 추가한다.

```bash
curl -s -u "$email:$token" -X PUT "$baseUrl/rest/api/3/issue/{이슈키}" \
  -H "Content-Type: application/json" \
  -d '{"update": {"labels": [{"add": "AI"}]}}'
```

### 9. Worktree 정리 (--source 사용 시)

`--source`로 worktree를 생성한 경우, 분석 완료 후 정리한다.

```bash
git worktree remove /tmp/wt-{이슈키}
```

### 10. 결과 출력

```
이슈 분석 완료!

- 이슈: {이슈키} ({JIRA_BASE_URL}/browse/{이슈키})
- 요약: {이슈 요약}
- 원인: {한 줄 요약}
- 댓글: 등록 완료
- 상태: 확인중으로 전환 (또는 전환 불가 시 사유)
- 라벨: AI 추가
- 분석 브랜치: {브랜치명} (--source 사용 시)
```

## 주의사항

- 코드 분석 시 CLAUDE.md의 아키텍처/패키지 구조를 참고한다
- 원인을 특정할 수 없는 경우, 파악한 범위까지만 기술하고 "추가 확인 필요" 항목을 명시한다
- 이슈 설명에 API 경로가 있으면 Controller → Service → Repository 순으로 추적한다
- 댓글 등록 전 반드시 5-1단계(사용자 확인)를 거친다 — 초안 전문 출력 없이 등록하지 않는다

## plugins.json 설정 권고 (작업 후)
이번 실행에서 AskUserQuestion 으로 받은 값이 있었다면, 작업 완료 후
[../../reference/config-recommendation.md](../../reference/config-recommendation.md) 의 출력 포맷대로
안내 블록을 출력한다. 모든 값을 plugins.json 에서 얻었으면 생략한다.

**권고 대상:**
- **포함**: AskUserQuestion 으로 받은 값 (다음부터 자동 처리되려면 plugins.json 에 저장 필요). 예: `projectKey`, `baseUrl`, `email`, `apiTokenFile`
- **제외**: CLI 인자로 받은 값(이슈 키/URL), AI 가 자동 판단한 값 (원인 분석 결과, 댓글 본문)

