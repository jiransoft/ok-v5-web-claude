---
name: release-note
description: 두 git 태그 사이의 변경사항을 분석하여 FE팀 공유용 릴리즈 노트를 작성하고 GitHub Release에 등록합니다
when_to_use: 사용자가 "릴리즈 노트 만들어줘", "이번 배포 변경사항 정리해줘", "FE팀 공유용 API 변경 노트 작성해줘", "태그 간 변경사항 릴리즈로 등록해줘", "release note 생성", "changelog 만들어줘" 등 두 태그 사이의 변경을 정리해 릴리즈 노트를 작성·등록하려 할 때.
allowed-tools: Bash(git *), Bash(gh *), Read, Grep, Glob, Agent, AskUserQuestion
argument-hint: "<source-tag> [--base <base-tag> | --no-base] [--dry-run]"
---

# Release Note Skill

두 git 태그 사이의 변경사항을 분석하여 **FE팀 공유용 API 변경사항 릴리즈 노트**를 작성하고, GitHub Release에 등록한다. 외부 연동은 `gh` CLI 만 쓴다 (MCP 불필요).

## --help 처리

`$ARGUMENTS`가 `--help` 또는 `-h` 면 [reference/usage.md](reference/usage.md) 의 사용법 블록을 그대로 출력하고 즉시 종료한다.

## 절차

### 1. 인자 파싱 및 설정 로드

`$ARGUMENTS`에서 다음을 파싱한다:

- `<source-tag>`: 릴리즈 대상 태그 (필수, 없으면 AskUserQuestion)
- `--base <tag>`: 이전 태그 (선택). `--no-base`와 상호 배타
- `--no-base`: 이전 태그 비교 없이 **스냅샷 모드**로 동작 (선택). `--base`와 상호 배타. 두 플래그가 함께 주어지면 에러로 즉시 종료한다
- `--dry-run`: 미리보기 모드 (선택)

> **스냅샷 모드란?** source-tag 시점의 전체 API 목록을 열거하는 모드. 두 태그 사이 diff 분석 대신 source-tag의 모든 Controller를 훑어 API 스냅샷을 만든다. 첫 릴리즈, 태그 네이밍 변경 후 리셋, 독립 스냅샷 발행 등의 용도에 쓴다.

#### 설정 로드 (`.claude/plugins.json`)

⚠️ **반드시 `.claude/plugins.json`을 Read 도구로 먼저 읽어야 한다. 이 단계를 건너뛰면 안 된다.**

> 📍 경로는 **본체 레포 루트의 `.claude/plugins.json`** 이다. worktree 경로를 대상으로
> 작업 중이어도 설정은 본체에서 읽는다 — `plugins.json` 은 gitignore 대상이라 worktree 에
> 체크아웃되지 않는다. worktree 에서 찾다 실패하면 설정이 있는데도 CLAUDE.md·질문으로
> 조용히 폴백한다.

설정 우선순위: (1) Read 도구로 `.claude/plugins.json`의 `release-tools` 섹션 → (2) 같은 파일의 `git-workflow` 섹션의 `swaggerBaseUrl`·`modules` — release-note 가 git-workflow 소속이던 시절(≤0.1.0, GitLab 기반) 설정 호환용 폴백. `project` 는 GitLab 경로라 폴백하지 않는다 → (3) 프로젝트의 `CLAUDE.md` → (4) AskUserQuestion.
시스템 컨텍스트에 이미 로드된 값을 사용하지 말고, 반드시 Read 도구로 파일을 직접 읽어서 설정을 가져온다.

```jsonc
{
  "release-tools": {
    // GitHub 레포 경로(owner/repo) — gh 호출 시 -R 플래그로 사용 (선택)
    "project": "owner/repo",
    // Swagger UI base URL — 릴리즈 노트에 API 링크 자동 생성에 사용
    "swaggerBaseUrl": "https://testing-api.officekeeper.dev/swagger-ui/index.html",
    // 모듈 분류 — 파일 경로 prefix를 모듈명으로 매핑. 릴리즈 노트를 모듈별로 그루핑할 때 사용
    // prefix는 앞에서부터 매칭하며, 더 긴 prefix가 우선한다 (예: "apps/api-v3/"가 "apps/"보다 먼저 매칭)
    "modules": {
      "apps/api/": "API",
      "apps/admin/": "Admin",
      "apps/v3-api/": "V3 API"
    }
  }
}
```

