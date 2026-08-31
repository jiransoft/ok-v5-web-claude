---
name: setup
description: release-tools를 사용할 수 있도록 .claude/plugins.json의 release-tools 섹션을 생성/병합하고, git remote에서 project를, 레포 구조에서 modules를 자동 유추하며, 기존 git-workflow 섹션의 값 이전도 처리하는 셋업 스킬.
when_to_use: 사용자가 "release-tools 셋업", "release-tools setup", "릴리즈 노트 설정해줘", "release-note 설정 만들어줘" 등을 요청하거나, release-tools 설치 직후 설정이 필요할 때 사용한다.
argument-hint: "[--help]"
allowed-tools: Read, Write, Edit, Bash(git *), Bash(gh *), Bash(command *), Bash(grep *), Bash(ls *), Bash(cat *), Bash(printf *), AskUserQuestion
---

# release-tools 셋업

release-tools 스킬(release-note)이 읽는 `.claude/plugins.json`의 `release-tools` 섹션을 준비한다. 재실행 안전(idempotent).

## --help 처리

`$ARGUMENTS`가 `--help`/`-h`이면 아래만 출력하고 종료:

```
/release-tools:setup — release-tools 설정 마법사
  .claude/plugins.json 의 release-tools 섹션 생성/병합, .gitignore 등록, gh CLI 확인.
  git remote 에서 project(owner/repo), 레포 구조에서 modules 를 자동 유추한다.
  기존 git-workflow 섹션에 swaggerBaseUrl·modules 가 있으면 이전을 제안한다.
```

## 실행 절차

### 1. 현재 설정 점검
- `.claude/plugins.json`을 Read. `release-tools` 섹션 있으면 값 보여주고 "유지/수정/새로작성" 선택. 없으면 병합.
- `release-tools` 섹션이 없는데 `git-workflow` 섹션에 `swaggerBaseUrl`·`modules`가 있으면 — release-note 가 git-workflow 소속이던 시절(≤0.1.0, GitLab 기반)의 설정이다 — 그 값을 `release-tools` 섹션으로 복사할지 확인받는다 (기본: 복사. git-workflow 쪽 원본은 지우지 않는다). `project` 는 GitLab 경로라 이전하지 않는다 — 2-1에서 새로 유추한다.

### 2-1. 레포에서 자동 유추 (먼저 수행)

```bash
git remote get-url origin        # → project 경로 파싱(owner/repo)
ls -d */ | head                  # → modules 후보(top dirs)
```

- `project` ← origin URL에서 `owner/repo` 추출(`.git` 제거, ssh/https 모두 처리). GitHub remote 가 아니면(아직 GitLab 등) 값을 비워두고, GitHub 이관 후 재실행을 안내한다.
- `modules` ← 모노레포면 `apps/`·`packages/` 같은 최상위 디렉터리 구조를 보고 prefix→모듈명 매핑 초안 제시(사용자 확인).

### 2-2. 나머지 값 입력받기
`AskUserQuestion`으로 받는다(전부 선택키 — 비워도 동작):
- **`swaggerBaseUrl`**: 릴리즈 노트의 API Swagger 링크 베이스(자동 유추 불가 — 알면 입력).

### 3. plugins.json 작성/병합

> 대상은 **본체 레포 루트의 `.claude/plugins.json`** 이다. worktree 안에서 실행 중이면
> worktree 가 아니라 본체에 써야 한다 — worktree 에 쓰면 설정이 worktree 제거와 함께
> 사라져 "셋업했는데 다음에 또 묻는" 상태가 된다. 본체 루트는 이렇게 구한다:
> ```bash
> gcd=$(git rev-parse --git-common-dir); case $gcd in /*) ;; *) gcd=$PWD/$gcd ;; esac
> root=$(cd "$gcd/.." && pwd -P)   # → $root/.claude/plugins.json
> ```

병합 시 다른 플러그인 섹션과 이 셋업이 다루지 않는 기존 키는 그대로 보존한다. "새로작성"을 선택해도 사라질 키를 먼저 보여주고 확인받는다.

```jsonc
{
  "release-tools": {
    "project": "owner/repo",
    "swaggerBaseUrl": "https://api.example.com/swagger-ui/index.html",
    "modules": { "apps/api/": "API", "apps/admin/": "Admin" }
  }
}
```

### 4. gitignore 등록
```bash
# .gitignore 는 본체 레포 것을 고친다. worktree 안에서 실행되면 worktree 의
# 트래킹된 .gitignore 에 써서 작업 브랜치를 오염시킨다.
gcd=$(git rev-parse --git-common-dir); case $gcd in /*) ;; *) gcd=$PWD/$gcd ;; esac
root=$(cd "$gcd/.." && pwd -P)
grep -qxF '.claude/plugins.json' "$root/.gitignore" 2>/dev/null || echo '.claude/plugins.json' >> "$root/.gitignore"
```

### 5. gh CLI 안내
release-note 는 `gh` CLI(`gh release view`·`create`·`edit`)를 쓴다. `command -v gh` 와 `gh auth status` 로
설치·인증을 확인하고, 안 되어 있으면 `brew install gh` → `gh auth login` 을 안내한다 (실행은 사용자 몫).

### 6. 요약 보고
plugins.json 경로·생성/병합, 유추된 project/modules, (했다면) git-workflow 값 이전 결과, gitignore 등록을 요약한다. "이제 `릴리즈 노트 만들어줘`로 사용하세요" 안내.
