---
name: postman-docs-review
description: Postman 컬렉션의 request 설정(URL, params, body)과 docs를 실제 코드와 비교 검증하고 불일치를 보고한다. Postman URL이나 컬렉션/폴더 지정 시 사용한다.
when_to_use: 사용자가 "postman docs 검토", "postman 검증", "포스트맨 문서 확인", "컬렉션 docs 검토해줘" 등을 요청하거나, Postman URL 또는 검증 대상 컬렉션/폴더를 지정할 때 사용한다.
argument-hint: "<postman-url|collection> [--source <branch|.>] [--base <branch|.>]"
allowed-tools: Bash(curl *), Bash(git *), Bash(python3 *), Bash(grep *), Read, Grep, Glob, Edit, AskUserQuestion, TaskCreate, TaskUpdate
---

# Postman Docs Review Skill

Postman 컬렉션의 **request 설정**(URL, query params, body 예시)과 **documentation**(description)을 실제 코드베이스와 필드 단위로 대조하여 불일치를 찾고 수정한다.

---

## 설정 (`.claude/plugins.json`)

⚠️ **이 스킬의 모든 작업을 시작하기 전에 반드시 `.claude/plugins.json`을 Read 도구로 읽어야 한다. 이 단계를 건너뛰면 안 된다.**

> 📍 경로는 **본체 레포 루트의 `.claude/plugins.json`** 이다. worktree 경로를 대상으로
> 작업 중이어도 설정은 본체에서 읽는다 — `plugins.json` 은 gitignore 대상이라 worktree 에
> 체크아웃되지 않는다. worktree 에서 찾다 실패하면 설정이 있는데도 CLAUDE.md·질문으로
> 조용히 폴백한다.

설정 우선순위:
1. **Read 도구로 `.claude/plugins.json`** 파일의 `postman-tools` 섹션을 직접 읽는다
2. plugins.json이 없거나 값이 누락되면 **프로젝트의 `CLAUDE.md`**에서 설정을 찾는다
3. 둘 다 실패하면 **AskUserQuestion으로 사용자에게 입력받는다**

**주의:** 시스템 컨텍스트에 이미 로드된 값을 사용하지 말고, 반드시 Read 도구로 파일을 직접 읽어서 설정을 가져온다.

```jsonc
{
  "postman-tools": {
    // 필수
    "workspaceId": "8f6b446a-...",          // Postman workspace ID
    "workspaceName": "officekeeper-postman", // Postman workspace 이름
    // 선택
    "backendStack": "Kotlin Spring Boot",    // 백엔드 기술 스택
    "services": {                            // 서비스 구분 (Base URL 변수 매핑)
      "api": "{{API-HOST}}",
      "checkout": "{{CHECKOUT-HOST}}"
    },
    "collections": {                          // 별칭 → 컬렉션 UID (owner-uuid, 선택)
      "api": "owner-uuid",
      "checkout": "owner-uuid2"
    }
  }
}
```
`collections` 는 **별칭 → 컬렉션 UID** 맵이다 (별칭은 팀이 자유롭게, `services` 키와 맞추면 서비스명으로
컬렉션까지 라우팅된다). 대상 컬렉션 결정: 인자/URL > 별칭·UID 직접 지정 > `collections` 가 1개면 자동 >
복수면 문맥(서비스명·별칭 언급)으로 추론, 애매하면 별칭 목록으로 질문.

> Jackson 네이밍 전략은 `plugins.json`에 두지 않는다. 아래 **네이밍 규칙** 섹션의 감지 절차를 따라 프로젝트 설정에서 직접 판별한다.

---

## Documentation 작성 규칙

docs(description)는 **공유 템플릿** [`../../templates/docs-template.md`](../../templates/docs-template.md) 의 빈 스켈레톤을 따른다. 섹션 순서·표 컬럼명·타입·enum·nullable 표기 규칙은 **이 템플릿이 유일한 진실**이며, 자유 양식은 검증 통과로 보지 않는다.