- `project`: GitHub 레포 경로(`owner/repo`). 모든 `gh` 호출에 `-R <project>` 로 넘긴다. 미설정이면 `-R` 없이 실행한다 — `gh` 가 현재 디렉토리의 git remote 에서 레포를 알아낸다 (remote 가 여럿이거나 fork 에서 작업할 때만 명시 필요)
- `swaggerBaseUrl`: 설정되어 있으면 모든 API 엔드포인트에 Swagger 링크를 자동 포함한다. 미설정이면 Swagger 링크 없이 생성한다 (링크 컬럼/섹션 생략)
- `modules`: 파일 경로 prefix → 모듈명 매핑. 릴리즈 노트를 모듈별로 그루핑한다. 4-1단계 "모듈 판별" 참고. 미설정이거나 매핑되지 않는 prefix가 있으면 AskUserQuestion으로 확인한다

### 2. 이전 태그 결정

분기 순서:

1. **`--no-base` 지정**: 이전 태그 탐색을 생략하고 **스냅샷 모드**로 진입. 이후 3·5·7단계는 각 섹션의 "스냅샷 모드" 분기를 따른다
2. **`--base <tag>` 지정**: 그대로 사용. 단 `git rev-parse --verify <tag>`로 태그 존재 검증. 실패 시 에러로 종료
3. **둘 다 미지정**: 자동 감지
   ```bash
   git tag --sort=-version:refname | head -20
   ```
   태그 목록에서 `<source-tag>` 바로 이전 태그를 선택. 감지 실패 시 AskUserQuestion으로 후보 태그 목록을 보여주고 사용자에게 "이전 태그 선택 / `--no-base`로 진행 / 취소" 중 선택받는다

**결과 안내:**
```
릴리즈: <source-tag>
이전 태그: <base-tag>               ← 기본 모드
(또는)
모드: 스냅샷 (이전 태그 비교 없음)         ← --no-base 모드
```

### 3. 변경사항 수집

#### 기본 모드 (이전 태그 있음)

다음을 **병렬로** 실행한다:

**3-1. 커밋 목록 조회**

```bash
git log <base-tag>..<source-tag> --first-parent --format='%H%x09%s%n%b%n---'
```

(Bash) 로 두 태그 사이의 커밋을 조회한다. 이슈 키 추출(8단계)에 사용한다. tag range 로 커밋 범위를 확실히 고정한다.

**3-2. Diff 조회**

git 으로 두 태그 사이의 변경 파일 목록을 조회한다:

```bash
git diff <base-tag>..<source-tag> --name-status -- . \
  ':(exclude)apps/site/**' ':(exclude)apps/daemon/**' \
  ':(exclude)**/*.lock' ':(exclude)**/package-lock.json' \
  ':(exclude)**/yarn.lock' ':(exclude)**/*.gradle'
```

> FE 공유용이므로 프론트엔드(site), 데몬, 락파일·빌드스크립트 변경은 제외한다.

diff **본문**은 전체를 한 번에 받지 않는다 — 대형 릴리즈에서 컨텍스트가 넘친다. 4단계에서 파일을 분류한 뒤, 분석이 필요한 카테고리의 파일만 조회한다:

```bash
git diff <base-tag>..<source-tag> -- <파일경로...>
```

#### 스냅샷 모드 (`--no-base`)

diff/커밋 수집 대신 **source-tag의 Controller 파일 전체 목록**을 조회한다:

```bash
git ls-tree -r <source-tag> --name-only \
  | grep -E '.*Controller.*\.kt$' \
  | grep -vE '(Test|Spec|^apps/site/|^apps/daemon/)'
```

