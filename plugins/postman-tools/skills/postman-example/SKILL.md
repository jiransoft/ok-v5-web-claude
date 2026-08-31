---
name: postman-example
description: Postman 컬렉션의 request에 example(response)을 생성한다. 코드의 Request/Response DTO를 분석하여 실제 코드와 일치하는 example을 자동 생성한다.
when_to_use: 사용자가 "postman example 생성", "포스트맨 예제 만들어", "example 만들어줘", "saved response 추가해줘" 등 컬렉션 request에 example(response)을 추가하도록 요청할 때 사용한다.
argument-hint: "[<collection>] [--source <branch>]"
allowed-tools: Bash(curl *), Bash(git *), Bash(python3 *), Bash(grep *), Read, Grep, Glob, AskUserQuestion, Agent
---

# Postman Example 생성 Skill

Postman 컬렉션의 request에 example(saved response)을 생성한다.

## 옵션

| 옵션 | 설명 |
|------|------|
| `--source <branch>` | 분석할 브랜치 지정 (worktree 격리). 미지정 시 현재 브랜치. |

## 워크플로우

### 0단계: 설정 읽기 (필수)

⚠️ **이 스킬의 모든 작업을 시작하기 전에 반드시 `.claude/plugins.json`을 Read 도구로 읽어야 한다. 이 단계를 건너뛰면 안 된다.**

> 📍 경로는 **본체 레포 루트의 `.claude/plugins.json`** 이다. worktree 경로를 대상으로
> 작업 중이어도 설정은 본체에서 읽는다 — `plugins.json` 은 gitignore 대상이라 worktree 에
> 체크아웃되지 않는다. worktree 에서 찾다 실패하면 설정이 있는데도 CLAUDE.md·질문으로
> 조용히 폴백한다.

Read 도구로 `.claude/plugins.json`의 `postman-tools` 섹션을 읽는다. 파일이 없거나 값이 누락되면 프로젝트의 `CLAUDE.md`에서 찾고, 둘 다 실패하면 AskUserQuestion으로 사용자에게 입력받는다. 시스템 컨텍스트에 이미 로드된 값을 사용하지 않는다.

**필수 설정:**
- `apiKey` — Postman API 키 (`PMAK-...`). 컬렉션 owner와 동일 계정이어야 함.
- `collectionUid` — 기본 컬렉션 UID (선택, `--collection`으로 오버라이드 가능)

**Jackson 네이밍 전략 감지 (example 생성 전 필수):**

`plugins.json`에는 두지 않는다. 프로젝트의 Spring 설정에서 직접 감지한다.

먼저 **탐색 루트**를 정한다. 이 값을 이후 모든 grep 에 붙인다 — 상대경로로 두면 `--source`
모드에서 worktree 가 아니라 현재 cwd(본체)를 읽어, **지정한 브랜치가 아닌 다른 브랜치의**
설정으로 필드명을 만든다. 에러 없이 결과만 틀리므로 발견이 늦다.

```bash
# --source 로 worktree 를 만들었으면 그 경로, 아니면 현재 레포 루트
ROOT=/tmp/wt-postman-example        # --source 미지정 시: ROOT=$(git rev-parse --show-toplevel)
```

1. `src/main/resources` 의 `application.yml`/`.yaml`/`.properties` 에서
   `spring.jackson.property-naming-strategy` 값을 찾는다.
   **레포 루트에 `src/` 가 있다고 가정하지 않는다** — 모노레포·멀티모듈이면 루트에 없고
   `apps/<모듈>/src/main/resources` 처럼 모듈 아래에 있다. 하드코딩하면 아무것도 못 찾고
   3번 폴백으로 떨어져 실제와 다른 전략을 쓰게 된다:
   ```bash
   find "$ROOT" -type d -path '*/src/main/resources' \
     -not -path '*/build/*' -not -path '*/out/*' -print0 \
   | xargs -0 grep -RInE 'property-naming-strategy|propertyNamingStrategy' \
       --include='*.yml' --include='*.yaml' --include='*.properties' 2>/dev/null
   ```
