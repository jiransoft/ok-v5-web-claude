---
name: code-review
description: 변경된 코드를 4개의 전문 리뷰어 에이전트(설계·로직·성능·테스트)로 병렬 리뷰하고 결과를 심각도별로 종합 보고한다. 워킹 디렉토리 변경 또는 브랜치 diff를 대상으로 하며, 필요 시 수정까지 진행한다.
when_to_use: 사용자가 "코드리뷰", "코드 리뷰", "code review", "리뷰 해줘", "변경사항 리뷰", "브랜치 리뷰" 등 코드 변경에 대한 리뷰를 요청할 때 사용한다.
allowed-tools: Bash(git *), Read, Grep, Glob, Agent
argument-hint: "[--source <branch>] [--base <branch>]"
---

# Code Review Skill

코드 리뷰를 수행합니다. 4개의 전문 리뷰어 에이전트를 병렬로 실행하여 결과를 종합합니다.

## 옵션

| 옵션 | 설명 |
|------|------|
| `--source <branch>` | 리뷰할 브랜치 지정 (worktree 격리). 미지정 시 현재 브랜치. |
| `--base <branch>` | diff 분석 기준 브랜치 지정. 미지정 시 자동 감지. |

## 설정 로드 — worktree 생성 **전에** 수행한다

⚠️ **이 섹션을 절차 0-1(worktree 생성)보다 먼저 처리한다.** 순서가 뒤집히면
"이후 모든 코드 읽기는 worktree 경로에서" 지시에 끌려 설정까지 worktree 에서 찾게 되는데,
`.claude/plugins.json` 은 gitignore 대상이라 거기엔 없다. 설정이 멀쩡히 있는데도 못 찾는다.

Read 도구로 **본체 레포 루트의 `.claude/plugins.json`** 을 읽어 `code-review-suite.techStack`
을 가져온다. 없으면 2단계에서 diff 의 파일 확장자로 추론한다.

## 절차

### 0. 인자 파싱

`$ARGUMENTS`에서 다음을 파싱한다:
- `--source <branch>`: 리뷰 대상 브랜치 (미지정 시 현재 브랜치)
- `--base <branch>`: diff 분석 기준 브랜치 (미지정 시 자동 감지)

### 0-1. Worktree 생성 (`--source` 지정 시)

`--source`가 지정된 경우, 격리된 worktree를 생성하여 해당 브랜치 코드 기준으로 리뷰한다.
미지정 시 이 단계를 건너뛰고 현재 디렉토리에서 리뷰한다 (기존 동작).

```bash
# 스테일 worktree 자기 치유 (이전 실행이 중단돼 남아 있으면 제거)
git worktree remove --force /tmp/wt-code-review 2>/dev/null; git worktree prune; rm -rf /tmp/wt-code-review
git worktree add --detach /tmp/wt-code-review <source>
```

- `--detach`를 사용하여 브랜치 잠금 충돌을 방지한다
- 이후 모든 코드 읽기(Read, Grep, Glob)는 worktree 경로(`/tmp/wt-code-review`)에서 수행한다
- git 명령어(`git log`, `git diff`)는 원래 repo에서 ref를 직접 지정하여 실행한다

> 이하 `<source>`는 `--source` 지정 시 해당 브랜치, 미지정 시 `HEAD`를 가리킨다.

### 1. 리뷰 범위 결정

사용자가 범위를 명시하면 그대로 사용한다. 명시하지 않으면 자동으로 판단한다:

1. `--source`가 지정되지 않은 경우에만 `git diff --stat`과 `git diff --cached --stat`으로 워킹 디렉토리 변경사항 확인
2. 워킹 디렉토리 변경이 없거나 `.claude/` 등 비코드 파일만 변경된 경우, 또는 `--source`가 지정된 경우:
   - **base 브랜치 결정** 후 `git log --oneline <base>..<source>`로 브랜치 커밋을 확인
   - 브랜치 커밋이 있으면 **브랜치 리뷰**로 전환 → **커밋 분석** 수행
3. 워킹 디렉토리에 코드 변경이 있으면 **워킹 디렉토리 리뷰**

#### Base 브랜치 결정

`--base`가 지정되었으면 해당 브랜치를 base로 사용한다. 미지정이면 **자동 감지**한다:

```bash
git branch -r
git merge-base <source> <each-branch>
git rev-list --count <merge-base>..<source>
```

1. `git branch -r`로 원격 브랜치 목록을 가져온다
2. 소스 브랜치 자신은 제외한다 (자기 자신 비교 방지)
3. 각 원격 브랜치와 `git merge-base <source> origin/<branch>`를 계산한다
4. merge-base에서 소스까지의 커밋 수가 **가장 적은** 브랜치를 base로 선택한다
5. 원격 브랜치가 없거나 계산 실패 시, 저장소의 기본 브랜치를 자동 감지해 사용한다: `git symbolic-ref --short refs/remotes/origin/HEAD`(예: `origin/main`)의 결과에서 `origin/`을 떼어 base로 쓰고, 이마저 없으면 `develop`을 최종 폴백으로 한다

#### 커밋 분석 (브랜치 리뷰 시 필수)

브랜치 리뷰로 전환되면, **관련 없는 커밋이 섞여있는지** 반드시 확인한다:

1. `git log --oneline <base>..HEAD`로 전체 커밋 목록을 확인한다
2. 커밋 메시지의 prefix/scope, Jira 이슈 키, 변경 파일 경로를 기준으로 **커밋을 그룹화**한다:
   ```
   예시:
   그룹 A (user-service): 3개 커밋 — PROJ-101, PROJ-102, PROJ-103
   그룹 B (license): 1개 커밋 — 3384f421e
   그룹 C (config): 2개 커밋 — f0d1e8f8c, 8e705717a
   ```
3. **그룹이 2개 이상이면** 사용자에게 확인한다:
   ```
   브랜치에 서로 다른 feature의 커밋이 섞여있습니다:

   1. user-service (3개 커밋): PROJ-101, PROJ-102, PROJ-103
   2. license refactor (1개 커밋): 3384f421e
   3. config/skill (2개 커밋): f0d1e8f8c, 8e705717a

   어떤 범위를 리뷰할까요?
   - 1번만 리뷰 (추천 — 현재 feature)
   - 전체 리뷰
   - 직접 지정
   ```
4. 사용자가 특정 그룹을 선택하면, 해당 그룹의 **첫 커밋의 부모**부터 HEAD까지를 diff 범위로 사용한다:
   - `git diff <첫 커밋>^..HEAD -- <해당 그룹 파일 경로들>`
   - 또는 해당 그룹 커밋들이 변경한 파일만 필터링한다
5. **그룹이 1개면** (모든 커밋이 같은 feature) 그대로 `<base>..HEAD`를 사용한다

범위 결정 후 사용자에게 "N개 파일을 [범위]로 리뷰합니다" 안내 후 진행한다.

**리뷰 범위 예시:**
- 워킹 디렉토리: `git diff` + `git diff --cached`
- 브랜치 전체: `git diff <base>..HEAD`
- 특정 커밋 그룹: `git diff <commit>^..HEAD -- <파일들>`
- 사용자 지정: 프롬프트에 명시된 범위

### 2. 스택 프로파일 결정

에이전트를 호출하기 전에 리뷰 대상의 스택을 한 줄로 정리한다:

1. 위 **설정 로드**에서 가져온 `code-review-suite.techStack` 이 있으면 그것을 쓴다
2. 없으면 **diff의 파일 확장자로 추론**한다 (예: `.kt`/`.java` → JVM 백엔드, `.ts`/`.tsx`/`.vue` → 프론트엔드, 혼재 → 풀스택으로 양쪽 다 명시)

스택 프로파일은 체크리스트가 아니라 **맥락**이다 — 무엇을 볼지는 각 리뷰어가 스택에 맞춰 스스로 판단한다.

### 3. 4개 리뷰어 에이전트 병렬 실행

다음 4개 에이전트를 **반드시 병렬로** (같은 턴에서 동시에) Agent 도구로 호출한다:

| 에이전트 | 관점 |
|---------|------|
| `design-reviewer` | 설계, 아키텍처, 가독성, 네이밍, 산출물 동기화 |
| `logic-reviewer` | 정확성, 에러 핸들링, 동시성·비동기, 데이터 정합성, 보안 |
| `performance-reviewer` | 반복 구간 비례 비용, 리소스 누적, 확장가능성 |
| `test-reviewer` | 테스트 커버리지, 테스트 품질, 누락 케이스, Mock 전략, 테스트 신뢰성 |

각 에이전트 호출 시 프롬프트에 **diff 범위와 스택 프로파일을 명시**한다:
```
다음 diff 범위로 변경사항을 리뷰해주세요.
- diff 범위: `git diff <base>..HEAD` (또는 해당 범위)
- 스택 프로파일: <2단계에서 결정한 값. 예: "프론트엔드 — React/TypeScript">
- 리뷰 대상: 소스 코드만 (설정 파일, lockfile, .claude/ 등 제외)
```

### 4. 결과 종합

4개 에이전트의 결과를 받으면 아래 형식으로 통합 리포트를 작성한다.

```
## Code Review 종합 결과

### 전체 요약
- 리뷰 범위: [브랜치 전체 (<base>..HEAD) / 워킹 디렉토리 / 기타]
- 리뷰 대상: N개 파일
- 🔴 Critical: N개 | 🟠 Major: N개 | 🟡 Minor: N개 | 💡 Suggestion: N개

### 🔴 Critical (즉시 수정 필요)
(4개 리뷰어 결과에서 Critical 이슈를 모아서 출처 표시)

### 🟠 Major (수정 권장)
(동일)

### 🟡 Minor (개선 가능)
(동일)

### 💡 Suggestion (제안)
(동일)

### ✅ 잘된 점
(4개 리뷰어가 공통으로 언급한 좋은 점)
```

- 이슈가 없는 심각도 레벨은 섹션을 생략한다
- 중복 지적은 하나로 합치고 관련 리뷰어를 모두 표시한다 (예: `[Design, Logic]`)
- 각 이슈에 출처 리뷰어를 태그한다 (예: `[Performance]`, `[Test]`)

### 5. 수정 여부 확인

종합 결과를 보여준 후, 수정할 항목이 있는지 사용자에게 확인한다.
사용자가 수정을 요청하면 코드를 수정하고 테스트를 실행하여 통과를 확인한다.

### 6. Worktree 정리 (`--source` 사용 시)

`--source`로 worktree를 생성한 경우, 리뷰 완료 후 정리한다.

```bash
git worktree remove /tmp/wt-code-review
```