이 목록이 이후 5단계 스냅샷 분석의 대상이 된다. 커밋 목록은 조회하지 않는다 (8단계 이슈 키 추출은 스냅샷 모드에서 생략).

### 4. 변경 파일 분류

diff 결과에서 파일을 추출하고, 다음 카테고리로 분류한다:

| 카테고리 | 대상 | 분석 우선순위 |
|----------|------|-------------|
| Controller | `*Controller*.kt` (test 제외) | **최우선** — 시그니처가 전체 분석의 기준점 |
| Controller 시그니처 그래프 타입 | Controller 메서드의 반환/`@RequestBody`/객체 바인딩 파라미터 타입, 그리고 그 필드로 도달 가능한 타입(1~2단계 확장) | **높음** — FE에 노출되는 JSON 스키마 |
| Migration | `*.sql` | **중간** — DB 스키마 변경 |
| Service | `*Service*.kt` (test 제외) | 낮음 — 내부 로직 (FE 무관, 참고용) |
| Test | `*Test*.kt`, `*Spec*.kt` | 제외 — FE 공유에 불필요 |

> **파일명 패턴은 힌트일 뿐 판단 기준이 아니다.** `*Response*`/`*Dto*`/`*Request*`/`*Filter*` 등은 그래프 탐색 시 읽기 우선순위를 정하는 데만 쓰고, 최종 포함 여부는 "Controller 시그니처에서 도달 가능한가"로 결정한다. `*View`, `*Projection`, `*Result`, `*Summary` 또는 도메인 이름 그대로 쓰는 타입도 그래프에 포함되면 분석 대상이다.

#### 4-1. 모듈 판별

5단계 분석 결과를 모듈별로 그루핑하기 위해, **각 Controller 파일**(스냅샷 모드는 3단계의 전체 Controller, 기본 모드는 diff에 포함된 Controller)을 모듈명으로 매핑한다.

**판별 절차:**

1. **plugins.json `modules` 설정 확인** — `release-tools.modules`(prefix → 모듈명 객체)을 로드한다
2. **prefix 매칭** — 각 Controller 파일 경로에 대해, `modules`의 키들과 startsWith 매칭한다. **더 긴 prefix가 우선한다** (예: 파일이 `apps/api-v3/...`이고 매핑에 `apps/`와 `apps/api-v3/`가 모두 있으면 `apps/api-v3/` 선택)
3. **매핑 실패 시 처리** — 다음 두 경우 모두 AskUserQuestion으로 사용자에게 매핑을 요청한다:
   - `modules` 설정 자체가 없는 경우: 모든 Controller 파일의 상위 디렉토리 후보(예: `apps/api/`, `apps/admin/` 등)를 자동 추출하여 사용자에게 각각에 모듈명을 지정받는다
   - 일부 파일이 어느 prefix에도 매칭되지 않는 경우: 해당 파일들의 후보 prefix를 추출하여 사용자에게 매핑을 받는다
4. **사용자 입력 결과**는 메모리에 보관하여 이번 실행 내에서 일관되게 사용하고, 11단계 "plugins.json 설정 권고"에 포함시켜 다음 실행부터 자동 처리되도록 안내한다
5. **DTO/타입 그래프 파일** — Controller 시그니처 그래프에서 가져온 타입 파일은, 해당 타입을 사용하는 Controller의 모듈로 분류한다. 여러 모듈의 Controller가 공유하는 타입은 첫 등장 Controller의 모듈에 배치하되 본문에 "여러 모듈 공유"를 명시한다
6. **Migration/Service 등 비-Controller 파일** — 모듈 그루핑 대상이 아니므로 본 단계에서는 무시한다 (현재 릴리즈 노트 본문에 포함되지 않는 카테고리)

> **참고**: 4-1단계는 파일을 분류만 한다. 실제 모듈별 분석/렌더링은 5·7단계에서 수행한다.

### 소스 파일 접근 규칙

5단계 이후로 **파일 전체 내용**이 필요할 때는 작업 디렉토리(HEAD)가 아니라 **source-tag 커밋 시점 스냅샷**을 읽어야 한다. 그렇지 않으면 source-tag 이후의 변경이 릴리즈 노트에 혼입된다.

