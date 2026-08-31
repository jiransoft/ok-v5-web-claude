---
name: setup
description: git-workflow를 사용할 수 있도록 .claude/plugins.json의 git-workflow 섹션을 생성/병합하고, git remote에서 project(owner/repo)를, 레포 구조에서 moduleRoot를 자동 유추하며 gh 인증을 점검하는 셋업 스킬.
when_to_use: 사용자가 "github 셋업", "github setup", "git-workflow 설정해줘", "깃헙 설정 만들어줘", "PR 워크플로우 설정" 등을 요청하거나, git-workflow 설치 직후 설정이 필요할 때 사용한다.
argument-hint: "[--help] [--test]"
allowed-tools: Read, Write, Edit, Bash(git *), Bash(gh *), Bash(chmod *), Bash(grep *), Bash(ls *), Bash(cat *), Bash(printf *), Bash(command *), AskUserQuestion
---

# git-workflow 셋업

git-workflow 스킬들(create-pr·commit)이 읽는 `.claude/plugins.json`의 `git-workflow` 섹션과 gh 인증을 준비한다. 재실행 안전(idempotent).

## --help 처리

`$ARGUMENTS`가 `--help`/`-h`이면 아래만 출력하고 종료:

```
/git-workflow:setup — git-workflow 설정 마법사
  .claude/plugins.json 의 git-workflow 섹션 생성/병합, gh 인증 점검, .gitignore 등록.
  git remote 에서 project(owner/repo), 레포 구조에서 moduleRoot 를 자동 유추한다.
  --test 를 주면 gh 인증/저장소 접근까지 검증한다.
```

## 실행 절차

### 1. 현재 설정 점검
- `.claude/plugins.json`을 Read. `git-workflow` 섹션 있으면 값 보여주고 "유지/수정/새로작성" 선택. 없으면 병합.
- `gh auth status` 로 인증 상태 확인.

### 2-1. 레포에서 자동 유추 (먼저 수행)
대부분 값은 묻기 전에 레포에서 유추한다.

```bash
git remote get-url origin                                   # → project 경로 파싱(host/group/project)
git config user.name; git config user.email                 # → defaultAssignee 후보
ls -d */ | head                                             # → moduleRoot 후보(top dirs)
command -v gh && gh api user -q .login 2>/dev/null          # 인증돼 있으면 username
```

- `project` ← origin URL에서 `owner/repo` 추출(`.git` 제거, ssh/https 모두 처리).
- `moduleRoot` ← 모노레포면 `apps/`·`packages/` 같은 최상위 디렉터리를 후보로 제시(사용자 확인).

### 2-2. 나머지 값 입력받기
`AskUserQuestion`으로 받는다(전부 선택키 — 비워도 동작):
- **`defaultAssignee`**/**`defaultReviewer`**: 기본 담당자/리뷰어(2-1 유추값 디폴트).
- **`defaultLabels`**: 기본 라벨(예: `["D-5"]`).

### 3. plugins.json 작성/병합

> 대상은 **본체 레포 루트의 `.claude/plugins.json`** 이다. worktree 안에서 실행 중이면
> worktree 가 아니라 본체에 써야 한다 — worktree 에 쓰면 설정이 worktree 제거와 함께
> 사라져 "셋업했는데 다음에 또 묻는" 상태가 된다. 본체 루트는 이렇게 구한다:
> ```bash
> gcd=$(git rev-parse --git-common-dir); case $gcd in /*) ;; *) gcd=$PWD/$gcd ;; esac
> root=$(cd "$gcd/.." && pwd -P)   # → $root/.claude/plugins.json
> ```

병합 시 이 셋업이 다루지 않는 기존 키(`commit` 등)는 그대로 보존한다. "새로작성"을 선택해도 사라질 키를 먼저 보여주고 확인받는다.

```jsonc
{
  "git-workflow": {
    "defaultAssignee": "username",
    "defaultReviewer": "username",
    "defaultLabels": ["D-5"],
    "moduleRoot": "apps",
    "project": "owner/repo",
    "commit": { "subjectLanguage": "en", "issueKeyPosition": "suffix" }  // 커밋 컨벤션 오버라이드 — 기본값(ko·prefix)과 다를 때만. 셋업이 묻지 않으므로 필요 시 수동 추가
  }
}
```

### 4. gh 인증 안내
`gh auth status`가 실패하면:

```bash
gh auth login        # 브라우저 로그인 (1회)
```

CI 같은 비대화형 환경에서는 `GH_TOKEN` 환경변수를 쓴다. 이미 인증돼 있으면 이 단계는 생략.

### 5. gitignore 등록
```bash
# .gitignore 는 본체 레포 것을 고친다. worktree 안에서 실행되면 worktree 의
# 트래킹된 .gitignore 에 써서 작업 브랜치를 오염시킨다.
gcd=$(git rev-parse --git-common-dir); case $gcd in /*) ;; *) gcd=$PWD/$gcd ;; esac
root=$(cd "$gcd/.." && pwd -P)
grep -qxF '.claude/plugins.json' "$root/.gitignore" 2>/dev/null || echo '.claude/plugins.json' >> "$root/.gitignore"
```

### 6. (선택) 검증 — `--test`
`--test`면 `gh auth status`와 `gh api repos/<project>`로 저장소 접근을 확인하고 결과만 보고(PR·변경 없음).

### 7. 요약 보고
plugins.json 경로·생성/병합, 유추된 project/moduleRoot, 인증 상태, gitignore 등록, (했다면) 검증 결과 요약. "이제 `PR 만들어줘`로 사용하세요" 안내.
