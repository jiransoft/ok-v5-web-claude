---
name: setup
description: runtime-verify를 사용할 수 있도록 .claude/plugins.json의 runtime-verify 섹션(modules·projectKey·credentialsFile 등)을 생성/병합하는 셋업 스킬. 레포 구조를 스캔해 모듈 후보를 제안하고 포트 슬롯 설계를 도와준다.
when_to_use: 사용자가 "runtime-verify 셋업", "verify-stack 설정", "이슈 검증 스택 설정해줘", "runtime verify setup" 등을 요청하거나, runtime-verify 설치 직후 설정이 필요할 때 사용한다.
argument-hint: "[--help]"
allowed-tools: Read, Write, Edit, Bash(git *), Bash(grep *), Bash(ls *), AskUserQuestion
---

# runtime-verify 셋업

verify-stack이 읽는 `.claude/plugins.json`의 `runtime-verify` 섹션을 준비한다. 핵심은 `modules`(기동 명령·헬스체크·포트 슬롯) 설계다. 재실행 안전(idempotent).

## --help 처리

`$ARGUMENTS`가 `--help`/`-h`이면 아래만 출력하고 종료:

```
/runtime-verify:setup — runtime-verify 설정 마법사
  .claude/plugins.json 의 runtime-verify 섹션 생성/병합.
  레포 구조를 스캔해 모듈 후보를 제안하고 포트 슬롯 설계를 돕는다.
```

## 실행 절차

### 1. 현재 설정 점검

`.claude/plugins.json`을 Read. `runtime-verify` 섹션이 있으면 값을 보여주고 "유지/수정"을 선택받는다. 없으면 새로 만들어 병합한다.

### 2. 모듈 후보 스캔

레포에서 기동 가능한 모듈을 찾는다:

```bash
ls apps 2>/dev/null; ls */build.gradle* */package.json 2>/dev/null
```

- Gradle 모듈(`build.gradle*`) → `./gradlew bootRun` 계열, 포트 인자 후보: `--server.port`·`--management.server.port`·gRPC 인자
- Node 모듈(`package.json`의 dev 스크립트) → `npm run dev -- -p {sN}` 계열
- 감지 결과를 AskUserQuestion으로 보여주고 모듈 구성·슬롯 배치를 확정한다. 슬롯 설계 기준은 [verify-stack의 config-example](../verify-stack/reference/config-example.md)을 따른다 — **슬롯 0은 다른 모듈이 참조할 대표 포트**로 둔다

### 3. 나머지 키 인터뷰

- `projectKey`: `jira-tools.projects` 의 키가 1개면 그 값을 기본 제안
- `credentialsFile`: UI 로그인 계정 파일(`id:pw` 한 줄). 민감 값 자체를 plugins.json에 넣지 않는다
- `portBase`(기본 10000)·`worktreeBase`(기본 /tmp)는 기본값 사용 여부만 확인
- `ui`: 브라우저 검증 진입 모듈·슬롯·로그인 경로
- `prepare`: fresh worktree 준비 명령 (의존성 설치, gitignore된 로컬 설정 복사 — `$MAIN`은 본체 루트로 치환됨)

### 4. plugins.json 작성/병합

> 대상은 **본체 레포 루트의 `.claude/plugins.json`** 이다. worktree 안에서 실행 중이면 본체에 써야 한다. 본체 루트는 이렇게 구한다:
> ```bash
> gcd=$(git rev-parse --git-common-dir); case $gcd in /*) ;; *) gcd=$PWD/$gcd ;; esac
> root=$(cd "$gcd/.." && pwd -P)   # → $root/.claude/plugins.json
> ```

```json
{
  "runtime-verify": {
    "projectKey": "PROJ",
    "credentialsFile": "~/.admin-credentials",
    "portBase": 10000,
    "worktreeBase": "/tmp",
    "modules": [
      {
        "name": "api",
        "dir": "apps/api",
        "start": "./gradlew bootRun --args=\"--server.port={s0} --management.server.port={s1} --spring.profiles.active=local\"",
        "health": { "url": "http://localhost:{s1}/actuator/health", "expect": "200" }
      }
    ],
    "ui": { "module": "site", "slot": 2, "signinPath": "/signin" },
    "prepare": ["npm --prefix apps/site install", "cp $MAIN/apps/site/.env apps/site/.env"]
  }
}
```

### 5. gitignore 등록

```bash
# .gitignore 는 본체 레포 것을 고친다 (worktree 오염 방지)
gcd=$(git rev-parse --git-common-dir); case $gcd in /*) ;; *) gcd=$PWD/$gcd ;; esac
root=$(cd "$gcd/.." && pwd -P)
grep -qxF '.claude/plugins.json' "$root/.gitignore" 2>/dev/null || echo '.claude/plugins.json' >> "$root/.gitignore"
```

### 6. 요약 보고

plugins.json 경로·생성/병합 여부, 확정된 모듈·슬롯 구성을 요약한다. "이제 `/verify-stack <이슈키>`로 검증 스택을 띄우세요" 안내.
