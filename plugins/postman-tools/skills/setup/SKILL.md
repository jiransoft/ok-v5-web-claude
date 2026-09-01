---
name: setup
description: postman-tools를 사용할 수 있도록 .claude/plugins.json의 postman-tools 섹션을 생성/병합하고, Postman API 키로 워크스페이스·컬렉션을 조회해 workspaceId·collections(별칭→UID)를 구성해주는 셋업 스킬.
when_to_use: 사용자가 "postman 셋업", "postman setup", "postman-tools 설정해줘", "포스트맨 설정 만들어줘", "포스트맨 연결 설정" 등을 요청하거나, postman-tools 설치 직후 설정이 필요할 때 사용한다.
argument-hint: "[--help] [--test]"
allowed-tools: Read, Write, Edit, Bash(curl *), Bash(grep *), Bash(jq *), Bash(printf *), Bash(chmod *), AskUserQuestion
---

# postman-tools 셋업

postman-tools 스킬들이 읽는 `.claude/plugins.json`의 `postman-tools` 섹션을 준비한다. 재실행 안전(idempotent).

## --help 처리

`$ARGUMENTS`가 `--help`/`-h`이면 아래만 출력하고 종료:

```
/postman-tools:setup — postman-tools 설정 마법사
  .claude/plugins.json 의 postman-tools 섹션 생성/병합, .gitignore 등록.
  Postman API 키로 워크스페이스·컬렉션을 조회해 workspaceId/collections(별칭→UID) 를 구성한다.
  --test 를 주면 키 유효성/컬렉션 접근까지 검증한다.
```

## 실행 절차

### 1. 현재 설정 점검
- `.claude/plugins.json`을 Read. `postman-tools` 섹션 있으면 값 보여주고 "유지/수정/새로작성" 선택. 없으면 병합.

### 2. 사람이 아는 값 입력받기
`AskUserQuestion`으로 받는다:
- **`apiKey`**: Postman API Key(`PMAK-...`). 컬렉션 owner와 동일 계정이어야 함.
- **`backendStack`**: 백엔드 스택(선택, 예: `Kotlin Spring Boot`).

> `workspaceId`·`workspaceName`·컬렉션 UID는 **묻지 않는다** — 사람이 외우는 값이 아니므로 2-1절에서 API로 조회해 **목록에서 고르게** 한다 (별칭만 사람이 정한다).

### 2-1. 워크스페이스/컬렉션 자동 조회 & 선택
`apiKey`로 아래를 호출하고, 결과를 `AskUserQuestion`으로 사용자가 고르게 해 ID를 확정한다.

```bash
# 워크스페이스 목록 → 하나 선택 → workspaceId / workspaceName
curl -s "https://api.getpostman.com/workspaces" -H "X-Api-Key: <apiKey>"
# 선택한 워크스페이스의 컬렉션 목록 → 쓸 컬렉션들 선택 + 각각 별칭 지정 → collections(별칭→owner-uuid)
curl -s "https://api.getpostman.com/collections?workspace=<workspaceId>" -H "X-Api-Key: <apiKey>"
```

- `collections` 는 선택(없으면 비워두고 실행 시 `--collection` 으로 지정 가능). 복수 선택 가능하며,
  별칭은 `services` 키와 맞추기를 권장한다 — 서비스명만으로 컬렉션까지 라우팅된다.
- 키 무효(401/403)면 중단하고 보고(API Key/owner 계정 확인).
- `services`(호스트 변수 매핑)는 레포·환경마다 다르니 필요 시 사용자에게 받아 채운다.

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
  "postman-tools": {
    "workspaceId": "<선택값>",
    "workspaceName": "<선택값>",
    "apiKey": "PMAK-...",
    "backendStack": "Kotlin Spring Boot",
    "services": { "api": "{{API-HOST}}" },
    "collections": { "api": "owner-uuid", "checkout": "owner-uuid2" }
  }
}
```

> ⚠️ `apiKey`는 민감값이다. 저장소에 커밋되지 않도록 5절 gitignore를 반드시 적용한다.

### 4. gitignore 등록

별도 토큰 파일은 없다 — `apiKey` 는 `plugins.json` 섹션 안에 보관하므로 파일 자체를 보호한다.
```bash
# .gitignore 는 본체 레포 것을 고친다. worktree 안에서 실행되면 worktree 의
# 트래킹된 .gitignore 에 써서 작업 브랜치를 오염시킨다.
gcd=$(git rev-parse --git-common-dir); case $gcd in /*) ;; *) gcd=$PWD/$gcd ;; esac
root=$(cd "$gcd/.." && pwd -P)
grep -qxF '.claude/plugins.json' "$root/.gitignore" 2>/dev/null || echo '.claude/plugins.json' >> "$root/.gitignore"
```

### 5. (선택) 검증 — `--test`
`--test`면 `GET https://api.getpostman.com/me -H X-Api-Key`로 키 유효성을, `collections` 가 있으면 각 UID 에 `GET /collections/{uid}`로 접근을 확인하고 결과만 보고(변경 없음).

### 6. 요약 보고
plugins.json 경로·생성/병합, 선택된 workspaceId/collections(별칭→UID), gitignore 등록, (했다면) 검증 결과 요약. "이제 `postman request 생성`으로 사용하세요" 안내.
