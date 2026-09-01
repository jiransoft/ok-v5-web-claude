---
name: create-jira-issue
description: Jira 이슈를 생성합니다. 컨텍스트(설명, 현상 등)를 받아 필드를 자동 결정하고 이슈를 생성합니다
when_to_use: 사용자가 "Jira 이슈 만들어줘", "이슈 생성해줘", "버그 등록", "이거 티켓으로 올려줘", "create jira issue" 등 현상·요구사항 설명과 함께 새 Jira 이슈 등록을 요청할 때.
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/../../scripts/jira-issue.sh *), Bash(curl *), Bash(jq *), Read, Write, AskUserQuestion
argument-hint: "[이슈 설명 또는 컨텍스트]"
---

# Create Jira Issue Skill

컨텍스트(현상 설명, 요구사항 등)를 받아 Jira 이슈를 생성한다.

## --help 처리

`$ARGUMENTS`가 `--help` 또는 `-h` 면 [reference/usage.md](reference/usage.md) 의 사용법 블록을 그대로 출력하고 즉시 종료한다.

## Jira 설정

⚠️ **이 스킬의 모든 작업을 시작하기 전에 반드시 `.claude/plugins.json`을 Read 도구로 읽어야 한다. 이 단계를 건너뛰면 안 된다.**

> 📍 경로는 **본체 레포 루트의 `.claude/plugins.json`** 이다. worktree 경로를 대상으로
> 작업 중이어도 설정은 본체에서 읽는다 — `plugins.json` 은 gitignore 대상이라 worktree 에
> 체크아웃되지 않는다. worktree 에서 찾다 실패하면 설정이 있는데도 CLAUDE.md·질문으로
> 조용히 폴백한다.

설정 우선순위:
1. **Read 도구로 `.claude/plugins.json`** 파일의 `jira-tools` 섹션을 직접 읽는다
2. plugins.json이 없거나 값이 누락되면 **프로젝트의 `CLAUDE.md`**에서 Jira 설정을 찾는다
3. 둘 다 실패하면 **AskUserQuestion으로 사용자에게 입력받는다**

시스템 컨텍스트에 이미 로드된 값을 사용하지 말고, 반드시 Read 도구로 파일을 직접 읽어서 설정을 가져온다.

**필수:**
- **baseUrl** — Atlassian URL (예: `https://xxx.atlassian.net`)
- **email** — Atlassian 계정 이메일 (Basic Auth 용)
- **apiTokenFile** — API 토큰이 저장된 파일 경로 (예: `~/.jira-token`)
- **projects** — 프로젝트 키 → 프로젝트별 설정 맵 (1개 이상)

> **설정 안내:** Atlassian API 토큰은 https://id.atlassian.com/manage-profile/security/api-tokens 에서 발급받아 `~/.jira-token` 파일로 저장한다.

**선택:**
- **cloudId** — Jira Cloud 인스턴스 ID
- `projects.<키>` 안 — **issueTypes**(유형→ID) · **components**(이름→ID) · **customFields**(예: issueCategory) · **assignee**: 있으면 사용, 없으면 생략 또는 질문

```jsonc
"jira-tools": {
  "baseUrl": "...", "email": "...", "apiTokenFile": "~/.jira-token", "cloudId": "...",
  "projects": {
    "OKEP": { "assignee": "...", "issueTypes": { "...": "..." }, "components": { "...": "..." }, "customFields": {} },
    "ABC":  { "issueTypes": { "...": "..." } }
  }
}
```

## 대상 프로젝트 결정

대상 프로젝트는 다음 순서로 정한다:

1. `--project` 인자
2. 대화 컨텍스트의 지시 (예: "ABC 프로젝트에 만들어줘", 이슈 URL/키의 prefix)
3. `projects` 에 프로젝트가 **1개뿐이면 그것** — 질문하지 않는다
4. 복수면 AskUserQuestion 으로 선택받는다

이슈유형·컴포넌트·커스텀필드·assignee 매핑은 **`projects.<대상키>` 에서 읽는다.** 다른 프로젝트의
매핑을 재사용하지 않는다 — 프로젝트마다 구성이 다르다. 대상이 `projects` 에 **등록되지 않은**
프로젝트면 createmeta 로 조회해 진행한다:

```bash
curl -s -u "$email:$token" "$baseUrl/rest/api/3/issue/createmeta?projectKeys=<대상키>&expand=projects.issuetypes.fields"
```

조회로 진행했다면 작업 완료 후 `projects.<대상키>` 병합을 설정 권고 블록으로 안내한다.
인증(baseUrl·email·apiTokenFile)은 사이트 공통이라 프로젝트와 무관하게 그대로 쓴다.

## 이슈 생성 규칙

### 필드 결정 규칙

| 필드 | 규칙 |
|------|------|
| **보고자** | 컨텍스트에서 보고자 정보가 있으면 REST API(`/rest/api/3/user/search`)로 검색 후 설정. 생성 후 REST API(`PUT /rest/api/3/issue/{key}`)로 reporter 변경을 시도한다. 실패 시 설명(description)에 "보고자: {이름}"으로 기록 |
| **담당자** | 컨텍스트에서 담당자 정보가 있으면 설정. 없으면 할당하지 않는다 (null) |
| **이슈 유형** | 기본 `결함`. 내용에 따라 사용자에게 선택지를 제공한다 |
| **이슈 구분** | 대상 프로젝트 설정(`projects.<키>.customFields`)에 있으면 적용. 없으면 생략 |
| **컴포넌트** | 대상 프로젝트 설정(`projects.<키>.components`)에 있으면 내용을 분석하여 결정. 없으면 생략 |
| **요약** | 핵심을 한글 70자 이내로 요약 |
| **설명** | 아래 설명 템플릿에 따라 작성 |

