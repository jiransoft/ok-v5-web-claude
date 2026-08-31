---
name: setup
description: figma-tools를 사용할 수 있도록 .claude/plugins.json의 figma-tools 섹션을 생성/병합하고, Figma personal access token 파일(~/.figma-token)을 준비·검증하며, @멘션 자동화에 필요한 figma 세션 캡처를 선택적으로 안내하는 셋업 스킬.
when_to_use: 사용자가 "figma 셋업", "figma setup", "figma-tools 설정해줘", "피그마 설정 만들어줘", "피그마 연결 설정" 등을 요청하거나, figma-tools 설치 직후 설정이 필요할 때 사용한다.
argument-hint: "[--help] [--test]"
allowed-tools: Read, Write, Edit, Bash(cat *), Bash(chmod *), Bash(curl *), Bash(grep *), Bash(printf *), AskUserQuestion
---

# figma-tools 셋업

figma-tools 스킬(figma-comment)이 읽는 `.claude/plugins.json`의 `figma-tools` 섹션과 토큰 파일을 준비한다. 재실행 안전(idempotent).

## --help 처리

`$ARGUMENTS`가 `--help`/`-h`이면 아래만 출력하고 종료:

```
/figma-tools:setup — figma-tools 설정 마법사
  .claude/plugins.json 의 figma-tools 섹션 생성/병합, ~/.figma-token 안내·검증, .gitignore 등록.
  @멘션 자동화에 필요한 ~/.figma-session 캡처를 선택 안내한다.
```

## 실행 절차

### 1. 현재 설정 점검
- `.claude/plugins.json`을 Read. `figma-tools` 섹션 있으면 값 보여주고 "유지/수정/새로작성" 선택. 없으면 병합.
- `~/.figma-token`·`~/.figma-session` 존재·권한(600) 확인(내용 비출력).

### 2. 값 입력받기
`AskUserQuestion`으로 받는다(선택):
- **`tokenFile`**: PAT 경로(기본 `~/.figma-token`).

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
  "figma-tools": {
    "tokenFile": "~/.figma-token"
  }
}
```

### 4. 토큰 파일 안내·검증
`~/.figma-token`이 없으면 발급·생성 안내:

```bash
# https://www.figma.com/settings → Personal access tokens
echo "figd_..." > ~/.figma-token && chmod 600 ~/.figma-token
```

토큰이 있으면 즉시 유효성 검증:
```bash
curl -s -H "X-Figma-Token: $(cat ~/.figma-token)" https://api.figma.com/v1/me   # → email/handle면 정상, 403이면 토큰 재발급
```

> **@멘션 자동화**: figma-comment의 @멘션은 REST API로 불가해 playwright로 Figma UI를 다룬다. 이때 `~/.figma-session`(로그인 세션) 캡처가 필요하면, 해당 스킬 실행 시 1회 로그인하도록 안내한다(여기선 토큰까지만 준비).

### 5. gitignore 등록
```bash
# .gitignore 는 본체 레포 것을 고친다. worktree 안에서 실행되면 worktree 의
# 트래킹된 .gitignore 에 써서 작업 브랜치를 오염시킨다.
gcd=$(git rev-parse --git-common-dir); case $gcd in /*) ;; *) gcd=$PWD/$gcd ;; esac
root=$(cd "$gcd/.." && pwd -P)
grep -qxF '.claude/plugins.json' "$root/.gitignore" 2>/dev/null || echo '.claude/plugins.json' >> "$root/.gitignore"
```

### 6. 요약 보고
plugins.json 경로·생성/병합, 토큰 파일 상태·검증 결과, gitignore 등록을 요약. "이제 Figma URL과 함께 `코멘트 달아줘`로 사용하세요" 안내.
