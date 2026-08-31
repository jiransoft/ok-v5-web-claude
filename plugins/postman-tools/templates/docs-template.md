# Postman Docs 템플릿

`postman-request`(작성) / `postman-docs-review`(검증) 양쪽이 동일한 골격으로 본문을 만들고 검사하기 위한 공유 템플릿이다.
신규 endpoint docs를 작성할 때 아래 **빈 스켈레톤**을 그대로 복사한 뒤, 사용하지 않는 row만 비우거나 "해당 없음"으로 명시한다 (섹션 자체는 삭제하지 않는다).

---

## 표기 규칙

### 타입

- 기본형: `string`, `number`, `boolean`, `array`, `object`
- nullable: 타입 뒤에 `?` 표기 (예: `string?`, `SimpleAgent?`)
- format: 괄호로 명시 (예: `string(ISO-8601)`, `string(UUID)`)
- DTO 참조: 클래스명 그대로 (예: `SimpleAgent`) — 동일 docs 안에 sub-DTO 섹션을 함께 둔다
- enum / enum?: 타입 칸은 `enum` 또는 `enum?`만 적고, 값 목록은 **설명 컬럼**에 백틱으로 분리 나열

### enum 값 표기 (백틱 안에는 값 하나씩)

- 예: `` `EXACT` `` | `` `CONTAINS` `` | `` `STARTS_WITH` `` (기본 `` `CONTAINS` ``)
- nullable enum: 값 끝에 `(nullable)` — `null`을 백틱 안에 넣지 않는다
- 예: `` `WINDOWS` ``, `` `MACOS` `` (nullable)

### 필수 컬럼

- 필수: `O`
- 선택: `-`
- Response 표는 항상 반환되므로 필수 컬럼을 두지 않는다 (3열).

### nested 표기

- **dot notation으로 펼침** — 해당 endpoint 전용이고 nested depth 2 이하인 inline 구조 (예: `search.field`, `filter.osType`)
- **별도 sub-DTO 섹션** (`#### <DtoClassName>`) — 다른 endpoint에서도 재사용되는 DTO (예: `SimpleAgent`, `SimpleUser`). 클래스명 그대로 헤더로 적는다.

### 표 컬럼 고정

| 영역 | 컬럼 |
| --- | --- |
| Path Variables | `파라미터 \| 타입 \| 필수 \| 설명` |
| Query Parameters | `파라미터 \| 타입 \| 필수 \| 설명` |
| Request Body | `필드 \| 타입 \| 필수 \| 설명` |
| Response Body / sub-DTO | `필드 \| 타입 \| 설명` |
| Status Codes | `코드 \| 설명` |

---

## 빈 스켈레톤

아래를 그대로 복사하여 채운다. **섹션 순서를 바꾸지 않는다.** 사용하지 않는 섹션은 통째로 삭제하지 말고 표 본문을 비우거나 "해당 없음"이라고 명시한다.

````markdown
> Last modified: YYYY-MM-DD

<한 줄 요약>. (`@<HttpMethod>Mapping("<URL>")`)

### Path Variables

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `<name>` | <type> | O | <설명> |

### Query Parameters

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `<name>` | <type> | - | <설명> |

#### Pageable 표준 (offset 페이징을 쓰는 경우 — 사용 안 하면 이 섹션 통째 삭제)

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `page` | number | - | 페이지 번호 (0-base, 기본 `0`) |
| `size` | number | - | 페이지 크기 (기본 `20`) |
| `sort` | string | - | 정렬 가능 필드: `<field1>`, `<field2>` (기본 `<field>,desc`). 형식 `field,asc\|desc` |

#### Cursor 페이징 (cursor 페이징을 쓰는 경우 — 사용 안 하면 이 섹션 통째 삭제)

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `cursor` | string? | - | 이전 응답의 `nextCursor`. 첫 페이지는 null/생략 |
| `size` | number | - | 페이지 크기 (기본 `20`) |
| `sort` | string | - | 정렬 가능 필드: `<field1>` (기본 `<field>,desc`) |

### Request Body — `<RequestDtoClassName>`

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `<field>` | <type> | - | <설명> |

> body 없는 endpoint(GET/DELETE 등)는 위 표 대신 "해당 없음 (body 없음)" 한 줄로 대체.

### Response — `<ResponseDtoClassName>`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `<field>` | <type> | <설명> |

#### `<SubDtoClassName>`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `<field>` | <type> | <설명> |

#### 페이지 응답 래퍼 — `CursorPage` (cursor 페이징을 쓰는 경우 — 사용 안 하면 통째 삭제)

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `content[]` | array | 페이지 항목 (위 Response 표 참조) |
| `nextCursor` | string? | 다음 페이지 커서 (마지막 페이지이면 `null`) |
| `totalCount` | number? | 전체 개수 (집계 비활성화 시 `null`) |

#### 페이지 응답 래퍼 — `PagedModel` (offset 페이징을 쓰는 경우 — 사용 안 하면 통째 삭제)

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `_embedded.items[]` | array | 페이지 항목 (위 Response 표 참조) |
| `page.size` | number | 페이지 크기 |
| `page.totalElements` | number | 전체 개수 |
| `page.totalPages` | number | 전체 페이지 수 |
| `page.number` | number | 현재 페이지 번호 (0-base) |