### 이슈 유형

대상 프로젝트 설정(`projects.<키>.issueTypes`)에 유형 목록이 있으면 그것을 사용한다.
없으면 Jira 프로젝트의 기본 이슈 유형을 사용하며, `결함`을 기본값으로 한다.

### 컴포넌트 판별 규칙

대상 프로젝트 설정(`projects.<키>.components`)에 목록이 있으면 내용의 키워드를 분석하여 컴포넌트를 결정한다.

- 판별이 애매하면 AskUserQuestion으로 사용자에게 질문한다
- 복수 컴포넌트 해당 시 모두 포함할 수 있다
- 대상 프로젝트 설정에 컴포넌트가 없으면 컴포넌트를 지정하지 않는다

### 설명 템플릿

```markdown
## 현상

{내용을 기반으로 현상 정리}

## 출처

{출처 정보가 있으면 기재. 없으면 이 섹션 생략}

## 조치 필요사항

- {내용 분석 기반 액션 아이템}
```

## 절차

### 1. 컨텍스트 확인

- `$ARGUMENTS`에 설명이 있으면 해당 내용을 분석한다
- 없으면 AskUserQuestion으로 이슈 내용을 입력받는다
- 현재 대화 컨텍스트에서 **부모 이슈(Epic)** 정보가 있으면 하위 이슈로 생성한다

### 2. 이슈 필드 결정

내용을 분석하여 다음을 결정한다:
- 이슈 유형 (기본: 결함)
- 컴포넌트 (Web.Backend / Web.Frontend)
- 요약 (70자 이내)
- 설명 (템플릿에 따라)

결정된 내용을 사용자에게 보여주고 확인을 받는다.

### 3. 사용자 매핑 (선택)

보고자/담당자 정보가 있으면 accountId 를 조회한다. 설정 로드·URL 인코딩은 스크립트가 한다.

```bash
${CLAUDE_SKILL_DIR}/../../scripts/jira-issue.sh user --query "<이름 또는 이메일>"
```

찾으면 accountId 를 한 줄로 출력하고, 못 찾으면 종료 코드 1과 함께 오류를 낸다.
**매핑 실패는 이슈 생성을 막지 않는다** — 설명에 "보고자: {이름}" 으로 기록하고 진행한다.

### 4. Jira 이슈 생성

**설명을 먼저 파일로 쓴다.** 설명 본문을 셸 인자로 넘기지 않는다 — 로그·스택트레이스에 흔한
`'` `"` `$` `\` 가 페이로드를 깨뜨린다. Write 도구로 `/tmp/jira-desc.md` 에 마크다운 평문을 쓴다.

그 다음 스크립트로 생성한다. 설정 로드·ADF 변환·이스케이프·에러 처리는 스크립트가 한다.

```bash
${CLAUDE_SKILL_DIR}/../../scripts/jira-issue.sh create \
  --summary "<요약>" \
  --type "<이슈 유형>" \
  --description-file /tmp/jira-desc.md
```

성공하면 생성된 이슈 키를 한 줄로 출력한다. 실패하면 Jira 가 준 `errorMessages` 를 그대로
보여주고 종료 코드 1로 끝난다.

선택 옵션:

| 옵션 | 용도 |
|------|------|
| `--project <키>` | 대상 프로젝트 명시 (미지정 시 `projects` 가 1개면 자동, 복수면 질문) |
| `--parent <이슈키>` | Epic 하위로 생성. 이때 `--type` 은 `하위 작업` 으로 준다 |
| `--component <이름>` | 컴포넌트 지정 |
| `--field <필드ID>=<값>` | 이슈 구분 등 커스텀 필드. 여러 번 반복 가능 |
| `--dry-run` | 전송하지 않고 페이로드만 출력 (문제 진단용) |

부모 이슈 정보는 대화 컨텍스트 또는 `$ARGUMENTS` 에서 추출한다.

### 5. 이슈 후처리

담당자·보고자가 있으면 생성 후 설정한다.

```bash
${CLAUDE_SKILL_DIR}/../../scripts/jira-issue.sh edit \
  --key "<이슈키>" --assignee "<accountId>" --reporter "<accountId>"
```

**보고자 변경은 권한 부족으로 실패할 수 있다.** 스크립트가 담당자와 보고자를 따로 보내므로
보고자만 실패해도 담당자는 남는다. 보고자 설정에 실패하면 경고를 내고, 이름은 설명에 기록한다.

### 6. 결과 출력

```
Jira 이슈 생성 완료!

- 이슈: {이슈키} ({JIRA_BASE_URL}/browse/{이슈키})
- 유형: {이슈유형}
- 요약: {요약}
- 담당자: {이름} / 할당되지 않음
```

## 주의사항

- 이슈 생성 전에 반드시 사용자 확인을 받는다
- Jira 사용자 매핑 실패 시 설명에 사용자 정보를 기록한다

## plugins.json 설정 권고 (작업 후)
이번 실행에서 AskUserQuestion 으로 받은 값이 있었다면, 작업 완료 후
[../../reference/config-recommendation.md](../../reference/config-recommendation.md) 의 출력 포맷대로
안내 블록을 출력한다. 모든 값을 plugins.json 에서 얻었으면 생략한다.

**권고 대상:**
- **포함**: AskUserQuestion 으로 받은 값 (다음부터 자동 처리되려면 plugins.json 에 저장 필요). 예: `baseUrl`, `email`, `apiTokenFile`, `projects.<키>`(assignee·issueTypes·components·customFields)
- **제외**: 컨텍스트에서 추출한 값 (담당자 등), AI 가 자동 판단한 값 (이슈 유형 분류, 컴포넌트 매핑 결과, 이슈 본문/요약)

