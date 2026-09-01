---
name: postman-request
description: Postman 컬렉션의 request를 생성하거나 수정한다. URL, params, body 설정과 documentation(description)을 코드 기반으로 구성하고 Postman API로 반영한다.
when_to_use: 사용자가 "postman request 생성", "포스트맨 요청 만들어", "request 수정해줘", "컬렉션에 요청 추가/수정" 등 Postman request의 생성·수정을 요청할 때 사용한다.
argument-hint: "<postman-url|collection> [--source <branch>] [--request <request-name>]"
allowed-tools: Bash(curl *), Bash(git *), Bash(python3 *), Bash(grep *), Read, Grep, Glob, Edit, AskUserQuestion
---

# Postman Request Skill

Postman 컬렉션의 **request**를 생성하거나 수정한다. URL, query params, body, documentation(description)을 실제 코드 기반으로 구성하고 Postman API로 반영한다.

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
    "apiKey": "PMAK-...",                    // Postman 플랫폼 API 호출용 키
    // 선택
    "backendStack": "Kotlin Spring Boot",    // 백엔드 기술 스택
    "services": {                            // 서비스 구분 (Base URL 변수 매핑)
      "api": "{{API-HOST}}",
      "checkout": "{{CHECKOUT-HOST}}"
    },
    "collections": {                         // 별칭 → 컬렉션 UID (owner-uuid, 선택)
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

docs(description)는 **공유 템플릿** [`../../templates/docs-template.md`](../../templates/docs-template.md) 의 빈 스켈레톤을 그대로 복사하여 채운다. 섹션 순서, 표 컬럼명, 타입·enum·nullable 표기 규칙은 템플릿을 따르며 자유 양식 금지.

- 첫 줄에 `> Last modified: YYYY-MM-DD` 를 삽입한다 (신규: 현재 날짜, 기존 수정: 갱신)
- 사용하지 않는 섹션은 통째로 삭제하지 말고 본문을 비우거나 "해당 없음"으로 명시한다
- 단, 페이징 보조 섹션(`Pageable 표준` / `Cursor 페이징` / `페이지 응답 래퍼 — *`)은 사용 안 하는 종류를 통째 삭제한다 (둘 중 하나만 남긴다)

---

## 네이밍 규칙

Jackson 네이밍 전략 감지 절차와 전략별 규칙표는 플러그인 공유 문서를 따른다:
[../../reference/naming-strategy.md](../../reference/naming-strategy.md)

이하 워크플로우에서 "JSON body 필드명"이라 하면 감지된 전략의 규칙을 의미한다.

---

## Worktree (`--source` 지정 시)

`--source`가 지정된 경우, 격리된 worktree를 생성하여 해당 브랜치 코드 기준으로 분석한다.
미지정 시 현재 디렉토리에서 분석한다.

```bash
# 스테일 worktree 자기 치유 (이전 실행이 중단돼 남아 있으면 제거)
git worktree remove --force /tmp/wt-postman-request 2>/dev/null; git worktree prune; rm -rf /tmp/wt-postman-request
git worktree add --detach /tmp/wt-postman-request <source>
```

- 이후 모든 코드 읽기(Controller, DTO 등)는 worktree 경로(`/tmp/wt-postman-request`)에서 수행한다
- Postman API 호출(수집, 반영)은 경로와 무관하므로 그대로 수행한다
- 작업 완료 후 worktree를 정리한다:
  ```bash
  git worktree remove /tmp/wt-postman-request
  ```

---

## 워크플로우

### 생성 모드 (Create)

신규 endpoint에 대한 Postman request를 생성한다.

#### 1단계: 코드 분석

1. Controller 메서드에서 HTTP method, URL 패턴, Request/Response DTO 식별
2. **모든 DTO 파일을 반드시 읽는다** (누락 방지)
3. 필드 구조, 타입, 검증 규칙, nullable 여부, nested 구조 파악

#### 2단계: request 구성

1. **URL**: base URL 변수 + path (services 설정 참조)
2. **Query Params**: DTO 필드를 camelCase로
3. **Request Body**: DTO 필드를 감지된 Jackson 전략에 맞춰 변환 (SNAKE_CASE → `snake_case`, LOWER_CAMEL_CASE → `camelCase`)
4. **Path Variables**: Controller의 @PathVariable과 대응

#### 3단계: Documentation 작성

[`../../templates/docs-template.md`](../../templates/docs-template.md) 의 **빈 스켈레톤**을 복사하여 채운다. 섹션 순서·표 컬럼명·타입 표기는 모두 템플릿을 따르며 별도 양식을 만들지 않는다.

채워야 할 섹션 (템플릿과 동일 순서):

1. `> Last modified: YYYY-MM-DD` + 한 줄 요약 + 컨트롤러 어노테이션 (예: `` (`@PostMapping("/foo")`) ``)
2. **Path Variables**
3. **Query Parameters** — Pageable/Cursor 보조 섹션은 해당하는 한 종만 남김
4. **Request Body — `<DtoClassName>`** — body 없으면 "해당 없음 (body 없음)"
5. **Response — `<DtoClassName>`** + 재사용 sub-DTO 섹션(`#### <DtoClassName>`) + 페이지 응답 래퍼(해당 시)
6. **Status Codes**
7. **권한**

#### 4단계: 반영

1. 생성할 request 내용을 사용자에게 보여주고 승인 받는다
2. 수정된 내용을 컬렉션 JSON에 적용 (python3 + json 모듈)
3. Postman API로 PUT하여 반영한다
4. 반영 후 재검증 (GET → 변경 항목 확인)

### 수정 모드 (Update)

기존 Postman request의 설정과 docs를 수정한다.

#### 1단계: 현재 상태 확인

1. 컬렉션에서 대상 request 가져오기
2. 현재 URL, params, body, docs 확인

#### 2단계: 코드 대조

1. Controller/DTO와 비교하여 수정 필요 항목 파악
2. 네이밍 규칙 위반 여부 확인

#### 3단계: 수정 적용

1. 수정 내용을 사용자에게 보여주고 승인 받는다
2. 수정된 내용을 컬렉션 JSON에 적용 (python3 + json 모듈)
3. Postman API로 PUT하여 반영한다
4. 반영 후 재검증 (GET → 변경 항목 확인)

---

## Postman API 참고

| 작업 | 엔드포인트 | 비고 |
|------|-----------|------|
| 컬렉션 읽기 | `GET /collections/{owner}-{uuid}` | UID 형식 필수 (owner-uuid) |
| 컬렉션 교체 | `PUT /collections/{owner}-{uuid}` | body: `{"collection": {...}}` |
| 인증 | `X-Api-Key` 헤더 | `plugins.json`의 `apiKey` 값 사용 |

**주의**: `updateCollectionRequest` API는 컬렉션 소유자만 사용 가능. 소유자가 다르면 `putCollection`(전체 교체)을 사용한다.

### 반영 절차

```bash
# 1. 컬렉션 전체를 JSON으로 가져오기
curl -s "https://api.getpostman.com/collections/{owner}-{uuid}" \
  -H "X-Api-Key: ${apiKey}" > collection.json

# 2. python3으로 JSON 수정 (description, body 등)

# 3. 수정된 컬렉션 PUT
curl -X PUT "https://api.getpostman.com/collections/{owner}-{uuid}" \
  -H "X-Api-Key: ${apiKey}" \
  -H "Content-Type: application/json" \
  -d @modified.json

# 4. 재검증 (GET으로 변경 확인)
```

---

## 주의사항

- 같은 인터페이스(SearchCriteria, FilterCriteria)를 구현하는 DTO가 여러 개일 때, **모두 개별 검증**한다
- Jackson 전략이 `SNAKE_CASE`인 프로젝트에서는 Response Body가 `snake_case`이므로, 해당 필드명이 Query Param 영역에 있으면 오류로 판단한다 (Query는 언제나 camelCase)
- request 삭제는 MCP 도구로 불가 — 사용자에게 Postman 앱에서 직접 삭제 요청
- `postman-local` MCP만 컬렉션 수정 가능 (`postman-team` API 키는 owner 불일치로 403)

## plugins.json 설정 권고 (작업 후)
이번 실행에서 AskUserQuestion 으로 받은 값이 있었다면, 작업 완료 후
[../../reference/config-recommendation.md](../../reference/config-recommendation.md) 의 출력 포맷대로
안내 블록을 출력한다. 모든 값을 plugins.json 에서 얻었으면 생략한다.

**권고 대상:**
- **포함**: AskUserQuestion 으로 받은 값 (다음부터 자동 처리되려면 plugins.json 에 저장 필요). 예: `workspaceId`, `workspaceName`, `apiKey`, `services`, `collections`
- **제외**: CLI 인자로 받은 값(`--source`, `--request`, Postman URL), AI 가 자동 판단한 값 (네이밍 전략, URL/params/body 구성, docs 본문)

