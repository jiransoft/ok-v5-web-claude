# Jackson 네이밍 전략 감지 및 적용 규칙

`postman-tools` 플러그인의 모든 스킬이 공유하는 검증·작성 기준이다.

Jackson 네이밍 전략은 **프로젝트의 Spring 설정에서 직접 감지**한다.
`plugins.json` 에 하드코딩된 `jacksonStrategy` 같은 값은 참고하지 않는다 — 코드가 유일한 진실이다.

## 목차

- [감지 절차](#감지-절차)
- [전략별 규칙 — SNAKE_CASE](#전략별-규칙--snake_case)
- [전략별 규칙 — LOWER_CAMEL_CASE (기본값)](#전략별-규칙--lower_camel_case-기본값)

## 감지 절차

1. Spring 설정 파일에서 `spring.jackson.property-naming-strategy` 값을 찾는다:

   ```bash
   grep -RInE 'property-naming-strategy|propertyNamingStrategy' \
     --include='*.yml' --include='*.yaml' --include='*.properties' \
     src/main/resources 2>/dev/null
   ```

   - yaml 예: `spring.jackson.property-naming-strategy: SNAKE_CASE`
   - properties 예: `spring.jackson.property-naming-strategy=SNAKE_CASE`

2. 값이 없으면 Java/Kotlin 설정 코드에서 확인한다 (`ObjectMapper` 빈 등):

   ```bash
   grep -RInE 'PropertyNamingStrategies\.|setPropertyNamingStrategy|@JsonNaming' \
     --include='*.kt' --include='*.java' src/main 2>/dev/null
   ```

3. 모두 찾지 못하면 Spring Boot 기본값 **`LOWER_CAMEL_CASE`(camelCase)** 로 간주한다.
4. 값이 `SNAKE_CASE`/`LOWER_CAMEL_CASE` 이외(예: `KEBAB_CASE`, `UPPER_CAMEL_CASE`)라면
   AskUserQuestion 으로 적용 규칙을 확인한다.
5. `--source` 모드에서는 **해당 worktree 의 설정**을 읽어 감지한다 (현재 브랜치 설정이 아니다).

## 전략별 규칙 — SNAKE_CASE

| 구분 | 규칙 | 이유 |
|------|------|------|
| Query Parameters | **camelCase** | Spring WebDataBinder 바인딩, Jackson 미적용 |
| Request Body (JSON) | **snake_case** | Jackson SNAKE_CASE 적용 |
| Response Body (JSON) | **snake_case** | Jackson SNAKE_CASE 적용 |
| Sort 파라미터 값 | **camelCase** | Spring Pageable 바인딩 |
| Search field 값 | **camelCase** | 서버가 문자열로 해석, Kotlin 프로퍼티명 기준 |

## 전략별 규칙 — LOWER_CAMEL_CASE (기본값)

| 구분 | 규칙 | 이유 |
|------|------|------|
| Query Parameters | **camelCase** | Spring WebDataBinder 바인딩 |
| Request Body (JSON) | **camelCase** | Jackson 기본 전략 그대로 |
| Response Body (JSON) | **camelCase** | Jackson 기본 전략 그대로 |
| Sort 파라미터 값 | **camelCase** | Spring Pageable 바인딩 |
| Search field 값 | **camelCase** | 프로퍼티명 기준 |

**Query Parameters 는 어느 전략에서도 항상 camelCase 다.** Jackson 이 관여하지 않기 때문이다 —
`SNAKE_CASE` 프로젝트에서 Query 자리에 `snake_case` 필드명이 보이면 오류로 판정한다.
