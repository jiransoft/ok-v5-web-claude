---
name: struct
description: 코드 분석 또는 자연어 서술을 바탕으로 archify JSON 을 작성하고, 동봉된 archify 엔진으로 검증(validate)·전달(deliver)·브라우저 검사(visual-check)를 거쳐 브라우저에서 탐색·발표할 수 있는 자립형 인터랙티브 HTML 다이어그램(architecture·workflow·sequence·dataflow·lifecycle)을 생성합니다. 수정용 JSON 소스를 함께 남깁니다. Mermaid 문서·PDF 는 diagram 스킬, 설계 의사결정 기록은 adr 스킬의 몫입니다.
when_to_use: 사용자가 "인터랙티브 다이어그램", "HTML 다이어그램", "탐색 가능한 아키텍처 맵", "클릭해서 볼 수 있는 구조도", "발표용 다이어그램", "struct 로 그려줘", "archify 로 그려줘", "interactive diagram" 등 브라우저에서 클릭·검색·확대해 볼 수 있는 다이어그램을 원할 때. 단순 "다이어그램 그려줘"·Mermaid·PDF 요청은 diagram 스킬을 쓴다.
allowed-tools: Bash(node ${CLAUDE_SKILL_DIR}/../../archify/bin/archify.mjs *), Bash(git *), Bash(cd *), Bash(rm *), Bash(mkdir *), Read, Grep, Glob, Write, Edit, Agent
argument-hint: <대상 설명> [--source <branch>] [--type <architecture|workflow|sequence|dataflow|lifecycle>] [--describe] [--output <path>]
---

# Struct Skill

코드 분석 또는 서술을 바탕으로 archify JSON 을 작성하고, 플러그인에 동봉된 archify 엔진으로
검증·전달해 **브라우저에서 탐색 가능한 자립형 HTML 다이어그램 1개**와 **수정용 JSON 소스**를 만든다.
Mermaid 문서·PDF 는 `/arch-tools:diagram`, 설계 의사결정 기록은 `/arch-tools:adr` 의 몫이다.

엔진은 `${CLAUDE_SKILL_DIR}/../../archify/` 에 있다. 모든 엔진 명령은 다음 형태로 실행한다:

```bash
node ${CLAUDE_SKILL_DIR}/../../archify/bin/archify.mjs <명령> ...
```

엔진 상세는 [UPSTREAM.md](../../archify/UPSTREAM.md) 와 업스트림 [SKILL.md](../../archify/SKILL.md) 에 있다.
아래 절차만으로 충분하며, 진단이 요구할 때만 [authoring-contract.md](../../archify/references/authoring-contract.md) 를 읽는다.

## --help 처리

`$ARGUMENTS`가 `--help` 또는 `-h` 면 [reference/usage.md](reference/usage.md) 의 사용법 블록을 그대로 출력하고 즉시 종료한다.

## 인자 파싱

- `$ARGUMENTS`에서 플래그 추출:
  - `--source <branch>` → 분석할 브랜치 (미지정 시 현재 브랜치)
  - `--type <type>` → 다이어그램 타입 강제 (미지정 시 2절에서 판단)
  - `--describe` → 코드 분석 없이 사용자 설명만으로 작성
  - `--output <path>` → 출력 디렉토리 (기본: `docs/`)
- 나머지 텍스트 → 다이어그램 대상 설명
- `--describe` 와 `--source` 를 함께 주면 `--source` 를 무시하고 그 사실을 알린다 (분석할 코드가 없다)

### 출력 위치

**산출물은 분석한 코드와 같은 계보에 남는다.** 로컬에 체크아웃된 브랜치는 분석 대상과
전혀 무관할 수 있다. 거기에 문서를 떨구면 엉뚱한 브랜치의 변경분이 된다.

| `--source` | 산출물 위치 |
|------------|------------|
| 미지정 | 현재 워킹트리의 `--output` (커밋하지 않는다) |
| 지정 | 0절 worktree 안의 `--output` → `docs/struct-<슬러그>` 브랜치에 커밋 |

`--source` 를 쓰면 **source 브랜치 자체는 건드리지 않는다.** 거기서 파생한 문서 전용
브랜치에 커밋하므로, 사용자는 그 브랜치를 보고 판단하면 된다.

산출물 디렉토리를 **하나의 절대경로로 확정**하고 `<OUT_DIR>` 로 표기한다. 주제 슬러그는
`<주제>` 로 표기한다 (영문 kebab-case, 예: `department-create-flow`). 산출물 이름은 고정이다:

