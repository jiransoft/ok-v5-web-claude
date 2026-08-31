---
name: dev-report
description: 현재 브랜치의 개발 이력을 분석하여 리뷰어용 레포트를 생성합니다. PR body 업데이트도 지원합니다.
when_to_use: 사용자가 "개발 레포트 만들어줘", "리뷰어용 리포트 작성해줘", "이 브랜치 작업 내용 정리해줘", "PR 설명(body) 업데이트해줘", "dev report", "리뷰 요약 문서 만들어줘" 등 브랜치의 개발 이력을 리뷰어가 파악하기 쉽게 정리하거나 그 내용으로 PR description을 갱신하려 할 때.
allowed-tools: Bash(git *), Bash(gh *), Read, Grep, Glob, Agent
argument-hint: "[--source <branch>] [--base <branch>] [--update <PR번호>]"
---

# Dev Report Skill

현재 브랜치(또는 `--source`로 지정한 브랜치)의 변경사항을 분석하여 리뷰어용 레포트를 생성한다.

## 옵션

| 옵션 | 설명 |
|------|------|
| `--source <branch>` | 분석할 브랜치 지정 (worktree 격리). 미지정 시 현재 브랜치. |
| `--base <branch>` | diff 분석 기준 브랜치 지정. 미지정 시 자동 감지. |
| `--update <PR번호>` | 생성한 레포트로 해당 PR의 description을 업데이트 |

## 절차

### 1. 인자 파싱

`$ARGUMENTS`에서 다음을 파싱한다:

- `--source <branch>`: 분석 대상 브랜치 (미지정 시 현재 브랜치)
- `--base <branch>`: diff 분석 기준 브랜치 (미지정 시 자동 감지)
- `--update <번호>`: PR 업데이트 모드 + PR 번호

### 1-1. Worktree 생성 (`--source` 지정 시)

`--source`가 지정된 경우, 격리된 worktree를 생성하여 해당 브랜치 코드 기준으로 분석한다.
미지정 시 이 단계를 건너뛰고 현재 디렉토리에서 분석한다 (기존 동작).

```bash
# 스테일 worktree 자기 치유 (이전 실행이 중단돼 남아 있으면 제거)
git worktree remove --force /tmp/wt-dev-report 2>/dev/null; git worktree prune; rm -rf /tmp/wt-dev-report
git worktree add --detach /tmp/wt-dev-report <source>
```

- `--detach`를 사용하여 브랜치 잠금 충돌을 방지한다
- 이후 모든 코드 읽기(Read, Grep, Glob)는 worktree 경로(`/tmp/wt-dev-report`)에서 수행한다
- git 명령어(`git log`, `git diff`)는 원래 repo에서 ref를 직접 지정하여 실행한다

> 이하 `<source>`는 `--source` 지정 시 해당 브랜치, 미지정 시 `HEAD`를 가리킨다.

### 2. Base 브랜치 결정

`--base`가 지정되었으면 해당 브랜치를 base로 사용한다. 미지정이면 **자동 감지**한다:

```bash
git branch -r
git merge-base <source> <each-branch>
git rev-list --count <merge-base>..<source>
```

**감지 로직:**
1. `git branch -r`로 원격 브랜치 목록을 가져온다
2. 소스 브랜치 자신은 제외한다 (자기 자신 비교 방지)
3. 각 원격 브랜치와 `git merge-base <source> origin/<branch>`를 계산한다
4. merge-base에서 소스까지의 커밋 수(`git rev-list --count <merge-base>..<source>`)가 **가장 적은** 브랜치를 base로 선택한다
   - 예: `origin/feature/PROJ-100`과의 거리가 3커밋, `origin/develop`과의 거리가 15커밋 → base는 `feature/PROJ-100`
5. 원격 브랜치가 없거나 계산 실패 시, 저장소의 기본 브랜치를 자동 감지해 사용한다: `git symbolic-ref --short refs/remotes/origin/HEAD`(예: `origin/main`)의 결과에서 `origin/`을 떼어 base로 쓰고, 이마저 없으면 `develop`을 최종 폴백으로 한다

**감지 결과를 사용자에게 안내한다:**
```
Base 브랜치 자동 감지: feature/PROJ-100 (4개 커밋)
```

### 3. 변경사항 수집

다음 명령어를 **병렬로** 실행한다:

```bash
git log <base>..<source> --format="%h %s" --no-merges
git diff <base>..<source> --stat
git diff <base>..<source> --name-only
```

- 커밋이 없으면 "변경사항 없음"을 안내하고 중단한다

### 4. 소스 코드 분석

**커밋 메시지만으로 판단하지 않는다. 반드시 변경된 소스 코드를 직접 읽어서 분석한다.**

변경된 파일 중 핵심 파일을 Read 도구로 읽는다:
- Controller, Service, Entity/Model, Repository, DTO, Event, Migration SQL, Test

파일 수가 많으면 Agent(subagent)를 활용하여 병렬 분석한다.

### 5. 레포트 작성

