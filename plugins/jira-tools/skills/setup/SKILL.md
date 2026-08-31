---
name: setup
description: jira-tools를 사용할 수 있도록 .claude/plugins.json의 jira-tools 섹션을 생성/병합하고, API 토큰 파일을 준비한 뒤 Jira REST API로 issueType·component·customField ID와 Cloud ID를 자동 조회해 채워주는 셋업 스킬.
when_to_use: 사용자가 "jira 셋업", "jira setup", "jira-tools 설정해줘", "지라 설정 만들어줘", "지라 연결 설정" 등을 요청하거나, jira-tools 설치 직후 설정이 필요할 때 사용한다.
argument-hint: "[--help] [--test]"
allowed-tools: Read, Write, Edit, Bash(cat *), Bash(chmod *), Bash(curl *), Bash(grep *), Bash(jq *), Bash(printf *), AskUserQuestion
---

# jira-tools 셋업

jira-tools 스킬들이 읽는 `.claude/plugins.json`의 `jira-tools` 섹션과 토큰 파일을 준비한다. 재실행 안전(idempotent) — 기존 값은 병합하고, 덮어쓰기 전 확인한다.

## --help 처리

`$ARGUMENTS`가 `--help`/`-h`이면 아래만 출력하고 종료:

```
/jira-tools:setup — jira-tools 설정 마법사
  .claude/plugins.json 의 jira-tools 섹션 생성/병합, ~/.jira-token 안내, .gitignore 등록.
  Jira REST API로 issueTypes·components·customFields·Cloud ID를 자동 조회한다.
  --test 를 주면 인증/프로젝트 접근까지 검증한다.
```

## 실행 절차

### 1. 현재 설정 점검
- `.claude/plugins.json`을 Read. `jira-tools` 섹션이 있으면 값을 보여주고 "유지/수정/새로작성" 선택(`AskUserQuestion`). 없으면 다른 섹션 보존하며 병합.
- `~/.jira-token` 존재·권한(600) 확인(내용은 출력하지 않음).

### 2. 사람이 아는 값 입력받기
`AskUserQuestion`으로 받는다:
- **`baseUrl`**: Jira 사이트(예: `https://your-domain.atlassian.net`).
- **`email`**: 계정 이메일.
- **`projectKey`**: 기본 프로젝트 키(예: `OKEP`).
- 이미 셋업된 상태에서 **다른 프로젝트를 추가**하려는 요청이면(예: "ABC 프로젝트 추가"), 기존
  섹션은 그대로 두고 2-1 조회를 그 프로젝트 키로 수행해 `projects.<키>` 서브섹션으로 병합한다
  (issueTypes·components·customFields·assignee 만 — 인증·baseUrl 은 사이트 공통이라 중복 저장하지 않는다).
- **`assignee`**: 기본 담당자(선택).

> `issueTypes`·`components`·`customFields`·Cloud ID는 **묻지 않는다** — 사람이 외우는 값이 아니므로 2-1절에서 API로 자동 조회한다.

### 2-1. ID 자동 조회 (Jira REST API)
`~/.jira-token`과 `email`로 Basic 인증 헤더를 만들어 아래를 호출하고, 결과로 섹션을 채운다.

```bash
AUTH=$(printf '%s:%s' "<email>" "$(cat ~/.jira-token)" | base64)
# Cloud ID
curl -s "https://<site>.atlassian.net/_edge/tenant_info"            # → {cloudId}
# 프로젝트 + 컴포넌트
curl -s -H "Authorization: Basic $AUTH" "<baseUrl>/rest/api/3/project/<projectKey>"        # → id, components[]{id,name}
# issueType + customField(프로젝트 스코프)
curl -s -H "Authorization: Basic $AUTH" "<baseUrl>/rest/api/3/issue/createmeta?projectKeys=<projectKey>&expand=projects.issuetypes.fields"
# 전체 필드(커스텀 필드 ID 확인용)
curl -s -H "Authorization: Basic $AUTH" "<baseUrl>/rest/api/3/field"
```

- `issueTypes` ← createmeta의 `projects[].issuetypes[]{name→id}`.
- `components` ← project의 `components[]{name→id}`.
- `customFields` ← `/field`에서 필요한 커스텀 필드(예: issueCategory)의 `customfield_xxxxx` id, 허용값은 createmeta의 `allowedValues`에서.
- 인증 실패(401)·프로젝트 없음(404)이면 중단하고 사용자에게 보고(토큰/이메일/키 확인).

### 3. plugins.json 작성/병합

> 대상은 **본체 레포 루트의 `.claude/plugins.json`** 이다. worktree 안에서 실행 중이면
> worktree 가 아니라 본체에 써야 한다 — worktree 에 쓰면 설정이 worktree 제거와 함께
> 사라져 "셋업했는데 다음에 또 묻는" 상태가 된다. 본체 루트는 이렇게 구한다:
> ```bash
> gcd=$(git rev-parse --git-common-dir); case $gcd in /*) ;; *) gcd=$PWD/$gcd ;; esac
> root=$(cd "$gcd/.." && pwd -P)   # → $root/.claude/plugins.json
> ```

`jira-tools` 섹션을 병합해 Write(다른 섹션 보존, JSON 유효성 유지):

```json
{
  "jira-tools": {
    "projectKey": "OKEP",
    "baseUrl": "https://your-domain.atlassian.net",
    "email": "you@example.com",
    "apiTokenFile": "~/.jira-token",
    "cloudId": "<자동조회>",
    "assignee": "username",
    "issueTypes": { "결함": "10004", "작업": "10002" },
    "components": { "Backend": "10001" },
    "customFields": { "issueCategory": { "fieldId": "customfield_10038", "value": { "id": "10022" } } },
    "projects": { "ABC": { "issueTypes": { "작업": "10012" }, "components": { "Web": "10201" } } }
  }
}
```

`projects` 는 같은 사이트의 **추가 프로젝트**를 쓸 때만 넣는다 — "프로젝트 추가" 요청 시 2-1 조회로 채운다.

> ⚠️ 토큰은 **plugins.json에 넣지 않는다** — `apiTokenFile` 경로로만 둔다.

### 4. 토큰 파일 안내
`~/.jira-token`이 없으면, 값을 받아 기록하지 말고 발급·생성 명령을 안내한다:

```bash
# https://id.atlassian.com/manage-profile/security/api-tokens 에서 발급
echo "ATATT3xF..." > ~/.jira-token && chmod 600 ~/.jira-token
```

### 5. gitignore 등록
```bash
# .gitignore 는 본체 레포 것을 고친다. worktree 안에서 실행되면 worktree 의
# 트래킹된 .gitignore 에 써서 작업 브랜치를 오염시킨다.
gcd=$(git rev-parse --git-common-dir); case $gcd in /*) ;; *) gcd=$PWD/$gcd ;; esac
root=$(cd "$gcd/.." && pwd -P)
grep -qxF '.claude/plugins.json' "$root/.gitignore" 2>/dev/null || echo '.claude/plugins.json' >> "$root/.gitignore"
```

### 6. (선택) 검증 — `--test`
`--test`면 `GET /rest/api/3/myself`로 인증을, `GET /rest/api/3/project/<key>`로 프로젝트 접근을 확인하고 결과만 보고(이슈 생성·변경 없음).

### 7. 요약 보고
plugins.json 경로·생성/병합, 토큰 파일 상태, 자동 조회된 ID 개수(issueTypes n·components m·customFields k), gitignore 등록, (했다면) 검증 결과를 요약. "이제 `jira 이슈 만들어줘`로 사용하세요" 안내.