> Jackson `SNAKE_CASE` 프로젝트에서는 `page.totalElements` → `page.total_elements`, `page.totalPages` → `page.total_pages`로 변환된다.

### Status Codes

| 코드 | 설명 |
| --- | --- |
| `200 OK` | 정상 응답 |
| `400 Bad Request` | <검증 실패 사유> |
| `403 Forbidden` | <필요 권한> 권한 없음 |
| `404 Not Found` | <대상> 미존재 |

### 권한

- `<resource:scope>` / `<action>`
````

---

## 작성된 예시

(원본 예시에 5개 보강을 반영한 결과)

````markdown
> Last modified: 2026-05-08

SW-그룹 매핑에 해당하는 설치 내역을 PC 기준으로 커서 페이지 조회합니다. (`@PostMapping("/{mappingId}/install/pc")`)

### Path Variables

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `mappingId` | number | O | SW-그룹 매핑 ID |

### Query Parameters

(고유 파라미터 없음 — 페이징 파라미터는 아래 Cursor 페이징 참조)

#### Cursor 페이징

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `cursor` | string? | - | 이전 응답의 `nextCursor`. 첫 페이지는 null/생략 |
| `size` | number | - | 페이지 크기 (기본 `20`) |
| `sort` | string | - | 정렬 가능 필드: `installedAt`, `pcName` (기본 `installedAt,desc`) |

### Request Body — `SoftwareAssetStatSearchRequestByPc`

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `search.field` | string | - | 검색 필드 |
| `search.keyword` | string | - | 검색 키워드 |
| `search.matchType` | enum | - | `EXACT` \| `CONTAINS` \| `STARTS_WITH` (기본 `CONTAINS`) |
| `filter.osType` | enum? | - | `WINDOWS`, `MACOS` (nullable) |

### Response — `CursorPage<SoftwareAssetInstallByPcResponse>`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `installedAt` | string(ISO-8601) | 설치일 |
| `assetBasis` | enum? | `PC`, `USER` (nullable) |
| `pc` | SimpleAgent | PC 정보 |
| `loginUser` | SimpleUser? | 로그인 사용자 |

#### `SimpleAgent`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `id` | number | 에이전트 ID |
| `osType` | enum? | `WINDOWS`, `MACOS` (nullable) |
| `osDescription` | string? | OS 상세 |
| `ipv4` | string | IP |
| `publicIpv4` | string? | 공인 IP |
| `macAddress` | string? | MAC |
| `pcName` | string | PC명 |
| `buildVersion` | string? | 에이전트 빌드 버전 |
| `lastLoggedInAt` | string(ISO-8601)? | 마지막 로그인 시각 |
| `lastPcVulnerabilityInspectedAt` | string(ISO-8601)? | 마지막 PC 취약점 점검 시각 |
| `lastCfmInspectedAt` | string(ISO-8601)? | 마지막 CFM 점검 시각 |

#### `SimpleUser`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `id` | number | 사용자 ID |
| `username` | string? | 계정명 |
| `name` | string? | 사용자 이름 |
| `email` | string? | 이메일 |
| `department` | SimpleDepartment? | 부서 |
| `picture` | string? | 프로필 이미지 |

#### `SimpleDepartment`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `id` | number? | 부서 ID |
| `name` | string? | 부서명 |
| `path` | string? | 부서 경로 |

#### 페이지 응답 래퍼 — `CursorPage`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `content[]` | array | 페이지 항목 (위 Response 표 참조) |
| `nextCursor` | string? | 다음 페이지 커서 (마지막 페이지이면 `null`) |
| `totalCount` | number? | 전체 개수 (집계 비활성화 시 `null`) |

### Status Codes

| 코드 | 설명 |
| --- | --- |
| `200 OK` | 정상 응답 |
| `400 Bad Request` | `search.matchType` 등 enum 잘못된 값, `cursor` 형식 오류 |
| `403 Forbidden` | `wsm:software-asset / LIST` 권한 없음 |
| `404 Not Found` | `mappingId`에 해당하는 매핑이 존재하지 않음 |

### 권한

- `wsm:software-asset` / `LIST`
````

---

## 작성·검증 시 주의사항

1. **섹션 순서 고정.** review의 B 영역 검증이 위치 기반으로 파싱한다.
2. **사용 안 하는 섹션은 본문만 비우거나 "해당 없음" 명시.** 섹션 자체 삭제 시 review가 "누락"으로 판정.
3. **단, 페이징 보조 섹션(`Pageable 표준` / `Cursor 페이징` / `페이지 응답 래퍼 — *`)은 사용 안 하는 종류를 통째 삭제.** 두 페이징을 동시에 쓰는 endpoint는 없으므로 항상 하나만 남는다.
4. **DTO 클래스명을 헤더에 정확히 적는다.** review B3/B4가 클래스명을 grep으로 매칭한다.
5. **`Last modified` 갱신.** 본 docs를 수정할 때마다 첫 줄 날짜를 현재 날짜로 갱신.