| 금지 | 대신 사용 | 용도 |
|------|----------|------|
| `Read <path>` | `git show <source-tag>:<path>` (Bash) | 특정 파일 전체를 source-tag 시점으로 읽기 |
| `Grep <pattern>` | `git grep <pattern> <source-tag> -- '<glob>'` (Bash) | 소스 전역 검색을 source-tag 시점으로 수행 |

아래 단계에서 "파일을 읽는다"/"검색한다"는 모두 이 규칙을 따른다. `Read`/`Grep` 도구를 그대로 호출하면 안 된다. (예외: diff 결과 자체는 이미 `git diff <base-tag>..<source-tag>`로 구간 제한되어 있으므로 diff 텍스트 처리에는 규칙이 적용되지 않는다.)

### 5. API 변경사항 분석

> **모드 분기**: 기본 모드는 아래 5-1 ~ 5-3 (diff 기반). 스냅샷 모드(`--no-base`)는 5-Snapshot 만 수행하고 5-1 ~ 5-3은 스킵한다.
>
> **공통**: 분석 결과의 각 항목(API/Breaking/필드변경/Deprecated)에는 4-1단계에서 결정한 **모듈명을 태깅**한다. 7단계 렌더링에서 모듈별로 그루핑하는 데 사용된다.

#### 기본 모드 (diff 기반)

**Controller diff를 최우선으로 분석한다.** diff에서 다음을 추출:

#### 5-1. 새로운 API
- 새 메서드 (`+fun`) 또는 새 파일의 엔드포인트
- HTTP Method, Path, 설명(`@Operation(summary)`)
- 메서드명 (Swagger 링크용)

> **경로 조합 규칙**: API 경로는 반드시 클래스의 `@RequestMapping` + 메서드의 `@GetMapping`/`@PostMapping` 등을 **조합**하여 전체 경로를 생성한다.
> 예: `@RequestMapping("/api/v3/pc-usages")` + `@PostMapping("/search")` → `POST /api/v3/pc-usages/search`
> diff만으로 전체 경로를 알 수 없는 경우, `git show <source-tag>:<path>`(Bash)로 소스 파일을 직접 확인한다.

#### 5-2. Breaking Changes
다음 패턴을 감지한다:

| 패턴 | 분류 |
|------|------|
| `@GetMapping` → `@PostMapping` (또는 반대) | HTTP Method 변경 |
| 파라미터 타입 변경 (Request body 클래스명 변경) | Request Body 구조 변경 |
| 반환 타입 변경 (`Page` → `PagedModel`, 커스텀 → 표준 등) | Response 구조 변경 |
| `@RequestParam` → `@RequestBody` (또는 반대) | 파라미터 전달 방식 변경 |
| `@Deprecated` 어노테이션 추가 | Deprecated |

#### 5-3. 요청/응답 필드 변경

**목적:** FE가 타입 선언과 파싱 로직을 고쳐야 할 JSON 스키마 변경만 기록한다.

**대상 타입 집합 구성 (top-down):**

1. diff에 변경이 있는 Controller 파일을 `git show <source-tag>:<path>`(Bash)로 읽어 **모든 메서드의 시그니처**를 스캔한다. 메서드 본문이 안 바뀌어도 타입 내부가 바뀌면 JSON이 바뀌므로 변경 메서드에 한정하지 않고 전체 시그니처를 본다
2. 각 메서드에서 JSON 경계 타입을 추출한다
   - 반환 타입 (`ResponseEntity<T>`, `Page<T>`, `Slice<T>`, `Flow<T>`, `List<T>` 등은 언래핑하여 `T`)
   - `@RequestBody` 파라미터 타입
   - `@ModelAttribute` / 객체 바인딩 `@RequestParam`의 타입