- 첫 줄에 `> Last modified: YYYY-MM-DD` 를 삽입한다 (신규: 현재 날짜, 기존 수정: 갱신)
- 사용하지 않는 섹션은 통째로 삭제하지 말고 본문을 비우거나 "해당 없음"으로 명시한다
- 단, 페이징 보조 섹션(`Pageable 표준` / `Cursor 페이징` / `페이지 응답 래퍼 — *`)은 사용 안 하는 종류를 통째 삭제한다 (둘 중 하나만 남긴다)

> 이 스킬의 **3-B Documentation 검증** 모든 항목(B1~B10)은 위 템플릿 구조를 기준으로 평가한다. 템플릿과 다른 양식의 docs는 해당 항목에서 ❌ 또는 ⚠️ 처리한다.

---

## 네이밍 규칙 (검증 기준)

Jackson 네이밍 전략 감지 절차와 전략별 규칙표는 플러그인 공유 문서를 따른다:
[../../reference/naming-strategy.md](../../reference/naming-strategy.md)

아래 A/B/C 검사 항목에서 "Body JSON 키 네이밍" 또는 "DTO 필드 변환"이라 하면, **감지된 전략에 맞는 변환 규칙**을 의미한다 (SNAKE_CASE → `snake_case`, LOWER_CAMEL_CASE → `camelCase`).

---

## 워크플로우

### 처리 원칙

- **request 단위 순차 처리**: 각 request에 대해 3단계의 A→B→C 27개 항목을 모두 마친 뒤에만 다음 request로 이동한다. 영역(A/B/C) 단위로 모든 request를 한 번에 처리하는 묶음 방식은 금지한다.
- **TaskCreate 의무**: 3단계 진입 직전에 대상 request 수만큼 `TaskCreate`로 task를 생성한다. 각 task 본문에 해당 request의 A/B/C 체크리스트를 인라인으로 둔다. 모든 task가 완료 상태가 되어야 4단계로 넘어간다.
- **배치 분할(7개 임계치)**: 대상 request가 7개를 넘으면 7개 단위로 배치를 나눈다. 한 배치를 마칠 때마다 "N/M 배치 검증 완료" 중간 보고를 출력한 뒤 다음 배치로 진행한다.

### 1단계: 수집 (Collect)

1. 대상 컬렉션을 결정한다:
   - Postman URL이 제공된 경우: URL에서 workspace ID, folder ID 파싱
   - 인자 없이 실행된 경우: `.claude/plugins.json`의 `postman-tools.collections` 를 읽어 —
     **1개면 자동**, 복수면 문맥(서비스명·별칭)으로 추론하고 애매하면 별칭 목록으로 질문한다. 미설정이면 AskUserQuestion으로 질문한다
2. Postman REST API로 컬렉션 가져오기:
   ```bash
   curl -s "https://api.getpostman.com/collections/{owner}-{uuid}" \
     -H "X-Api-Key: ${apiKey}"
   ```
3. 대상 폴더의 각 request에서 추출:
   - `name`, `id`, `method`, `url`, `description`(docs), `body`(예시), `response[]`(saved examples: 각 example의 `name`, `status`, `code`, `body`, `originalRequest.body`)

### 2단계: 매핑 (Map)

1. 각 request URL 패턴으로 코드베이스 Controller 파일 검색 (Grep)
2. Controller 메서드에서 사용하는 Request DTO, Response DTO 식별
3. **모든 DTO 파일을 반드시 Read 도구로 읽는다** (누락 방지)
4. **매핑 표를 화면에 반드시 출력한다** (Map 단계 종료 의무 산출물):

   | Postman Request | Controller (file:line) | Request DTO (path) | Response DTO (path) | 읽은 DTO 파일 목록 |
   |---|---|---|---|---|

   - "읽은 DTO 파일 목록" 칸에는 실제로 Read 도구로 읽은 파일 경로를 모두 나열한다. 비어 있으면 안 된다 (DTO가 본질적으로 없는 경우에만 `—` 허용).
   - 한 endpoint라도 Controller/DTO 매핑이 누락되면 3단계로 진행하지 않는다.

