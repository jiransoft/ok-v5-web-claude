---
name: setup
description: code-review-suite를 사용할 수 있도록 .claude/plugins.json의 code-review-suite 섹션(techStack)을 생성/병합하는 셋업 스킬. 레포의 빌드/매니페스트 파일을 스캔해 techStack을 자동 감지해 채운다.
when_to_use: 사용자가 "code-review 셋업", "code review setup", "코드리뷰 설정해줘", "리뷰 스택 설정", "code-review-suite 설정" 등을 요청하거나, code-review-suite 설치 직후 설정이 필요할 때 사용한다.
argument-hint: "[--help]"
allowed-tools: Read, Write, Edit, Bash(grep *), Bash(ls *), AskUserQuestion
---

# code-review-suite 셋업

code-review-suite가 읽는 `.claude/plugins.json`의 `code-review-suite` 섹션을 준비한다. 설정은 `techStack`(선택) 하나뿐이고 크리덴셜이 없어, **레포에서 스택을 자동 감지**하는 게 핵심이다. 재실행 안전(idempotent).

## --help 처리

`$ARGUMENTS`가 `--help`/`-h`이면 아래만 출력하고 종료:

```
/code-review-suite:setup — code-review-suite 설정 마법사
  .claude/plugins.json 의 code-review-suite 섹션(techStack) 생성/병합.
  레포의 빌드/매니페스트 파일을 스캔해 techStack 을 자동 감지한다.
```

## 실행 절차

### 1. 현재 설정 점검
- `.claude/plugins.json`을 Read. `code-review-suite` 섹션 있으면 값 보여주고 "유지/수정" 선택. 없으면 병합.

### 2. techStack 자동 감지
레포 루트의 매니페스트/빌드 파일을 스캔해 스택을 추론한다.

```bash
ls package.json tsconfig.json build.gradle build.gradle.kts pom.xml go.mod Cargo.toml \
   requirements.txt pyproject.toml composer.json Gemfile 2>/dev/null
```

- 매핑 예: `build.gradle(.kts)`/`pom.xml`→Java/Kotlin/Spring Boot, `package.json`+`tsconfig.json`→TypeScript/Node, `go.mod`→Go, `Cargo.toml`→Rust, `pyproject.toml`/`requirements.txt`→Python.
- 감지 결과를 `AskUserQuestion`으로 보여주고 확인/보정받는다. 모노레포면 복수 스택 허용.

### 3. plugins.json 작성/병합

> 대상은 **본체 레포 루트의 `.claude/plugins.json`** 이다. worktree 안에서 실행 중이면
> worktree 가 아니라 본체에 써야 한다 — worktree 에 쓰면 설정이 worktree 제거와 함께
> 사라져 "셋업했는데 다음에 또 묻는" 상태가 된다. 본체 루트는 이렇게 구한다:
> ```bash
> gcd=$(git rev-parse --git-common-dir); case $gcd in /*) ;; *) gcd=$PWD/$gcd ;; esac
> root=$(cd "$gcd/.." && pwd -P)   # → $root/.claude/plugins.json
> ```

```json
{
  "code-review-suite": {
    "techStack": ["Java", "Spring Boot", "Kotlin"]
  }
}
```

> `techStack`은 선택이다 — 비워도 리뷰는 동작하며, 지정하면 리뷰어가 스택 관용구에 맞춰 더 정확히 본다.

### 4. gitignore 등록
```bash
# .gitignore 는 본체 레포 것을 고친다. worktree 안에서 실행되면 worktree 의
# 트래킹된 .gitignore 에 써서 작업 브랜치를 오염시킨다.
gcd=$(git rev-parse --git-common-dir); case $gcd in /*) ;; *) gcd=$PWD/$gcd ;; esac
root=$(cd "$gcd/.." && pwd -P)
grep -qxF '.claude/plugins.json' "$root/.gitignore" 2>/dev/null || echo '.claude/plugins.json' >> "$root/.gitignore"
```

### 5. 요약 보고
plugins.json 경로·생성/병합, 자동 감지된 techStack을 요약. "이제 `코드리뷰`로 변경사항을 리뷰하세요" 안내.
