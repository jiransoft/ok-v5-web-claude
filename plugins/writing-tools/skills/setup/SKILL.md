---
name: setup
description: writing-tools 의 flex-style 이 기술 글 작성 요청에 확정적으로 적용되도록, 사용자 전역 ~/.claude/CLAUDE.md(또는 --project 로 본체 레포의 CLAUDE.md)에 마커로 감싼 지시 블록을 추가·갱신·제거하는 셋업 스킬. .claude/plugins.json 설정은 만들지 않는다.
when_to_use: 사용자가 "writing-tools 셋업", "writing-tools setup", "플렉스 스타일 기본으로 켜줘", "기술 글 쓸 때 flex-style 자동 적용되게 해줘", "flex-style 기본 적용 꺼줘" 등을 요청하거나, writing-tools 설치 직후 기본 적용 설정이 필요할 때 사용한다.
argument-hint: "[--project] [--remove] [--help]"
allowed-tools: Read, Write, Edit, Bash(git *), Bash(mkdir *), Bash(ls *), AskUserQuestion
---

# writing-tools 셋업

flex-style 스킬은 설치만 해도 `when_to_use` 매칭으로 자동 호출되지만, 그 매칭은 확률적이다. 이 셋업은 CLAUDE.md 에 지시 블록 하나를 넣어 기술 글 요청에 확정적으로 적용되게 한다. 재실행 안전(idempotent). 같은 마커 블록이 있으면 교체한다.

## --help 처리

`$ARGUMENTS`가 `--help`/`-h`이면 아래만 출력하고 종료:

```
/writing-tools:setup — flex-style 기본 적용 설정
  ~/.claude/CLAUDE.md 끝에 <!-- writing-tools:flex-style start/end --> 마커로 감싼 지시 블록을 추가/갱신한다.
  --project   현재 본체 레포의 CLAUDE.md 에 넣는다 (git 으로 팀 공유, 커밋은 사용자 몫)
  --remove    넣어둔 블록을 제거한다
  재실행 안전. 다른 내용은 건드리지 않는다.
```

## 절차

### 1. 대상 파일 결정

- 기본은 `~/.claude/CLAUDE.md` 다. 설치한 사람에게만 적용되는 전역 설정이다.
- `--project` 면 **본체 레포 루트의** `CLAUDE.md` 다. worktree 안에서 실행 중일 수 있으니 루트는 아래로 구한다.
  ```bash
  gcd=$(git rev-parse --git-common-dir); case $gcd in /*) ;; *) gcd=$PWD/$gcd ;; esac
  root=$(cd "$gcd/.." && pwd -P)   # → $root/CLAUDE.md
  ```
  git 레포가 아니면 에러를 알리고 종료한다.
- `--project` 도 `--remove` 도 없으면 AskUserQuestion 으로 "전역(추천) / 프로젝트" 중 하나를 고르게 한다. 프로젝트를 고르면 팀원 전체에 적용되고 커밋 대상이 된다는 점을 선택지 설명에 적는다.

### 2. 현재 상태 점검

- 대상 파일을 Read 한다. 없으면 빈 파일로 간주한다(전역이면 `mkdir -p ~/.claude` 후 새로 만든다).
- `<!-- writing-tools:flex-style start -->` 와 `<!-- writing-tools:flex-style end -->` 한 쌍이 있으면 "갱신", 없으면 "추가"다.
- `--remove` 면 그 블록(start 마커 줄부터 end 마커 줄의 줄바꿈까지)과 그 바로 앞의 빈 줄 하나만 지우고 5단계로 간다. end 마커 뒤에 있는 내용과 파일 끝 개행은 건드리지 않는다. **제거 후 파일은 블록을 넣기 전과 바이트 단위로 같아야 한다.** 블록이 없으면 "제거할 블록 없음"으로 보고하고 종료한다.
- 반대쪽 파일(전역이면 본체 레포 `CLAUDE.md`, 프로젝트면 `~/.claude/CLAUDE.md`)에도 같은 마커가 있는지 Read 로 확인해 두고 6단계에서 알린다. 양쪽에 있어도 해롭지는 않지만 사용자가 알아야 한다.

### 3. 지시 블록

아래 블록을 그대로 쓴다. 문구를 임의로 바꾸지 않는다. 적용 범위와 제외 범위가 이 블록의 전부다.

```markdown
<!-- writing-tools:flex-style start -->
## 기술 글 작성 규칙 (writing-tools)

기술 블로그 글, 기술 회고, 아키텍처·설계 설명 글을 새로 쓰거나 다듬어 달라는 요청에는 먼저 `/writing-tools:flex-style` 스킬을 호출해 그 규칙으로 작성한다.
릴리즈 노트, Jira 댓글, 회의록, 커밋 메시지, PR 본문, API 문서에는 적용하지 않는다.
<!-- writing-tools:flex-style end -->
```

### 4. 쓰기

- "추가"면 파일 끝에 빈 줄 하나를 두고 블록을 붙인다(Edit 또는 Write). 파일이 개행으로 끝나지 않으면 먼저 개행을 붙인 뒤 빈 줄과 블록을 더한다. 블록은 개행으로 끝낸다.
- "갱신"이면 기존 start 마커 줄부터 end 마커 줄까지만 위 블록으로 교체한다(Edit). 마커 밖의 빈 줄과 공백은 그대로 둔다.
- 블록 밖의 기존 내용은 한 글자도 바꾸지 않는다.
- `--project` 면 `git status --short CLAUDE.md` 로 변경을 보여준다. 커밋은 하지 않는다.

### 5. 검증

- 대상 파일을 다시 Read 해 start 마커와 end 마커가 각각 정확히 한 번씩 있는지 확인한다(`--remove` 면 0번).
- 두 번 이상이면 첫 쌍만 남기고 나머지를 지운 뒤 다시 Read 해 확인한다. 세 번째 시도에도 어긋나면 멈추고 파일 상태를 그대로 보고한다.

### 6. 요약 보고

- 대상 경로, 추가/갱신/제거 중 무엇을 했는지, 적용 범위(전역/프로젝트), 반대쪽 파일에 블록이 있었는지를 요약한다.
- 안내 문구: "새 세션부터 적용됩니다. 지금 세션에서 바로 쓰려면 `/writing-tools:flex-style` 로 직접 호출하세요."

## 주의사항

- 이 플러그인은 `.claude/plugins.json` 설정이 없다. plugins.json 을 만들거나 건드리지 않는다.
- CLAUDE.md 는 사용자의 다른 규칙이 함께 있는 파일이다. 마커 밖은 읽기만 하고 쓰지 않는다.
- `--project` 로 넣은 블록은 팀원 전체의 세션에 실린다. 팀 합의 없이 넣지 않도록 선택지 설명에 명시한다.