### 3단계: 대조 (Compare)

> **이 단계의 처리 규칙**
> - 각 request마다 3-A → 3-B → 3-C를 **한 번에** 끝낸다. 한 request의 3-A만 끝내고 다음 request의 3-A로 넘어가는 식의 영역 묶음 처리는 금지한다.
> - request마다 TaskCreate로 만든 task를 진행 상태로 갱신하며, 27개 항목 결과를 모두 채워야 task를 완료 처리한다.
> - 7개 임계치(처리 원칙 참고)를 넘기면 배치 단위로 끊는다.

세 가지를 검증한다: **3-A. Request 설정** (Postman request 자체), **3-B. Documentation** (description 텍스트), **3-C. Example** (saved response).

#### 3-A. Request 설정 검증

| # | 검사 항목 | 방법 |
|---|----------|------|
| A1 | URL path 일치 | Postman URL vs Controller의 @RequestMapping + @GetMapping 등 |
| A2 | HTTP Method 일치 | Postman method vs Controller 어노테이션 |
| A3 | Query param 키 네이밍 | URL의 query param 키가 camelCase인지 (어느 전략이든 Query는 camelCase) |
| A4 | Body 예시 JSON 키 네이밍 | body의 JSON 키가 감지된 전략의 규칙(SNAKE_CASE→`snake_case`, 기본→`camelCase`)을 따르는지 |
| A5 | Body 예시 JSON 키 vs DTO 필드 | body의 키가 DTO 필드를 감지된 전략으로 변환한 결과와 일치하는지 |
| A6 | Body 예시값 유효성 | 비정상 값(의미 없는 큰 수, 빈 문자열 등) 감지 |
| A7 | Base URL 변수 통일 | 같은 서비스 내 request끼리 `{{API-HOST}}` vs `{{base_url}}` 혼용 여부 |
| A8 | Path variable 일치 | URL의 `{{policyId}}` 등이 Controller의 @PathVariable과 대응 |
| A9 | endpoint 코드 존재 여부 | Controller에 매칭 endpoint가 있는지 |

#### 3-B. Documentation 검증

> **검증 기준**: [`../../templates/docs-template.md`](../../templates/docs-template.md) 의 스켈레톤 구조. 섹션 순서/표 컬럼명/타입 표기 규칙이 템플릿과 다르면 해당 항목은 ❌ 또는 ⚠️ 처리한다.

| # | 검사 항목 | 방법 |
|---|----------|------|
| B1 | docs 존재 여부 | description != null && length > 0 |
| B2 | Query Param docs 네이밍 | docs 테이블의 param명이 camelCase인지 |
| B3 | Request Body docs 필드 1:1 대조 | docs 테이블의 모든 필드 ↔ DTO 필드(감지된 전략으로 변환) |
| B4 | Response docs 필드 1:1 대조 | docs 테이블의 모든 필드 ↔ Response DTO 필드(감지된 전략으로 변환) |
| B5 | Response 섹션 존재 여부 | GET/PUT/POST(204 제외)에 Response 문서 있는지 |
| B6 | HTTP Status Code | Controller 반환 코드 vs docs 기술 |
| B7 | Sort 파라미터 | docs vs @PageableSchema(sortProperty) |
| B8 | Search 패턴 공통 필드 | POST /search body에 match_type 등 SearchCriteria 필드 포함 여부 |
| B9 | Last modified 줄 존재 | description 최상단에 `> Last modified: YYYY-MM-DD` 줄이 있는지 |
| B10 | Last modified 형식 | 날짜가 `YYYY-MM-DD` 형식을 지키는지 (미래 날짜/비정상 값 아님) |

#### 3-C. Example (saved response) 검증