2. 없으면 Java/Kotlin config(`ObjectMapper` 빈, `@JsonNaming` 등)에서 확인:
   ```bash
   find "$ROOT" -type d -path '*/src/main' -not -path '*/build/*' -print0 \
   | xargs -0 grep -RInE 'PropertyNamingStrategies\.|setPropertyNamingStrategy|@JsonNaming' \
       --include='*.kt' --include='*.java' 2>/dev/null
   ```
   `src/test` 는 제외한다 — 테스트가 프로덕션과 다른 전략을 쓰는 경우가 흔해 오탐이 난다.
3. 모두 없으면 Spring Boot 기본값 **`LOWER_CAMEL_CASE`**(camelCase)로 간주한다.
4. `SNAKE_CASE`/`LOWER_CAMEL_CASE` 이외의 값이면 AskUserQuestion으로 적용 규칙을 확인한다.
5. **주석 줄은 세지 않는다.** `# spring.jackson.property-naming-strategy=SNAKE_CASE (제거됨)`
   처럼 비활성화된 줄이 그대로 남아 있는 경우가 있다. 매치된 줄이 `#`/`//` 로 시작하면
   그 모듈은 미설정으로 본다.
6. **모듈마다 값이 다를 수 있다.** 실제로 한 모듈은 `SNAKE_CASE`, 다른 모듈은 미설정
   (=camelCase)인 레포가 있다. 서로 다른 값이 2개 이상 나오면 임의로 고르지 말고, 대상
   request 의 컨트롤러가 속한 모듈의 값을 쓴다. 컨트롤러 모듈을 특정할 수 없으면
   AskUserQuestion 으로 확인한다.
7. **감지 결과를 한 줄 보고하고 진행한다.** 조용히 정하면 틀려도 아무도 모른다 — 필드명이
   전부 어긋나는데 에러가 없어 발견이 가장 늦는 항목이다. 아래 형식으로 출력한다:

   > 네이밍 전략: `apps/checkout` → **SNAKE_CASE** (`application.properties:44`)
   > 미검출 시: `apps/api/api` → **LOWER_CAMEL_CASE** (설정 없음, Spring 기본값)

   근거 파일·라인을 함께 낸다. 값만 찍으면 사용자가 맞는지 판단할 수 없다.

이후 example의 **모든 JSON 필드명(request body, response body)**은 감지된 전략에 맞춰 생성한다:
- `SNAKE_CASE` → `snake_case`
- `LOWER_CAMEL_CASE` → `camelCase`

### 1단계: 대상 request 식별

- 대상 컬렉션을 결정한다:
  - 컬렉션 이름 또는 ID가 직접 제공된 경우: 그대로 사용한다
  - 미제공 시: Read 도구로 `.claude/plugins.json`의 `postman-tools.collectionUid`를 기본 컬렉션으로 사용한다
  - 둘 다 없으면 Postman REST API로 탐색하여 사용자에게 선택지를 제시한다:
    ```bash
    # 워크스페이스 목록
    curl -s "https://api.getpostman.com/workspaces" -H "X-Api-Key: ${apiKey}"
    # 컬렉션 목록
    curl -s "https://api.getpostman.com/collections?workspace={workspaceId}" -H "X-Api-Key: ${apiKey}"
    # 컬렉션 상세
    curl -s "https://api.getpostman.com/collections/{owner-uuid}" -H "X-Api-Key: ${apiKey}"
    ```
- 사용자에게 **request 이름(또는 API 경로)**를 확인받는다
- request ID를 확보한 뒤 다음 단계로 진행한다

### 1-1. Worktree 생성 (`--source` 지정 시)

`--source`가 지정된 경우, 격리된 worktree를 생성하여 해당 브랜치 코드 기준으로 분석한다.
미지정 시 현재 디렉토리에서 분석한다.