3. 추출한 각 타입의 소스를 `git show <source-tag>:<path>`(Bash)로 읽어 **필드 타입을 1~2 단계 확장**한다 (중첩 data class, sealed class 하위 타입, enum 포함). 타입이 속한 파일 경로를 모르면 `git grep -l '<ClassName>' <source-tag> -- '*.kt'`(Bash)로 찾는다
4. 이 "Controller 타입 그래프"에 속한 파일의 diff만 분석 대상으로 삼는다. 파일명이 `*Response*`/`*Dto*`여도 그래프에 없으면 제외한다

**감지 대상:**
- 필드 추가 (`+val`) / 삭제 (`-val`)
- 필드 타입 변경 (`String?` → `String`, `Long` → `String` 등 — nullable 변경 포함)
- 제네릭 파라미터 변경 (`List<Old>` → `List<New>`)
- enum 상수 추가/삭제
- `@JsonProperty` / `@field:JsonProperty`의 직렬화 이름 변경
- 요청 구조 공통 패턴 변경 (예: `SearchRequest` 패턴 통일, `startTime`/`endTime` → `dateTimeRange`, enum → boolean 필터 방식 변경). 여러 Controller에 공통 적용되면 개별 나열 대신 패턴 설명 + 대상 API 테이블로 정리한다

**제외:**
- `@JsonIgnore` 필드 / private val / companion object — 직렬화 안 됨
- 메서드 본문 변경 (시그니처 불변)
- Controller 그래프에 없는 DTO (내부 Service 전달용, DB 매핑 전용 등)

#### 스냅샷 모드 (`--no-base`)

3단계에서 수집한 **source-tag의 모든 Controller 파일**을 대상으로 전체 API 목록을 열거한다. Controller가 10개 이상이면 Agent(general-purpose)에 위임해 병렬 처리한다.

각 Controller에서:

1. `git show <source-tag>:<path>`(Bash)로 파일을 읽는다
2. 클래스 `@RequestMapping` + 각 메서드의 `@GetMapping`/`@PostMapping` 등을 조합하여 전체 경로를 만든다
3. 각 메서드마다 다음을 추출:
   - **HTTP Method**, **Path**
   - **설명**: `@Operation(summary = "...")` → 없으면 KDoc 첫 줄 → 없으면 메서드 이름
   - **Swagger 태그명**: 6단계 규칙 적용 (메서드 레벨 > 클래스 레벨 > 패턴 A/B)
   - **operationId**: 6단계 URL 조합 규칙
   - **Deprecated 여부**: 메서드·클래스에 `@Deprecated` 또는 `@Operation(deprecated = true)`

4. 결과를 **Swagger 태그별로 그루핑**하여 정렬한다 (동일 태그 내에서는 Path 사전순)

기본 모드의 "새로운 API", "Breaking Changes", "요청/응답 필드 변경" 섹션은 스냅샷 모드에서 생성하지 않는다. 대신 "전체 API 목록"과 "Deprecated" 섹션만 만든다.

### 6. Swagger 링크 생성 (`swaggerBaseUrl` 설정 시)

변경된 Controller의 Swagger 태그명을 추출하여 `<swaggerBaseUrl>#/<URL-encoded-tag-name>/<methodName>` 형태의 딥링크를 생성한다. `swaggerBaseUrl` 미설정 시 이 단계를 건너뛴다.

> 태그명 추출(패턴 A/B), 태그 우선순위 결정, URL 조합 규칙 등 상세는 [reference/swagger-links.md](reference/swagger-links.md) 참고.

### 7. 릴리즈 노트 작성

> **모드 분기**: 기본 모드는 아래 세 하위 템플릿(변경 없음/있음)을 사용. 스냅샷 모드(`--no-base`)는 "스냅샷 모드 템플릿"만 사용한다.
>
> **공통 — 모듈 최상위 구조**: 모든 본문 섹션은 `### <모듈명>` 을 최상위로 두고, 그 아래에 `#### 새로운 API` / `#### Breaking Changes` / `#### 응답 필드 변경` / `#### Deprecated` 를 배치한다. 모듈 내에서 해당 섹션의 항목이 없으면 그 섹션은 생략한다. 모듈 자체가 비어 있으면(어떤 섹션에도 항목 없음) 그 모듈도 생략한다. 모듈 순서는 plugins.json `modules` 선언 순서를 따르고, 누락된 모듈은 가나다순으로 뒤에 붙인다.

