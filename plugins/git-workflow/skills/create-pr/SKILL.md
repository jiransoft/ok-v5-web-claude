---
name: create-pr
description: 현재 브랜치(또는 지정한 브랜치)의 변경사항을 분석하여 GitHub Pull Request를 생성합니다
when_to_use: 사용자가 "PR 만들어줘", "풀리퀘스트 생성해줘", "이 브랜치로 PR 올려줘", "MR 만들어줘", "create pull request", "open PR" 등 현재 또는 지정 브랜치의 변경사항으로 GitHub Pull Request를 새로 생성하려 할 때.
allowed-tools: Bash(git *), Bash(gh *), Read, Grep, Glob, Agent, AskUserQuestion, Skill
argument-hint: "[--target <branch>] [--source <branch>] [--base <branch>] [-a <username>] [-r <username>] [-l <label>] [-i]"
---

# Create PR Skill

현재 브랜치(또는 `--source`로 지정한 브랜치)의 변경사항을 분석하여 GitHub Pull Request를 생성한다.

## --help 처리

`$ARGUMENTS`가 `--help` 또는 `-h` 면 [reference/usage.md](reference/usage.md) 의 사용법 블록을 그대로 출력하고 즉시 종료한다.

## 사전 조건

- `gh` CLI가 설치되어 있어야 한다
- GitHub 인증이 완료되어 있어야 한다 (`gh auth status`로 확인)
  - 인증이 안 되어 있으면 `gh auth login` 을 안내하고 중단한다 (비대화형 환경은 `GH_TOKEN` 환경변수로 대체 가능)

## 설정 로드 — worktree 생성 **전에** 수행한다

⚠️ **이 섹션을 절차 2-1(worktree 생성)보다 먼저 처리한다.** 순서가 뒤집히면 "이후 모든 소스
코드 분석은 worktree 경로에서" 지시에 끌려 설정까지 worktree 에서 찾게 되는데,
`.claude/plugins.json` 은 gitignore 대상이라 거기엔 없다. 설정이 멀쩡히 있는데도 못 찾고
질문으로 떨어진다.

설정 우선순위: (1) Read 도구로 **본체 레포 루트의 `.claude/plugins.json`** 의 `git-workflow`
섹션 → (2) 프로젝트의 `CLAUDE.md` → (3) AskUserQuestion.
시스템 컨텍스트에 이미 로드된 값을 사용하지 말고, 반드시 Read 도구로 파일을 직접 읽는다.

가져올 키: `project` · `defaultAssignee` · `defaultReviewer` · `defaultLabels` · `moduleRoot`.

## 절차

### 1. 인증 확인

```
gh auth status
```

- 실패 시 `gh auth login` 을 안내하고 중단한다 (`GH_TOKEN` 환경변수가 있으면 gh 가 자동으로 사용한다)

### 2. 소스 브랜치 결정 및 검증

`--source`가 지정되었으면 해당 브랜치를 소스로 사용한다. 미지정 시 현재 브랜치를 소스로 사용한다:

```bash
# --source 미지정 시
git branch --show-current

# --source 지정 시: 해당 브랜치가 로컬에 존재하는지 확인
git rev-parse --verify <source>
```

- 소스 브랜치가 `main` 또는 `develop`이면 PR을 생성하지 않는다 — 사용자에게 안내하고 중단한다
- `--source`로 지정한 브랜치가 존재하지 않으면 사용자에게 안내하고 중단한다

### 2-1. Worktree 생성 (`--source` 지정 시)

`--source`로 다른 브랜치를 지정한 경우, 소스 코드를 정확히 읽기 위해 **임시 worktree**를 생성한다. 현재 브랜치를 checkout하지 않는다.

```bash
# 임시 worktree 생성
# 스테일 worktree 자기 치유 (이전 실행이 중단돼 남아 있으면 제거)
git worktree remove --force /tmp/wt-create-pr 2>/dev/null; git worktree prune; rm -rf /tmp/wt-create-pr
git worktree add --detach /tmp/wt-create-pr <source>
```

- 이후 모든 소스 코드 분석(Read, Grep, Glob)은 worktree 경로(`/tmp/wt-create-pr/`)를 기준으로 수행한다
- git 명령어(`git log`, `git diff`, `git push`)는 원래 repo에서 ref를 직접 지정하여 실행한다 (worktree 불필요)
- PR 생성 완료 후 worktree를 정리한다:
  ```bash
  git worktree remove /tmp/wt-create-pr
  ```
