# 릴리즈 노트 출력 템플릿

7단계 "릴리즈 노트 작성"의 출력 형식. 기본 모드(변경 없음/있음)와 스냅샷 모드 템플릿을 정의한다.

## Contents

- [기본 모드 — API 변경사항이 없는 경우](#기본-모드--api-변경사항이-없는-경우)
- [기본 모드 — API 변경사항이 있는 경우](#기본-모드--api-변경사항이-있는-경우)
- [스냅샷 모드 (`--no-base`)](#스냅샷-모드---no-base)

#### 기본 모드 — API 변경사항이 없는 경우

5단계 분석 결과 API 변경사항(새 API, Breaking Changes, 응답 필드 변경, Deprecated)이 하나도 없으면 nil 릴리즈 노트를 생성한다:

```markdown
## <source-tag> API 변경사항

> 이전 릴리즈: `<base-tag>` | 관련 이슈: <이슈 키>

API 변경사항 없음
```

#### 기본 모드 — API 변경사항이 있는 경우

아래 형식으로 마크다운을 생성한다.

```markdown
## <source-tag> API 변경사항

> 이전 릴리즈: `<base-tag>` | 관련 이슈: <커밋에서 추출한 이슈 키>
>
> [Swagger UI](<swaggerBaseUrl>)    ← swaggerBaseUrl 설정 시

### <모듈 A>

#### 새로운 API

| Method | Path | 설명 | Swagger |
|--------|------|------|---------|
| `POST` | `/api/v3/...` | 설명 | [열기](<link>) |

(새 API가 없으면 섹션 생략)

#### Breaking Changes

##### N. <변경 카테고리>

변경 내용 테이블 또는 설명.
각 API에 Swagger 링크 포함.

(Breaking Change가 없으면 섹션 생략)

#### 응답 필드 변경

| 응답 | 변경 내용 |
|------|----------|
| DTO명 | 변경 설명 |

(필드 변경이 없으면 섹션 생략)

#### Deprecated

| 엔드포인트 | 제거 예정 | 대체 | Swagger |
|-----------|----------|------|---------|
| ... | ... | ... | ... |

(Deprecated가 없으면 섹션 생략)

### <모듈 B>

(같은 구조 반복)
```

#### 스냅샷 모드 (`--no-base`)

```markdown
## <source-tag> 릴리즈 (스냅샷)

> 스냅샷 모드 — 이전 태그 비교 없이 source-tag 기준 전체 API 목록
>
> [Swagger UI](<swaggerBaseUrl>)    ← swaggerBaseUrl 설정 시

### <모듈 A>

#### 전체 API 목록

##### <Swagger 태그 A>

| Method | Path | 설명 | Swagger |
|--------|------|------|---------|
| `GET`  | `/api/v3/...` | 설명 | [열기](<link>) |
| `POST` | `/api/v3/...` | 설명 | [열기](<link>) |

##### <Swagger 태그 B>

| Method | Path | 설명 | Swagger |
|--------|------|------|---------|
| ... |

#### Deprecated

| 엔드포인트 | Swagger |
|-----------|---------|
| ... | ... |

(Deprecated가 없으면 섹션 생략)

### <모듈 B>

(같은 구조 반복)
```

> 스냅샷 모드는 "관련 이슈" 줄을 생략한다 (비교 기준이 없어 커밋 범위가 없음).
> 스냅샷 모드에서 모듈 내 Swagger 태그가 단 하나뿐이면 `##### <태그>` 헤더는 생략하고 표만 바로 둔다.