```bash
# 스테일 worktree 자기 치유 (이전 실행이 중단돼 남아 있으면 제거)
git worktree remove --force /tmp/wt-postman-example 2>/dev/null; git worktree prune; rm -rf /tmp/wt-postman-example
git worktree add --detach /tmp/wt-postman-example <source>
```

- 이후 모든 코드 읽기(Controller, DTO 등)는 worktree 경로(`/tmp/wt-postman-example`)에서 수행한다
- Postman API 호출은 경로와 무관하므로 그대로 수행한다
- 작업 완료 후 worktree를 정리한다:
  ```bash
  git worktree remove /tmp/wt-postman-example
  ```

### 2단계: 코드 기반 분석 (필수)

example은 반드시 실제 코드를 분석한 결과를 기반으로 작성한다. 추측이나 Postman description만으로 만들지 않는다.

1. **Controller** — 해당 API의 HTTP method, 경로, Request/Response 타입 확인
2. **Request DTO** — 필드 구조, 타입, 검증 규칙(`@field:NotBlank` 등), 기본값, nested 구조 파악
3. **Response DTO** — 필드 구조, 타입, nullable 여부, `companion object`의 팩토리 메서드(`of`/`from`) 확인
4. **Service** — 비즈니스 로직에서 발생하는 에러 케이스, 조건 분기 파악
5. **ErrorCode** — 관련 에러 코드의 `status`, `message` 확인

코드에서 확인한 필드명·타입·구조가 example의 **유일한 진실 소스(source of truth)**이다.

### 3단계: example 생성

Postman REST API 전용 엔드포인트 `POST /collections/{collectionId}/responses?request={requestId}`를 사용한다.

#### 핵심 규칙 (이것을 지키지 않으면 method/url이 누락됨)

1. Collection Format v2.1.0 스키마를 따라 body를 구성한다
2. **`originalRequest` 필드에 원본 요청 정보를 JSON 객체로 전달**한다
3. `originalRequest.url`은 반드시 **문자열**이어야 한다 (객체로 전달하면 `[object Object]`로 표시됨)

#### body 구조

```json
{
  "name": "v20260409 200 OK - 설명",
  "status": "OK",
  "code": 200,
  "header": [{"key": "Content-Type", "value": "application/json"}],
  "body": "<response body JSON 문자열>",
  "originalRequest": {
    "method": "POST",
    "header": [],
    "body": {
      "mode": "raw",
      "raw": "<request body JSON 문자열>",
      "options": {"raw": {"language": "json"}}
    },
    "url": "{{API-HOST}}/api/v3/some-endpoint"
  }
}
```

#### 전체 호출 예시

```bash
curl -X POST \
  "https://api.getpostman.com/collections/{collectionId}/responses?request={requestId}" \
  -H "X-Api-Key: ${apiKey}" \
  -H "Content-Type: application/json" \
  -d @example-body.json
```

python3으로 body JSON을 구성한 뒤 curl로 POST하는 패턴을 권장한다 (`postman-request`와 동일한 방식).

### 4단계: example 설계 — 코드 분석 결과를 바탕으로 유용한 케이스를 도출한다

1개만 만들지 않는다. 코드에서 파악한 분기·필터·에러를 기반으로 **실제 사용 시나리오를 커버하는 다수의 example**을 생성한다.

#### 이름 규칙

example 이름에는 **날짜 접두사 `vYYYYMMDD`**를 붙인다. 시스템 컨텍스트의 `currentDate`에서 날짜를 가져와 하이픈을 제거한 형식을 사용한다.

- 형식: `v{YYYYMMDD} {HTTP_STATUS} {STATUS_NAME} - {설명}`
- 예시: `v20260409 200 OK - 정상 응답`, `v20260409 400 Bad Request - 필수값 누락`

#### 기본 example (항상 포함)

| 이름 | 코드 | 설명 |
|------|------|------|
| v{YYYYMMDD} 200 OK - 정상 응답 | 200 | 주요 필드가 모두 채워진 대표 응답 |
| v{YYYYMMDD} 200 OK - 빈 목록 | 200 | 결과 0건 (페이징 API인 경우) |