| # | 검사 항목 | 방법 |
|---|----------|------|
| C1 | Example 존재 여부 | GET/POST/PUT (204 제외)에 최소 1개 saved response example이 있는지 |
| C2 | Example response JSON 키 네이밍 | response body의 JSON 키가 감지된 전략의 규칙을 따르는지 |
| C3 | Example response 필드 ↔ Response DTO 1:1 대조 | example의 모든 키가 Response DTO 필드(감지된 전략으로 변환)와 일치하는지, 누락/잉여 여부 |
| C4 | Example HTTP Status Code | example의 status code가 Controller 반환 코드와 일치 |
| C5 | Example 요청 body 키 네이밍 | example에 포함된 request body JSON 키가 감지된 전략의 규칙을 따르는지 |
| C6 | Example 값 유효성 | 비정상 값(의미 없는 큰 수, 잘못된 enum, placeholder 미치환 등) 감지 |
| C7 | Example 이름 패턴 | `v{YYYYMMDD} {HTTP_STATUS} {STATUS_NAME} - {설명}` 형식 준수 (예: `v20260409 200 OK - 정상 응답`). `postman-example` SKILL의 이름 규칙과 일치해야 함 |
| C8 | Example 커버리지 | 코드에서 도출되는 주요 시나리오(enum 분기, nullable 필드, 비즈니스 에러, 검증 에러, 빈 body, 페이징/정렬)를 충분히 커버하는지. 최소 `200 OK - 정상 응답` 1개는 존재해야 함 |

**3-C 처리 방식 (의무)**:
- 각 saved response를 **이름 단위로 한 개씩** 순차 처리한다. 한 example의 C1~C8을 모두 채운 뒤 다음 example로 넘어간다.
- **C5 검증 시 해당 example의 `originalRequest.body` raw JSON을 보고서에 그대로 인용**한다 (얼버무림 방지).
- example이 0개인 request는 C2~C7을 ❌로 보고한다. "skip" 또는 "—"로 갈음 금지 (단, 204 No Content 응답은 C 영역 전체를 `—`로 표기 가능).

**주의사항**:
- 같은 인터페이스(SearchCriteria, FilterCriteria)를 구현하는 DTO가 여러 개일 때, **모두 개별 검증**한다
- Jackson 전략이 `SNAKE_CASE`인 프로젝트에서는 Response Body가 `snake_case`이므로, 해당 필드명이 Query Param 영역에 있으면 오류로 판단한다 (Query는 언제나 camelCase)
- docs 스타일이 간략하더라도 필드 누락은 이슈로 보고

### 4단계: 보고 (Report)

이슈를 심각도별로 분류하여 보고:

| 심각도 | 기준 |
|--------|------|
| **HIGH** | Response 필드명 불일치, Response 섹션 누락, endpoint 코드 미존재, docs 전체 누락, Example response 필드 불일치, Example status code 불일치 |
| **MEDIUM** | 필드 누락, Query Param 네이밍 오류, Request Body 구조 미문서화, match_type 등 공통 필드 누락, Example 전체 누락, Example JSON 키 네이밍 오류 |
| **LOW** | Filter 테이블 네이밍 혼용, Body 예시값 비정상, Last modified 줄 누락/형식 오류, Example 값 비정상, Example 이름 패턴 불일치, Example 커버리지 부족 |

보고 형식:
```
## 검증 결과: N개 request 중 M건 이슈

### 검증 매트릭스

각 셀은 다음 중 하나로 채워야 한다 (빈 칸 금지):
- ✅ 통과
- ❌ 실패 (아래 심각도 섹션에 이슈로 보고)
- ⚠️ 의심 (확인 필요)
- — 미적용 (예: 204 No Content 응답의 C 항목)

| Request | A1 | A2 | A3 | A4 | A5 | A6 | A7 | A8 | A9 | B1 | B2 | B3 | B4 | B5 | B6 | B7 | B8 | B9 | B10 | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 |
|---------|----|----|----|----|----|----|----|----|----|----|----|----|----|----|----|----|----|----|-----|----|----|----|----|----|----|----|-----|

> "정상 확인 N건" 식 요약 갈음 금지. 모든 셀이 ✅/❌/⚠️/— 중 하나로 명시적으로 채워져야 보고가 완료된 것으로 간주한다.

### HIGH (N건)
| # | Request | 항목 | 문제 |
...

### MEDIUM (N건)
...

### LOW (N건)
...
```