| 파일 | 역할 |
|------|------|
| `<OUT_DIR>/<주제>.<type>.json` | archify JSON 소스. 다음 수정은 이 파일을 고쳐 5절부터 다시 돈다 |
| `<OUT_DIR>/<주제>.html` | 자립형 인터랙티브 HTML. 브라우저에서 바로 열린다 |

> **셸 변수를 쓰지 말 것.** Bash 호출마다 셸이 새로 뜨므로 변수는 다음 호출까지 살아남지 않는다.
> 이후 모든 명령에는 확정한 절대경로를 **리터럴로 직접 써넣는다.**

## 실행 절차

### 0. Worktree 생성 (`--source` 지정 시)

`--source`가 지정된 경우, 격리된 worktree를 생성하여 해당 브랜치 코드 기준으로 분석한다.
미지정 시 이 단계를 건너뛰고 현재 디렉토리에서 분석한다.

```bash
# <slug> = source 브랜치명의 / 와 특수문자를 - 로 치환 (feat/x → feat-x)
# 스테일 worktree 자기 치유 (이전 실행이 중단돼 남아 있으면 제거)
git worktree remove --force /tmp/wt-struct-<slug> 2>/dev/null; git worktree prune; rm -rf /tmp/wt-struct-<slug>
# 1) detached HEAD로 worktree 생성 (브랜치 잠금 충돌 방지)
git worktree add --detach /tmp/wt-struct-<slug> <source>

# 2) worktree로 이동하여 문서용 작업 브랜치 생성
cd /tmp/wt-struct-<slug>
git checkout -b docs/struct-<주제 슬러그>
```

- **1번의 `--detach` 를 빼지 않는다.** `<source>` 가 이미 다른 워크트리나 본체에
  체크아웃돼 있으면 `is already checked out at` 으로 실패한다
- **2번을 건너뛰지 않는다.** detached HEAD 에서 커밋하면 어느 ref에도 닿지 않는
  고아 커밋이 되어, worktree 제거와 함께 사라진다
- 이후 모든 코드 읽기(Read, Grep, Glob)와 산출물 생성은 worktree 경로에서 수행한다

### 1. 코드 분석 (`--describe` 면 건너뛴다)

대상 설명을 기반으로 관련 코드를 탐색한다:
- Grep/Glob으로 관련 클래스, 설정, 호출 관계, 큐·DB·외부 연동 파악
- 필요시 Agent(Explore)로 깊은 탐색
- 다이어그램에 넣을 사실만 모은다: 컴포넌트 이름, 역할, 연결 방향, 프로토콜·경로·이벤트 이름
- **실제로 확인한 것만 그린다.** 추정은 노드 `sublabel` 이나 카드에 "추정" 으로 표기한다

`--describe` 면 사용자 설명에서 같은 사실을 추린다. 설명에 없는 구성요소를 지어내지 않고,
다이어그램에 영향을 주는 빈칸만 한 번 되묻는다.

### 2. 다이어그램 타입 결정

`--type` 이 있으면 그대로 쓴다. 없으면 표로 정한다. 애매하면 `architecture` 다.

| 대상 | 타입 |
|------|------|
| 컴포넌트·서비스·저장소·네트워크 경계·인프라 | `architecture` |
| 절차·승인 게이트·도구 호출·런북·CI/CD | `workflow` |
| API 호출 체인·요청 생명주기·비동기 추적·응답 순서 | `sequence` |
| 파이프라인·ETL·데이터 계보·소비자 | `dataflow` |
| 상태 전이·재시도·대기·종료 상태 | `lifecycle` |

엔진의 `guide` 명령은 영어·중국어 신호만 인식하므로 쓰지 않는다.

### 3. 스키마와 예제 읽기

정확히 **세 파일만** 읽는다. 렌더러·검증기 소스나 테스트는 읽지 않는다.

| 타입 | 스키마 | 예제 |
|------|--------|------|
| architecture | `schemas/architecture.schema.json` | `examples/web-app.architecture.json` |
| workflow | `schemas/workflow.schema.json` | `examples/agent-tool-call.workflow.json` |
| sequence | `schemas/sequence.schema.json` | `examples/cache-miss-request.sequence.json` |
| dataflow | `schemas/dataflow.schema.json` | `examples/product-analytics.dataflow.json` |
| lifecycle | `schemas/lifecycle.schema.json` | `examples/agent-run.lifecycle.json` |

세 파일 모두 `${CLAUDE_SKILL_DIR}/../../archify/` 아래에 있고, 공통 enum 은 `schemas/common.schema.json` 에 있다.
예제는 **필드 모양을 보는 용도**다. 예제의 사실·좌표·ID 를 복사하지 않는다.

### 4. JSON 작성

Write 도구로 `<OUT_DIR>/<주제>.<type>.json` 을 만든다. 규칙:

- `schema_version` 은 workflow 만 `2`, 나머지는 `1`. `diagram_type` 은 2절의 타입
- `meta.title` 은 한글 한 줄. `meta.quality_profile` 은 `"showcase"` 고정
- `meta.locale`, `meta.visual_preset`, `meta.subtitle`, `meta.animation` 은 **쓰지 않는다** (뷰어 UI 는 영어로 폴백된다)
- **주 경로 하나**가 한눈에 보이게 한다. 주 노드 12개 이하, 곁가지는 가장 가까운 주 경로 노드에서 뻗는다
- 콘텐츠(라벨·sublabel·카드·views)는 **한글**. 클래스명·API 경로·큐 이름·제품명·프로토콜은 원문 유지
- ID 는 영문 kebab-case 로 새로 짓는다. 관계에도 `id` 를 준다 (딥링크용)
- 관계 `label` 은 의미 데이터다. 프로토콜·동작·방향·동기/비동기를 담고, 양 끝 노드만으로 자명한 것만 생략한다
- `via`, `labelAt`, `channelX`, `channelY` 같은 좌표 제어는 **진단이 요구하기 전에는 쓰지 않는다**
- 한글은 폭이 두 배로 계산된다. architecture 의 `size` 폭은 라벨 글자수 × 14px 이상, 노드 사이 빈 간격은 80px 이상 두고, 라벨이 붙는 가로 연결은 노드 사이를 라벨 길이만큼 넉넉히 벌린다
- `cards` 는 2~3개로 핵심 경로·예외·비동기를 요약한다. `meta.views` 는 최대 3개, 실제 노드 ID 만 참조한다
- workflow 는 `lanes` 로 책임 주체, `col` 0..5 로 진행 순서를 표현하고 `mainPath` 를 채운다. 좌표는 쓰지 않는다
- 이 스킬 범위 밖이라 쓰지 않는 필드: `meta.repository`·`sources`(소스 근거), `brand`, `meta.engineering_profile`

### 5. 검증 루프

JSON 을 저장할 때마다 실행한다:

```bash
node ${CLAUDE_SKILL_DIR}/../../archify/bin/archify.mjs validate <type> <OUT_DIR>/<주제>.<type>.json --quality showcase --json
```

**통과 조건**: `ok: true`, `checks` 9개 모두 `ok`, `composition.summary` 의 `errors` 와 `warnings` 가 0.
종료코드가 0이 아니면 통과가 아니다.

실패하면 출력의 `diagnostics[]` 를 읽는다. 항목마다 `code`, `subject`, `evidence`, `supportedFixes` 가
있고 `message` 에 `Suggested fix: labelAt [x, y] or labelDy +N` 같은 **구체 수정값**이 붙는다.

1. 진단이 가리키는 `subject` 만 고친다. 제안값이 있으면 그 값을 그대로 쓴다
2. 라벨 겹침은 라벨을 옮기거나 노드 간격을 벌려서 푼다. **라벨을 지우는 것은 수정이 아니다**
3. 고친 뒤 **파일을 다시 validate 한다**. 기억이나 직전 출력으로 판단하지 않는다
4. 오류 수가 직전 최소치보다 줄지 않는 라운드가 **2회 연속**이거나 총 5라운드를 넘으면 멈추고
   "자동 수정 실패" 로 분류해 남은 진단을 그대로 보고한다. 임의로 더 고치지 않는다

workflow 의 기하 진단은 `--layout-json` 을 붙여 컴파일러 receipt(`viewBox`, `requiredViewBox`, `columns`) 를 보면 원인이 드러난다.

### 6. 전달 (deliver)

검증을 통과한 JSON 은 더 고치지 않고 그대로 전달한다:

```bash
node ${CLAUDE_SKILL_DIR}/../../archify/bin/archify.mjs deliver <type> <OUT_DIR>/<주제>.<type>.json <OUT_DIR>/<주제>.html --quality showcase --json
```

- 종료코드 0 이면 receipt 의 `specification.sha256`, `artifact.sha256`, `artifact.bytes`, `validation` 을 기록해 둔다 (결과 안내에 쓴다)
- 종료코드가 0이 아니면 **실패**다. 기존 HTML 이 있었다면 그대로 보존된다. 진단을 읽고 5절로 돌아간다
- `--open` 은 쓰지 않는다. 열기 방법은 결과 안내로 알린다

### 7. 브라우저 검사 (visual-check)

전달이 성공한 **그 HTML** 에 대해서만 실행한다:

```bash
node ${CLAUDE_SKILL_DIR}/../../archify/bin/archify.mjs visual-check <OUT_DIR>/<주제>.html --json
```