수집한 정보를 종합하여 레포트를 작성한다. 형식은 아래 **출력 형식** 섹션을 따른다.

### 6. 출력 또는 MR 업데이트

- `--update` 없음: 레포트를 마크다운으로 출력하고 종료
- `--update <PR번호>`: 레포트를 해당 PR의 description으로 업데이트
  ```bash
  gh pr edit <PR번호> --body "<레포트>"
  ```
  - create-pr 가 만든 **템플릿 본문을 통째로 대체**한다 — 이 점을 함께 고지하고,
    업데이트 전 사용자에게 레포트를 보여주고 확인을 받는다
  - 업데이트 후 PR URL을 출력한다

### 7. Worktree 정리 (`--source` 사용 시)

`--source`로 worktree를 생성한 경우, 레포트 생성 완료 후 정리한다.

```bash
git worktree remove /tmp/wt-dev-report
```

## 출력 형식

변경 규모에 따라 형식을 조절한다.

### 소규모 (파일 5개 이하, 단순 수정)

```markdown
## 요약
- 변경사항 1~3줄

## 변경 내용
- 구체적인 변경 설명
```

### 중/대규모 (신규 기능, 구조 변경)

````markdown
## 기능 요약
**<기능명>** — 한 줄 설명

---

## API 엔드포인트 (<N>개)

### <ControllerName> (`<base-path>`)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/` | 설명 |

(Controller 추가/변경이 없으면 생략)

---

## 데이터 모델

엔티티 관계, 유니크 제약, 예약 필드 등

(Entity 추가/변경이 없으면 생략)

---

## 핵심 비즈니스 로직

**1. <메서드명> (<한줄 설명>)** — 복잡도 표시
- 동작 설명
- 주의점

(복잡한 Service 로직이 없으면 생략)

---

## 테스트 현황

### 요약

| 유형 | 파일 수 | 테스트 수 | 대상 |
|------|--------|----------|------|
| 통합 (TestContainers) | N | N | API 전체 흐름 (실제 DB) |
| 단위 Service (MockK) | N | N | 비즈니스 로직, 검증, 예외 |
| 단위 Controller (MockK) | N | N | HTTP 상태코드, 라우팅 |
| 단위 Repository (MockK) | N | N | QueryDSL, 조건 검색 |

(해당 유형이 없으면 행 생략)

### API별 테스트 매트릭스

| API | 정상 | 404 | 입력검증 | 비즈니스룰 | 동시성 | 중복 |
|-----|:----:|:---:|:-------:|:---------:|:-----:|:----:|
| POST /resource | ✅ | - | ✅ 설명 | ✅ 설명 | - | ✅ 409 |

- ✅: 테스트 존재 (간단한 설명 첨부)
- `-`: 해당 없음 또는 미작성
- 검증 관점 열은 상황에 맞게 조정 가능 (예: 권한, 페이징 등 추가)

### 통합 테스트 시나리오 상세

`<details>` 접이식으로 파일별 시나리오를 나열한다:

```markdown
<details>
<summary><b>TestClassName</b> (N 시나리오)</summary>

| # | 시나리오 | 검증 |
|---|---------|------|
| 1 | Given-When-Then 한줄 요약 | 검증 관점 |

</details>
```

- 실제 테스트 파일의 `it("...")` 문자열을 기반으로 작성한다
- setup용 `it`은 "setup"으로 표시한다

### 커버리지 갭

| # | 미검증 시나리오 | 중요도 | 비고 |
|---|--------------|--------|------|
| 1 | 시나리오 설명 | **높음**/중간/낮음 | 현재 구현 상태, 의도적 제외 사유 등 |

- 의도적으로 빠진 것과 누락된 것을 구분하여 비고에 기재
- 코드에 구현되었으나 테스트가 없는 경우 중요도 **높음**

(테스트가 없는 PR이면 이 섹션 전체 생략)

---

## 리뷰 시 주목할 포인트

### 설계 판단이 필요한 부분

| # | 포인트 | 현황 | 검토 사항 |
|---|--------|------|----------|
| 1 | 설명 | 현재 구현 | 대안/질문 |

### 잘 된 부분
- 좋은 패턴/구현 나열

````

## 작성 규칙

- **한글**로 작성한다
- 해당 사항이 없는 섹션은 생략한다
- 커밋 메시지만으로 추측하지 않는다 — 실제 코드를 읽고 분석한다
- 리뷰어가 "왜 이렇게 했지?"라고 물을 수 있는 부분을 선제적으로 설명한다
- 테스트 커버리지 갭은 실제 테스트 코드를 읽어 판단한다
- 비즈니스 로직 설명은 복잡한 메서드 위주로, 단순 CRUD는 생략한다
- 설정 변경(.gitignore, CLAUDE.md, skill 등)은 상세 분석하지 않는다

## 출력 규칙

- **최종 레포트만 출력한다** — 내부 분석 과정, 중간 메모를 노출하지 않는다
- 도구 호출의 raw 결과를 그대로 출력하지 않는다
- 출력 형식에 정의된 구조 외의 텍스트를 출력하지 않는다