### 5단계: 수정 및 재검증 (Fix & Re-verify)

사용자가 수정까지 요청한 경우("이상한거 수정해줘" 등)에만 수행한다. 보고만 요청했으면 4단계에서 끝낸다.

검증 스킬이 스스로 수정 결과를 다시 검증하지 않으면 "고쳤다고 보고했지만 여전히 틀린" 상태가 남는다.
**아래 루프를 이슈가 0건이 되거나 3회차에 도달할 때까지 반복한다.**

1. **수정 대상 선별** — HIGH → MEDIUM → LOW 순. 코드가 정답이고 Postman 이 오답이라는 전제이며,
   반대로 판단되는 항목(코드 쪽이 틀려 보임)은 수정하지 말고 "코드 확인 필요"로 남긴다.
2. **반영** — `postman-request` 스킬의 "반영 절차"(컬렉션 GET → python3 로 수정 → PUT)를 따른다.
3. **재검증** — 수정한 request 를 대상으로 **3단계 A/B/C 27개 항목을 다시 돌린다.**
   기억에 의존하지 말고 Postman API 로 컬렉션을 **다시 GET** 해서 대조한다.
4. **판정**
   - 이슈 0건 → 루프 종료, 6단계로.
   - 이슈가 남았고 회차 < 3 → 1번으로 돌아간다.
   - 3회차에도 남으면 루프를 멈추고, 남은 이슈를 "자동 수정 실패"로 분류해 원인과 함께 보고한다.
     반복해서 실패하는 항목은 대개 코드 쪽 판단이 필요한 경우다 — 임의로 더 고치지 않는다.

### 6단계: 최종 보고

````
## 수정 결과: N건 수정 / M건 잔여

| 회차 | 수정 시도 | 재검증 통과 | 잔여 |
|------|----------|------------|------|
| 1 | N건 | N건 | N건 |

### 수정 완료 (N건)
| # | Request | 항목 | 수정 전 → 후 |

### 자동 수정 실패 (N건)
| # | Request | 항목 | 3회 시도 후에도 남은 이유 |

### 코드 확인 필요 (N건)
| # | Request | 항목 | 코드 쪽이 틀려 보이는 근거 |
````

---

## `--source` 모드

지정한 브랜치의 코드를 기준으로 Postman 검증을 수행한다. worktree로 격리하여 현재 작업 디렉토리에 영향을 주지 않는다.

```
/postman-docs-review <postman-url> --source feat/OKEP-4215   # feat/OKEP-4215 브랜치에서 리뷰
/postman-docs-review <postman-url> --source .                  # 현재 브랜치에서 리뷰 (축약)
```

### Worktree 생성

`--source .`이면 현재 디렉토리에서 그대로 작업한다 (worktree 생성 안 함).

브랜치명이 지정된 경우:

```bash
# 1) detached HEAD로 worktree 생성 (브랜치 잠금 충돌 방지)
# 스테일 worktree 자기 치유 (이전 실행이 중단돼 남아 있으면 제거)
git worktree remove --force /tmp/wt-postman-review 2>/dev/null; git worktree prune; rm -rf /tmp/wt-postman-review
git worktree add --detach /tmp/wt-postman-review <source>

# 2) 이후 모든 코드 읽기/검증은 worktree 경로에서 수행
# (Postman API 호출은 경로 무관)
```

- 이후 모든 코드 읽기(Controller, DTO 등)는 worktree 경로(`/tmp/wt-postman-review`)에서 수행한다
- Postman API 호출(수집, 반영)은 경로와 무관하므로 그대로 수행한다
- 작업 완료 후 worktree를 정리한다:
  ```bash
  git worktree remove /tmp/wt-postman-review
  ```

