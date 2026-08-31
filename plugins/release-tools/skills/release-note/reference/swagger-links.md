# Swagger 링크 생성

## Contents

- [태그명 추출 절차](#태그명-추출-절차)
- [태그 우선순위 결정](#태그-우선순위-결정)
- [URL 조합 규칙](#url-조합-규칙)

### 6. Swagger 링크 생성 (`swaggerBaseUrl` 설정 시)

변경된 Controller의 Swagger 태그명을 추출하여 딥링크를 생성한다.

```
Swagger URL = <swaggerBaseUrl>#/<URL-encoded-tag-name>/<methodName>
```

#### 태그명 추출 절차

1. 변경된 Controller 파일 경로를 추출하고, `git show <source-tag>:<file-path>`로 해당 태그 시점의 소스를 읽는다
2. **Controller가 여러 개인 경우 병렬로 읽는다** (Agent 또는 병렬 Bash 호출)
3. 태그 어노테이션을 찾는다. **메서드 레벨 어노테이션이 클래스 레벨을 override**하므로, 대상 메서드에 태그가 붙어있으면 그 메서드에 한해 메서드 레벨을 우선한다. 어노테이션 형태는 **두 가지 패턴**이 있다:

**패턴 A: 직접 `@Tag` 사용**
```kotlin
@Tag(name = "IT 자산 관리")
@RestController
class AssetController
```
→ `@Tag(name = "...")` 에서 바로 추출

**패턴 B: 커스텀 태그 어노테이션 사용**

커스텀 어노테이션으로 `@Tag`를 감싸는 구조. 래퍼 어노테이션(`@MetaTag`/`@FeatureTag`)의 유무에 따라 2단 또는 3단 구조로 나뉜다.

**B-1. 2단 구조 — 커스텀 태그 어노테이션 → `@Tag`** (래퍼 없음)

```kotlin
// 커스텀 어노테이션 정의 (별도 파일)
@Tag(name = "IT 자산 관리", description = "IT 자산 관리 API")
annotation class AssetManagementTag(
    val precedence: Int = Ordered.HIGHEST_PRECEDENCE
)

// Controller에서 사용
@AssetManagementTag
@RestController
class AssetController
```

→ Controller에 붙은 커스텀 어노테이션의 정의 파일을 `git grep -l 'annotation class <Name>' <source-tag> -- '*.kt'`(Bash)로 찾고, `git show <source-tag>:<path>`(Bash)로 읽어 `@Tag(name = "...")`을 추출한다. `precedence`가 커스텀 어노테이션 자체에 선언되어 있을 수 있다.

**B-2. 3단 구조 — `@MetaTag`/`@FeatureTag` 래퍼 → 커스텀 태그 어노테이션 → `@Tag`** (래퍼 있음)

래퍼 어노테이션이 커스텀 태그 어노테이션을 참조하고, 커스텀 태그 어노테이션에 `@Tag`가 선언된 구조:

```kotlin
// 래퍼 어노테이션 정의
annotation class MetaTag(
    val value: KClass<out Annotation>,
    val precedence: Int = Ordered.HIGHEST_PRECEDENCE   // 값이 낮을수록 우선순위 높음
)
annotation class FeatureTag(
    val value: KClass<out Annotation>,
    val precedence: Int = Ordered.LOWEST_PRECEDENCE    // 값이 높을수록 우선순위 낮음
)

// 커스텀 태그 어노테이션 정의 (별도 파일)
@Tag(name = "IT 자산 관리", description = "IT 자산 관리 API")
annotation class AssetManagementTag

@Tag(name = "소프트웨어 자산", description = "소프트웨어 자산 API")
annotation class SoftwareAssetTag

// Controller에서 사용 — 단일 래퍼
@MetaTag(value = AssetManagementTag::class)       // precedence = HIGHEST_PRECEDENCE (기본값)
@FeatureTag(value = SoftwareAssetTag::class)       // precedence = LOWEST_PRECEDENCE (기본값)
@RestController
@RequestMapping("/api/v3/common-policy/software")
class SoftwareAssetControllerV3

// 또는 컨테이너 어노테이션으로 다중 선언 — @MetaTags, @FeatureTags
@FeatureTags(
    value = [
        FeatureTag(value = TaggableTag::class),
        FeatureTag(value = HardwareAssetTag::class)
    ]
)
@RestController
class HardwareAssetController
```

→ 래퍼에서 참조하는 커스텀 태그 어노테이션을 먼저 특정하고, 그 정의 파일에서 `@Tag(name = "...")`을 추출한다.

**공통 추출 절차:**

1. Controller(또는 메서드)에서 태그 관련 어노테이션을 모두 모아 후보 목록을 만든다
   - **직접 `@Tag`**: 그대로 후보에 담는다 (패턴 A)
   - **래퍼 없는 커스텀 어노테이션** (예: `@AssetManagementTag`): 그대로 후보에 담는다 (패턴 B-1)
   - **`@MetaTag`/`@FeatureTag` 등 래퍼**: `value` 파라미터의 클래스명을 후보에 담는다 (패턴 B-2)
   - 컨테이너 어노테이션(`@MetaTags`, `@FeatureTags` 등)은 `value` 배열을 펼쳐 **내부의 모든 래퍼를 개별 항목으로 전개**한다
2. 후보 목록에서 `precedence`로 우선순위를 결정한다 (아래 "태그 우선순위 결정" 참조). **사용처에서 오버라이드한 `precedence` 값이 정의의 기본값보다 우선한다**
3. 선택된 후보가 커스텀 어노테이션이면 해당 정의 파일을 `git grep -l 'annotation class <Name>' <source-tag> -- '*.kt'`(Bash)로 찾고, `git show <source-tag>:<path>`(Bash)로 읽어 `@Tag(name = "...")`을 추출한다
4. 위 과정에서 `@Tag`를 특정할 수 없으면 Swagger 링크 컬럼을 비워 FE에 수동 확인을 요청한다

#### 태그 우선순위 결정

Controller/메서드에 태그 관련 어노테이션이 여러 개 붙어있을 수 있다. 아래 순서로 결정한다:

1. **메서드 레벨 어노테이션이 클래스 레벨을 override한다.** 대상 메서드에 태그가 붙어있으면 그 메서드에 한해 메서드 레벨 후보만 사용한다
2. **`precedence` 값이 낮을수록 우선순위가 높다**
   - `Ordered.HIGHEST_PRECEDENCE` = `Int.MIN_VALUE` = 가장 높음
   - `Ordered.LOWEST_PRECEDENCE` = `Int.MAX_VALUE` = 가장 낮음
   - 패턴 B-2(래퍼 있음)는 래퍼의 `precedence`를, 패턴 B-1(래퍼 없음)은 커스텀 어노테이션 자체의 `precedence`를 본다
   - 사용처에서 오버라이드한 `precedence` 값이 정의의 기본값보다 우선한다
   - 예: `@MetaTag`(HIGHEST) vs `@FeatureTag`(LOWEST) → `@MetaTag`의 `AssetManagementTag` → `@Tag(name = "IT 자산 관리")` 사용
3. **동일 `precedence`가 여러 개이면 소스에서 먼저 선언된 것을 사용한다**
4. `precedence`가 없거나 직접 `@Tag`를 사용한 경우, 소스 코드에서 가장 먼저 선언된 것을 사용한다

#### URL 조합 규칙

- 태그명은 URL 인코딩한다 (예: `IT 자산 관리` → `IT%20%EC%9E%90%EC%82%B0%20%EA%B4%80%EB%A6%AC`)
- operationId(URL의 메서드 부분) 결정 규칙:
  1. 메서드에 `@Operation(operationId = "...")`이 지정되어 있으면 그 값을 사용한다
  2. 없으면 `fun` 이름을 그대로 사용한다 (springdoc 기본 operationId)
  3. 오버로드된 메서드는 springdoc이 `methodName_1`, `methodName_2` 같은 접미사를 붙인다. 확신이 없으면 링크 컬럼을 비우고 FE에 수동 확인을 요청한다