#### 코드 분석으로 도출하는 추가 example

- **enum/필터 분기**: Request DTO에 enum 필터(OS, 상태, 유형 등)가 있으면 → 주요 enum 값별 example (예: WINDOWS용, MACOS용)
- **nullable 필드 차이**: Response에 nullable 필드가 있으면 → null인 케이스와 non-null인 케이스를 별도 example로 분배
- **비즈니스 에러**: Service에서 throw하는 에러 → 해당 에러 코드별 example (400, 404 등)
- **검증 에러**: Request DTO의 validation 규칙 위반 시 → 400 Bad Request example
- **빈 body / 최소 요청**: `required = false`이거나 기본값이 있으면 → 빈 body `{}`로 요청하는 example
- **페이징/정렬**: 정렬 조건이 다른 경우 → query parameter 차이를 보여주는 example

## 병렬 처리 (대량 request)

대상 request가 다수(10개 이상)인 경우, subagent를 활용하여 병렬로 처리한다.

### 그룹핑 전략

1. 컬렉션에서 대상 request 목록을 확보한다
2. **비슷한 request끼리 그룹**으로 묶는다:
   - 같은 도메인/리소스 (예: SW 자산 관련 API 묶음, 반출 IP 관련 API 묶음)
   - 같은 Controller 클래스를 공유하는 request
   - 같은 Request/Response DTO를 공유하는 request
3. 그룹당 1개의 subagent(`oh-my-claudecode:executor`)를 생성하여 병렬 실행한다

### subagent 프롬프트 구성

각 subagent에게 전달할 정보:
- 담당 request 목록 (이름, ID, URL)
- 컬렉션 ID
- 이 SKILL.md의 **2단계(코드 분석)**, **3단계(example 생성)**, **4단계(example 설계)** 규칙 전체
- `originalRequest` 사용 규칙 (핵심 — 이것을 빠뜨리면 method/url 누락)

### 실행 예시

```
request 30개 → 도메인별 5그룹 → subagent 5개 병렬 실행
- Agent 1: SW 자산 관련 6개
- Agent 2: HW 자산 관련 5개
- Agent 3: 반출 IP 관련 7개
- Agent 4: 보안 활동 관련 6개
- Agent 5: 공통 설정 관련 6개
```

## 주의사항

- Request/Response body의 JSON 필드명은 **0단계에서 감지한 Jackson 네이밍 전략**에 맞춰 생성한다 (`SNAKE_CASE` → `snake_case`, `LOWER_CAMEL_CASE` → `camelCase`)
- 페이징 응답은 `CustomPagedModelResponse` 형식: `{"_embedded": {"items": [...]}, "page": {"size": 20, "total_elements": N, "total_pages": N, "number": 0}}` (SNAKE_CASE 프로젝트 기준 — camelCase 프로젝트면 `totalElements`, `totalPages`로 변환)
- example 삭제는 단일 API로 불가 — 사용자에게 Postman 앱에서 직접 삭제 요청 (또는 컬렉션 전체 PUT으로 가능하나 무거움)
- `apiKey`는 컬렉션 owner와 동일한 계정의 API Key여야 함 (owner 불일치 시 403)

## plugins.json 설정 권고 (작업 후)
이번 실행에서 AskUserQuestion 으로 받은 값이 있었다면, 작업 완료 후
[../../reference/config-recommendation.md](../../reference/config-recommendation.md) 의 출력 포맷대로
안내 블록을 출력한다. 모든 값을 plugins.json 에서 얻었으면 생략한다.

**권고 대상:**
- **포함**: AskUserQuestion 으로 받은 값 (다음부터 자동 처리되려면 plugins.json 에 저장 필요). 예: `workspaceId`, `workspaceName`, `apiKey`, `collectionUid`
- **제외**: CLI 인자로 받은 값(request 이름/컬렉션), AI 가 자동 판단한 값 (네이밍 전략, 생성된 example body)