### 워크플로우

기존 5단계 워크플로우를 그대로 수행하되, 코드 참조 경로만 worktree 경로로 바뀐다.
`--base`와 조합하지 않은 경우, 사용자가 지정한 Postman URL/폴더의 전체 request를 대상으로 검증한다.

---

## `--base` 모드

브랜치에서 변경된 API endpoint만 대상으로 Postman 검증/생성을 수행한다.
`--source`와 조합하여 사용할 수 있다.

```
/postman-docs-review <postman-url> --base develop              # 현재 브랜치 vs develop
/postman-docs-review <postman-url> --base .                     # 현재 브랜치 vs base branch (자동 탐지)
/postman-docs-review <postman-url> --source feat/OKEP-4215 --base develop  # 조합: feat/OKEP-4215 worktree에서 develop 대비 diff
```

### base branch 자동 탐지 (`--base .`)

> 이하 `<source>`는 `--source` 지정 시 해당 브랜치, 미지정 시 `HEAD`를 가리킨다.

```bash
git branch -r
git merge-base <source> <each-branch>
git rev-list --count <merge-base>..<source>
```

1. `git branch -r`로 원격 브랜치 목록을 가져온다
2. 소스 브랜치 자신은 제외한다 (자기 자신 비교 방지)
3. 각 원격 브랜치와 `git merge-base <source> origin/<branch>`를 계산한다
4. merge-base에서 소스까지의 커밋 수(`git rev-list --count <merge-base>..<source>`)가 **가장 적은** 브랜치를 base로 선택한다
   - 예: `origin/feature/PROJ-100`과의 거리가 3커밋, `origin/develop`과의 거리가 15커밋 → base = `feature/PROJ-100`
5. 원격 브랜치가 없거나 계산 실패 시, 저장소의 기본 브랜치를 자동 감지해 사용한다: `git symbolic-ref --short refs/remotes/origin/HEAD`(예: `origin/main`)의 결과에서 `origin/`을 떼어 base로 쓰고, 이마저 없으면 `develop`을 최종 폴백으로 한다

### 워크플로우 (기존 5단계 중 1~2단계를 대체)

#### D1단계: endpoint 추출 (Replace 1단계)

1. 변경된 Controller 파일 목록을 가져온다:
   ```bash
   git diff <base>...<source> --name-only -- '*.kt' '*.java' | xargs grep -l '@RestController\|@Controller'
   ```
2. 각 Controller 파일에서 **새로 추가/수정된 endpoint**를 식별한다:
   ```bash
   git diff <base>...<source> -- <controller-file>
   ```
3. diff에서 추가된(`+`) `@GetMapping`, `@PostMapping`, `@PutMapping`, `@DeleteMapping`, `@PatchMapping` 라인을 파싱하여 **추가/변경 endpoint** 목록을 구성한다:
   ```
   {method, url_pattern, controller_file, line_number, change_type: "added"}
   ```
4. diff에서 제거된(`-`) `@XxxMapping` 라인도 파싱하여 **삭제 후보 endpoint** 목록을 구성한다:
   ```
   {method, url_pattern, controller_file, change_type: "removed"}
   ```
5. 삭제 후보 중 **현재 코드에 여전히 존재하는 endpoint는 제외**한다 (리네임/이동 구분):
   ```bash
   # 현재 코드(또는 worktree)에서 해당 URL 패턴이 존재하는지 확인
   grep -r '<url_pattern>' --include='*.kt' --include='*.java' <src-dir>
   ```
   - 현재 코드에 같은 method + url_pattern이 있으면 → 이동/리네임으로 판단, 삭제 후보에서 제외
   - 현재 코드에 없으면 → 진짜 삭제된 endpoint로 확정

#### D2단계: Postman 매칭 (Replace 2단계)