- `--source`를 지정하지 않은 경우(현재 브랜치 사용)에는 worktree를 생성하지 않는다

### 3. 타겟 브랜치 및 옵션 파싱

`$ARGUMENTS`에서 다음을 파싱한다:

- `--source`: 소스 브랜치 (미지정 시 현재 브랜치)
- `--target`: 타겟 브랜치 (미지정 시 자동 감지)
- `--base`: diff 분석 기준 브랜치 (미지정 시 타겟 브랜치를 사용)
- `-a`, `--assignee`: assignee username (1명)
- `-r`, `--reviewer`: reviewer username (1명)
- `-l`, `--label`: 라벨 이름 (복수: 쉼표 구분)
- `-i`, `--interactive`: 인터랙티브 모드 플래그

#### 타겟 브랜치 결정

`--target`이 지정되었으면 그대로 사용한다. 미지정이면 **자동 감지**한다.

> 이하 `<source>`는 2단계에서 결정된 소스 브랜치를 가리킨다 (`--source` 지정 시 해당 브랜치, 미지정 시 현재 브랜치 = `HEAD`).

```bash
# 원격 브랜치 목록과 소스 브랜치의 merge-base를 비교하여
# 가장 가까운(커밋 수가 적은) 브랜치를 타겟으로 선택한다.
git branch -r
git merge-base <source> <each-branch>
git rev-list --count <merge-base>..<source>
```

**감지 로직:**
1. `git branch -r`로 원격 브랜치 목록을 가져온다
2. 소스 브랜치 자신은 제외한다 (자기 자신 비교 방지)
3. 각 원격 브랜치와 `git merge-base <source> origin/<branch>`를 계산한다
4. merge-base에서 소스까지의 커밋 수(`git rev-list --count <merge-base>..<source>`)가 **가장 적은** 브랜치를 타겟으로 선택한다
   - 예: `origin/feature/PROJ-100`과의 거리가 3커밋, `origin/develop`과의 거리가 15커밋 → 타겟은 `feature/PROJ-100`
5. 원격 브랜치가 없거나 계산 실패 시, 저장소의 기본 브랜치를 자동 감지해 사용한다: `git symbolic-ref --short refs/remotes/origin/HEAD`(예: `origin/main`)의 결과에서 `origin/`을 떼어 base로 쓰고, 이마저 없으면 `develop`을 최종 폴백으로 한다

**감지 결과를 사용자에게 안내한다:**
```
타겟 브랜치 자동 감지: feature/PROJ-100 (4개 커밋)
```

#### Base 브랜치 결정

> 이하 `<base-branch>`는 diff 분석의 기준 브랜치를 가리킨다.

- `--base`가 지정되었으면 해당 브랜치를 `<base-branch>`로 사용한다
- 미지정이면 `<target-branch>`를 `<base-branch>`로 사용한다 (기존 동작과 동일)

`--base` 지정 시 안내:
```
PR 타겟: develop / diff 분석 기준: feature/PROJ-100
```

### 4. 변경사항 분석

다음 명령어를 **병렬로** 실행한다 (`<source>`는 2단계에서 결정된 소스 브랜치):

```
git log <base-branch>..<source> --oneline
git diff <base-branch>...<source> --stat
git diff <base-branch>...<source> --name-only
```

- 커밋이 없으면 사용자에게 안내하고 중단한다

### 5. PR 제목/본문 작성

PR 본문은 **팀 공용 템플릿**을 따른다. 자유 양식 금지 — 템플릿의 섹션 구조·순서가 유일한 진실이다.

#### 5-1. 템플릿 선택

4단계의 커밋 목록·diff 내용으로 변경의 성격을 판단해 둘 중 하나를 고른다:

| 변경 성격 | 템플릿 |
|-----------|--------|
| fix·refactor — "원인이 있어 고치는" 변경 | [`../../templates/pr-default.md`](../../templates/pr-default.md) (**원인** 항목 포함) |
| feat·docs·style·test·perf·chore·ci·build | [`../../templates/pr-feature.md`](../../templates/pr-feature.md) |

- 혼재하면 지배적인 쪽을 따른다. 판단이 애매하면 AskUserQuestion 으로 확인한다

#### 5-2. 본문 작성

선택한 템플릿을 Read 하고, 섹션 구조를 그대로 유지한 채 채운다.
**커밋 메시지만으로 채우지 않는다** — 4단계 결과에 더해 변경된 핵심 파일을 Read 로 직접 읽고 동작 기준으로 서술한다.