| 종료코드 | 의미 | 처리 |
|----------|------|------|
| `0` | 데스크톱 뷰포트 4종(1440×900~2048×1320) 모두 넘침 없음 | `browser_evidence: passed` |
| `1` | 어느 뷰포트에서 넘침·측정 실패 | `containment.viewports[]` 에서 넘친 뷰포트 확인. 노드 Y 좌표를 압축하거나 `meta.viewBox` 를 늘려 5절부터 1회만 재시도. 다시 실패면 `failed` 로 보고 |
| `2` | Chrome/Chromium 없음 | `skipped` 로 보고. 결과 안내에 `ARCHIFY_CHROME` 안내를 붙인다 |

검사가 끝나면 사이드카를 **반드시** 지운다. PNG 4장·contact sheet·receipt 약 1MB 가 산출물 옆에 남는다:

```bash
rm -f <OUT_DIR>/<주제>.visual-check.json <OUT_DIR>/<주제>.visual-check.html <OUT_DIR>/<주제>.visual-check.*.png
```

visual-check 는 넘침만 잰다. **화면을 직접 보지 않았으면 "시각 검토 완료" 라고 쓰지 않는다.**

### 8. 커밋 & Worktree 정리 (`--source` 사용 시)

`--source` 를 쓰지 않았으면 이 단계를 건너뛴다 — 산출물만 남기고 커밋하지 않는다.

7절의 사이드카 정리를 **먼저** 끝낸 뒤 커밋한다. 남아 있으면 `git status` 를 더럽히고 스테이징된다.

```bash
git -C /tmp/wt-struct-<slug> add <OUT_DIR 의 worktree 기준 상대경로>
git -C /tmp/wt-struct-<slug> commit -m "docs: <주제> 인터랙티브 다이어그램 추가"
git worktree remove /tmp/wt-struct-<slug>
```

- 커밋이 `docs/struct-<주제 슬러그>` 브랜치에 남으므로 worktree를 제거해도 유실되지 않는다
- **푸시하지 않는다.** 사용자가 브랜치를 확인한 뒤 판단한다
- `git worktree remove` 가 실패하면 정리 안 된 임시 파일이 남은 것이다. 지우고 다시 시도한다

## 결과 안내

```
docs/<주제>.html, docs/<주제>.<type>.json 을 생성했습니다.

  타입:       <type>
  검증:       9/9 showcase, 0 errors, 0 warnings  (수정 라운드 N회)
  브라우저:   passed | failed (<뷰포트> 넘침) | skipped (Chrome 없음 — ARCHIFY_CHROME 에 Chromium 경로를 주면 검사됩니다)
  열기:       open docs/<주제>.html   (파일을 더블클릭해도 열립니다. 네트워크 불필요)

  뷰어 조작:  ? 도움말 · / 노드 검색 · 노드 클릭 → 상하류 추적 · T 테마 · E 내보내기(PNG/SVG)
  뷰어 UI(범례·툴바)는 영어입니다. 다이어그램 내용은 한글입니다.
  다음 수정은 docs/<주제>.<type>.json 을 고쳐 다시 요청하면 됩니다.
```

`--source` 사용 시 산출물이 로컬 워킹트리에 없으므로 위치를 반드시 덧붙인다:

```
  브랜치: docs/struct-<주제 슬러그>  (<source> 에서 파생)
  확인:   git log -p docs/struct-<주제 슬러그>
  체크아웃: git switch docs/struct-<주제 슬러그>

현재 체크아웃된 브랜치는 건드리지 않았습니다. 푸시는 하지 않았습니다.
```

"자동 수정 실패" 로 끝났으면 성공처럼 쓰지 않는다. 남은 진단의 `code` 와 `subject`, 시도한 라운드 수를 적고
JSON 소스 위치를 알려 사용자가 이어서 고칠 수 있게 한다.

## 주의사항

- **종료코드가 0이 아닌 명령을 성공이라 쓰지 않는다.** validate·deliver·visual-check 모두 같다
- 엔진의 `examples` 명령은 플러그인 디렉터리에 HTML 4MB 를 다시 쓴다. `preview`, `compare`, `brands`, `--repo-root` 도 이 스킬 범위 밖이다. 호출하지 않는다
- 산출물 HTML 은 약 800KB 의 자립형 파일이다. 폰트·스크립트를 임베드하므로 오프라인에서 열리고, 외부 요청이 없다
- 뷰어 UI 로케일은 영어·중국어만 지원한다. `meta.locale` 에 `ko` 를 넣으면 스키마 검증에서 거부된다
- 엔진 버전과 업스트림 출처는 [UPSTREAM.md](../../archify/UPSTREAM.md) 에 있다. 엔진 파일은 손으로 고치지 않는다