출력 형식(기본 모드 변경 없음/있음, 스냅샷 모드)은 [reference/output-template.md](reference/output-template.md)를 따른다.

### 8. 이슈 키 추출

**스냅샷 모드(`--no-base`)에서는 이 단계를 스킵한다** (커밋 구간이 없어 추출 기준이 없음).

기본 모드에서는 3-1 단계의 `git log <base-tag>..<source-tag>` 출력에서 Jira 이슈 키를 추출한다:

```
패턴: \b[A-Z]+-\d+\b (예: OKEP-4218, OKEP-4257)
```

중복 제거 후 릴리즈 노트 상단에 나열한다. 이 추출도 태그 구간 내 커밋만 대상으로 하므로 범위 이탈이 없다.

### 9. 미리보기 및 확인

생성된 릴리즈 노트를 사용자에게 보여준다.

- `--dry-run`: 미리보기만 출력하고 종료
- 그 외: "이 내용으로 GitHub Release를 생성할까요?" 확인 후 진행

### 10. GitHub Release 생성/업데이트

릴리즈 노트 본문을 임시 파일로 저장한 뒤(인라인 인자로 넘기면 셸 이스케이프가 깨진다), `gh release view`로 해당 태그의 릴리즈 존재 여부를 확인한다. `project` 설정이 있으면 모든 명령에 `-R <project>` 를 붙인다.

```bash
gh release view <source-tag>          # exit 0 → 이미 존재, exit 1 → 없음
```

- **릴리즈 없음**:
  ```bash
  gh release create <source-tag> --verify-tag --title <source-tag> --notes-file <임시파일>
  ```
  `--verify-tag`: 태그가 원격에 없으면 만들어버리지 않고 실패한다 — 릴리즈 노트는 이미 푸시된 태그에만 단다
- **릴리즈 있음**:
  ```bash
  gh release edit <source-tag> --notes-file <임시파일>
  ```

### 11. 결과 출력

```
GitHub Release 생성 완료
  https://github.com/<owner/repo>/releases/tag/<source-tag>
```

(`gh release create`/`edit` 가 출력한 URL을 그대로 쓴다)

## 작성 규칙

- **FE팀 관점**으로 작성한다 — DB 마이그레이션 상세, 내부 서비스 구조, 테스트 변경은 제외
- **한글**로 작성한다
- 해당 사항이 없는 섹션은 생략한다
- Breaking Changes는 **구체적인 Before/After**를 명시한다
- 공통 패턴 변경(검색 필터 리팩토링 등)은 개별 나열 대신 패턴 설명 + 대상 API 테이블로 정리
- 응답 필드 변경은 **추가/삭제/타입변경**을 명확히 구분한다
- Swagger 링크는 `plugins.json`의 `swaggerBaseUrl`이 설정되어 있을 때 자동 포함한다

## 출력 규칙

- 내부 분석 과정, 중간 메모를 노출하지 않는다
- 도구 호출의 raw 결과를 그대로 출력하지 않는다
- 최종 릴리즈 노트와 결과 URL만 출력한다

## plugins.json 설정 권고 (작업 후)
이번 실행에서 AskUserQuestion 으로 받은 값이 있었다면, 작업 완료 후
[../../reference/config-recommendation.md](../../reference/config-recommendation.md) 의 출력 포맷대로
안내 블록을 출력한다. 모든 값을 plugins.json 에서 얻었으면 생략한다.

**권고 대상:**
- **포함**: AskUserQuestion 으로 받은 값 (다음부터 자동 처리되려면 plugins.json 에 저장 필요). 예: `project`, `swaggerBaseUrl`, `modules`(4-1단계에서 사용자에게 매핑받은 prefix → 모듈명)
- **제외**: CLI 인자로 받은 값(`--base`, `--no-base`, `--dry-run`), AI 가 자동 판단한 값 (자동 감지된 이전 태그, 생성된 릴리즈 노트 본문, 추출된 이슈 키 등)