- HTML 주석(작성 가이드·title 패턴)은 채운 뒤 모두 삭제한다
- **(필수)** 섹션은 반드시 채운다. **(선택)** 섹션은 쓸 내용이 없으면 `해당 없음` 으로 남긴다 — 섹션 자체를 지우지 않는다
- **작업내용/수정내용**은 파일 나열이 아니라 동작(변화) 기준으로 쓴다
- **링크**: Jira 는 브랜치에서 추출한 이슈 키를 적는다(URL 을 알면 링크로). Figma 는 사용자가 준 것이 없으면 `해당 없음`
- **확인방법**의 체크박스는 체크하지 않은 상태로 둔다 — 작성자가 직접 확인 후 체크한다
- **스크린샷**: UI 변경이 감지되면 `(작성자 첨부 필요)` 를 남기고, 사용자 확인 단계에서 첨부를 안내한다
- 리뷰어용 상세 분석 레포트(API 표·테스트 매트릭스)가 따로 필요하면 PR 생성 후 `/dev-report --update <PR번호>` 를 별도로 쓴다

#### 5-3. 제목

- **패턴**: `[{이슈키}] {내용}`
- Jira 이슈 키는 소스 브랜치명에서 추출한다 (예: `OKEP-123-some-feature` → `OKEP-123`)
  - 추출 명령: `echo "<source>" | grep -oE '[A-Z]+-[0-9]+' | paste -sd, -`
  - 이슈가 여럿이면 쉼표로 잇는다 (예: `[OKEP-4810,OKEP-4813]`)
  - 브랜치명에 Jira 이슈 키가 없으면 `[NO-ISSUE]`로 대체한다
- 내용은 70자 이하, 한글로 변경의 핵심을 간결하게 요약
- 예: `[OKEP-4810,OKEP-4813] 소프트웨어 자산 목록 실시간 검색`

### 6. Assignee/Reviewer/Label 결정

#### 인터랙티브 모드 (`-i`)

`-i` 플래그가 있으면 프로젝트 멤버 및 라벨 목록을 조회하여 사용자가 선택하도록 한다:

1. 프로젝트 멤버 목록과 라벨 목록을 **병렬로** 조회한다:
   ```
   gh api 'repos/{owner}/{repo}/assignees' --paginate
   gh api 'repos/{owner}/{repo}/labels' --paginate
   ```
   (`{owner}`/`{repo}` 는 gh 가 현재 레포에서 자동 해석한다)
2. 멤버: bot 계정을 제외하고, `login` 을 정리하여 선택지로 제공한다
3. AskUserQuestion으로 assignee를 선택하게 한다 (선택지 최대 4개 + 기타)
4. AskUserQuestion으로 reviewer를 선택하게 한다 (선택지 최대 4개 + 기타, "없음" 포함)
5. AskUserQuestion으로 label을 선택하게 한다 (선택지 최대 4개 + 기타, "없음" 포함, multiSelect: true)

#### 일반 모드

**설정 로드**(`## 절차` 위 섹션)에서 이미 읽어둔 `git-workflow` 섹션 값을 쓴다. 여기서 처음
읽지 않는다 — 2-1단계에서 worktree 를 만든 뒤라 상대 표기가 worktree 로 해석될 수 있다.

- `-a`/`--assignee`가 지정되었으면 해당 username을 사용한다
- 지정되지 않았으면 `.claude/plugins.json`의 `git-workflow.defaultAssignee`를 사용한다. 설정이 없으면 AskUserQuestion으로 질문한다
- `-r`/`--reviewer`가 지정되었으면 해당 username을 사용한다
- 지정되지 않았으면 `.claude/plugins.json`의 `git-workflow.defaultReviewer`를 사용한다. 설정이 없으면 AskUserQuestion으로 질문한다
- `-l`/`--label`이 지정되었으면 해당 라벨을 사용한다 (쉼표 구분으로 복수 가능)
- 지정되지 않았으면 `.claude/plugins.json`의 `git-workflow.defaultLabels`를 사용한다. 설정이 없으면 AskUserQuestion으로 질문한다
- **모듈 라벨 자동 판단**: `.claude/plugins.json`의 `git-workflow.moduleRoot` 설정값을 기준으로 변경된 모듈명을 추출하여 라벨로 자동 추가한다
  - `moduleRoot`가 설정되어 있을 때만 동작한다. 미설정이면 모듈 라벨과 ROOT 라벨 모두 스킵한다
  - 모듈명 추출 명령: `git diff <base-branch>...<source> --name-only | sed -n "s|^${moduleRoot}/\([^/]*\)/.*|\1|p" | sort -u`
  - 매치된 모듈명을 라벨에 추가 (예: `moduleRoot=apps`, `apps/api/src/...` 변경 시 → `api` 라벨 추가)
  - 복수 모듈이 변경되었으면 각각 추가 (예: `D-5,api,checkout`)
  - `${moduleRoot}/` 밖의 파일이 변경되었으면 `ROOT` 라벨을 추가한다
    - 확인 명령: `git diff <base-branch>...<source> --name-only | grep -v "^${moduleRoot}/" | head -1`
    - 매치되면 라벨에 `ROOT`를 추가 (예: `D-5,api,ROOT`)