1. Postman 컬렉션을 가져온다 (기존 1단계 수집과 동일)
2. 추출된 각 endpoint를 Postman의 request와 **URL path + HTTP Method**로 매칭한다
3. 매칭 결과를 분류:

| 결과 | 다음 단계 |
|------|----------|
| **추가 endpoint → Postman에 없음** | → D3단계 (생성) |
| **추가/변경 endpoint → Postman에 있음** | → 기존 3단계 (대조/리뷰) |
| **삭제 endpoint → Postman에 있음** | → D4단계 (삭제 보고) |
| **삭제 endpoint → Postman에 없음** | → 무시 (이미 정리됨) |

#### D3단계: 신규 endpoint 보고

Postman에 없는 endpoint를 **신규 생성 대상**으로 보고한다. Controller에서 HTTP method, URL 패턴, DTO 정보를 추출하여 보고에 포함한다.

#### D4단계: 삭제 보고 (삭제된 endpoint)

코드에서 삭제된 endpoint에 대응하는 Postman request를 식별하여 보고한다.

1. D1단계에서 확정된 삭제 endpoint 목록과 Postman request를 매칭한다
2. 매칭된 request를 **삭제 후보**로 사용자에게 보고한다
3. MCP 도구로 request 삭제가 불가하므로, **사용자가 Postman에서 직접 삭제**하도록 안내한다
   - request 이름, 폴더 위치, URL을 명시하여 찾기 쉽게 한다

#### 이후 단계

- Postman에 **있던** request → 기존 3단계(대조) → 4단계(보고)
- Postman에 **없는** endpoint → 신규 생성 대상으로 보고
- 코드에서 **삭제**된 request → 삭제 후보로 보고

### 보고 형식 (--base 모드)

```
## 브랜치 검증 결과: N개 endpoint

### 신규 생성 (N건)
| # | Method | URL | Postman Request |
...

### 리뷰 결과 (N건)
(기존 보고 형식과 동일)

### 삭제 후보 (N건)
| # | Method | URL | Postman Request | 폴더 |
...
⚠️ 위 request는 코드에서 삭제된 endpoint입니다. Postman에서 직접 삭제해주세요.
```

---

## 사용 예시

```
# Postman URL 전달
사용자: https://officekeeper-postman.postman.co/workspace/...?folder=...  여기 docs 검토해줘

# 특정 폴더만
사용자: OKEP-local 컬렉션 API 폴더만 검토해줘

# 수정까지
사용자: docs 검토하고 이상한거 수정해줘

# 특정 브랜치에서 리뷰 (worktree 격리)
사용자: /postman-docs-review <postman-url> --source feat/OKEP-4215

# 현재 브랜치에서 리뷰 (축약)
사용자: /postman-docs-review <postman-url> --source .

# 변경된 endpoint만 검증 (develop 대비 diff)
사용자: /postman-docs-review <postman-url> --base develop

# base branch 자동 탐지하여 diff
사용자: /postman-docs-review <postman-url> --base .

# 조합: 특정 브랜치 worktree에서 develop 대비 변경분만 검증
사용자: /postman-docs-review <postman-url> --source feat/OKEP-4215 --base develop
```

## plugins.json 설정 권고 (작업 후)
이번 실행에서 AskUserQuestion 으로 받은 값이 있었다면, 작업 완료 후
[../../reference/config-recommendation.md](../../reference/config-recommendation.md) 의 출력 포맷대로
안내 블록을 출력한다. 모든 값을 plugins.json 에서 얻었으면 생략한다.

**권고 대상:**
- **포함**: AskUserQuestion 으로 받은 값 (다음부터 자동 처리되려면 plugins.json 에 저장 필요). 예: `workspaceId`, `workspaceName`, `apiKey`, `backendStack`, `services`, `collections`
- **제외**: CLI 인자로 받은 값(`--source`, `--base`, Postman URL), AI 가 자동 판단한 값 (네이밍 전략, 불일치 보고서 본문)