- **AI 라벨 자동 판단**: 대상 커밋 중 `Co-Authored-By: Claude`가 포함된 커밋이 있으면 `AI` 라벨을 자동 추가한다
  - 확인 명령: `git log <base-branch>..<source> --format=%b | grep -q "Co-Authored-By: Claude"`
  - 매치되면 라벨에 `AI`를 추가 (예: `D-5,AI`)
- **라벨 대문자 변환**: 위 과정에서 수집된 모든 라벨을 대문자로 변환한다 (예: `api` → `API`, `d-5` → `D-5`, `root` → `ROOT`)

### 7. 리모트 push 확인

```bash
# 소스 브랜치의 upstream 확인
git rev-parse --abbrev-ref <source>@{u}
```

- upstream이 설정되지 않았거나 로컬이 리모트보다 앞서 있으면 push 여부를 사용자에게 확인한다
- 확인 후 `git push -u origin <source>` 실행

### 8. PR 생성

```
gh pr create --title "<제목>" --body "<설명>" --head <source> --base <target-branch> --assignee <assignee> [--reviewer <reviewer>] [--label <label>]
```

- `--head`로 소스 브랜치를 명시한다 (`--source` 미지정 시 현재 브랜치)
- 머지 시 소스 브랜치 자동 삭제는 PR 옵션이 아니라 **저장소 설정**이다 — 미설정이면 1회만 실행: `gh api -X PATCH 'repos/{owner}/{repo}' -F delete_branch_on_merge=true`
- squash 여부는 머지 시점에 정한다 — 커밋 이력 보존을 위해 merge commit 방식을 기본으로 안내한다
- `--title`/`--body` 를 모두 지정하므로 에디터가 열리지 않는다
- label 은 저장소에 존재해야 한다 — 없다는 에러가 나면 `gh label create <이름>` 후 재시도한다
- assignee는 항상 포함 (`.claude/plugins.json` 기본값 또는 사용자 지정)
- reviewer는 항상 포함 (`.claude/plugins.json` 기본값 또는 `-r` 옵션으로 오버라이드 가능)
- label은 항상 포함 (기본값: `D-5`, `-l` 옵션으로 오버라이드 가능)

### 9. 결과 출력

- 생성된 PR의 URL을 출력한다
- `gh pr view --web` 안내를 함께 제공한다

### 10. Worktree 정리 (`--source` 사용 시)

```bash
git worktree remove /tmp/wt-create-pr
```

- PR 생성 성공/실패에 관계없이 반드시 정리한다

## 주의사항

- PR 제목과 설명은 반드시 한글로 작성한다
- 민감한 정보(토큰, 비밀번호 등)가 출력되지 않도록 주의한다
- push 전에 반드시 사용자 확인을 받는다
- PR 생성 전에 제목과 설명을 사용자에게 보여주고 확인을 받는다

## plugins.json 설정 권고 (작업 후)
이번 실행에서 AskUserQuestion 으로 받은 값이 있었다면, 작업 완료 후
[../../reference/config-recommendation.md](../../reference/config-recommendation.md) 의 출력 포맷대로
안내 블록을 출력한다. 모든 값을 plugins.json 에서 얻었으면 생략한다.

**권고 대상:**
- **포함**: AskUserQuestion 으로 받은 값 (다음부터 자동 처리되려면 plugins.json 에 저장 필요). 예: `defaultAssignee`, `defaultReviewer`, `defaultLabels`, `moduleRoot`, `project`
- **제외**: CLI 인자로 받은 값(`-a`, `-r`, `-l`, `--target`, `--source`, `--base`), AI 가 자동 판단한 값(모듈 라벨 자동 추가, AI 라벨 자동 추가, 자동 감지된 타겟 브랜치, MR 제목/설명 본문)

