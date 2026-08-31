---
name: figma-comment
description: Figma 파일에 코멘트를 조회, 작성, 삭제합니다. @멘션이 필요하면 playwright-cli로 Figma UI를 자동화합니다.
when_to_use: 사용자가 Figma URL과 함께 "코멘트 달아줘", "코멘트 목록 보여줘", "이 코멘트 삭제해줘", "@멘션해서 코멘트 남겨줘", "figma comment" 등 Figma 코멘트의 조회·작성·삭제를 요청할 때.
allowed-tools: Bash(curl *), Bash(playwright-cli *), Bash(node *), Read, AskUserQuestion
argument-hint: "[list|post|delete] [figma-url] [options]"
---

# Figma Comment Skill

Figma REST API를 사용하여 코멘트를 조회, 작성, 삭제한다.
**@멘션이 필요한 경우** `playwright-cli`로 Figma UI를 자동화하여 코멘트를 작성한다.

## 전제 조건

`playwright-cli` 설치 필요:
```bash
npm install -g @playwright/cli
```
MS가 AI 에이전트용으로 만든 공식 CLI. `npx playwright` (테스트용)와 다른 별도 도구.

## 스냅샷 워크플로우 패턴

`playwright-cli snapshot`은 현재 페이지의 접근성 트리를 YAML 파일로 저장하고, 파일 경로를 출력한다.
각 요소에는 `e1`, `e2`, ... 형태의 ref가 부여된다. 이 ref를 사용하여 click, type 등 후속 명령을 실행한다.

```
# 1. 스냅샷 저장 (파일 경로가 stdout에 출력됨)
Bash: playwright-cli snapshot

# 2. 출력된 경로의 YAML 파일을 읽어서 요소 ref 확인
Read: <snapshot-file-path>

# 3. 원하는 요소의 ref로 상호작용
Bash: playwright-cli click e42
```

이 패턴은 이 스킬 전체에서 "스냅샷 촬영 → 요소 확인 → 상호작용"이 필요한 모든 곳에 적용된다.

## --help 처리

`$ARGUMENTS`가 `--help` 또는 `-h` 면 [reference/usage.md](reference/usage.md) 의 사용법 블록을 그대로 출력하고 즉시 종료한다.

## 공통: 토큰 확보

토큰 확보 우선순위:
1. `~/.figma-token` 파일이 있으면 읽어서 사용
2. 없으면 AskUserQuestion으로 요청하고, `~/.figma-token`에 저장

토큰은 절대 출력이나 문서에 기록하지 않는다.

## 공통: URL 파싱

Figma URL에서 추출할 정보:
- **fileKey**: URL path의 `design` 다음 segment
- **nodeId** (선택): query parameter `node-id` 값 (`-`를 `:`로 변환)

예: `https://www.figma.com/design/ABC123/FileName?node-id=36048-107098`
→ fileKey: `ABC123`, nodeId: `36048:107098`

## 공통: 노드 ID 결정 (코멘트 위치 미세조정)

코멘트를 달 노드 ID를 결정할 때 다음 우선순위를 따른다:

1. `--node` 옵션이 있으면 해당 노드 ID 사용
2. URL의 `node-id` 파라미터가 있으면 해당 노드 ID 사용
3. 둘 다 없으면 파일 레벨에 코멘트

**미세조정 가이드**: 코멘트 내용과 가장 밀접한 컴포넌트의 node-id를 `--node`로 지정하고, 해당 노드 내에서 `--offset`으로 정확한 위치를 조정한다.

## 인터랙티브 모드

`$ARGUMENTS`가 비어있으면 AskUserQuestion으로 순차 수집:

### 1. 동작 선택

```
어떤 작업을 할까요?

옵션:
- 코멘트 조회 (list)
- 코멘트 작성 (post)
- 코멘트 작성 + @멘션 (post --mention)
- 코멘트 삭제 (delete)
```

### 2. Figma URL

```
Figma 파일 URL을 입력해주세요.
```

### 3. 동작별 추가 입력

- **list**: 추가 입력 없음
- **post**: 코멘트 내용 입력, 답글 여부
- **post --mention**: 코멘트 내용, 멘션 대상 이메일
- **delete**: comment ID 입력

---

## 동작: list

### API 호출

```bash
curl -s -H "X-Figma-Token: {token}" \
  "https://api.figma.com/v1/files/{fileKey}/comments"
```

### 필터링

- `nodeId`가 지정된 경우: `client_meta.node_id`가 해당 노드와 일치하는 코멘트만
- `--unresolved`: `resolved_at`이 null인 코멘트만

### 출력 형식

코멘트를 스레드 단위로 그룹핑하여 출력한다:

```markdown
## Figma 코멘트

> 파일: {fileName}
> 총 {N}개 코멘트 ({M}개 스레드)

| # | 노드 | 작성자 | 내용 (요약) | 답글 수 | 상태 |
|---|------|--------|-----------|---------|------|
| 1 | `{nodeId}` | {handle} | {메시지 요약 50자} | {N}개 | Open/Resolved |

---

### 스레드 1 — `comment_id: {root_id}`

> **{handle}** ({created_at}):
> {message}
>
> ---- **{reply_handle}** ({created_at}):
> ---- {reply_message}
```

- `parent_id`가 비어있으면 루트 코멘트, 있으면 답글로 들여쓰기
- `resolved_at`이 null이면 Open, 값이 있으면 Resolved

---

## 동작: post (REST API 모드)

`--mention` 옵션이 **없을 때** 사용한다.

### 코멘트 내용 규칙

- AI가 작성하는 코멘트는 반드시 `💸` 로 시작한다
- 사용자가 내용을 직접 지정한 경우 그대로 사용한다

### API 호출 — 새 코멘트

nodeId가 있으면 해당 노드에, 없으면 파일 레벨에 코멘트를 작성한다.

```bash
curl -s -X POST "https://api.figma.com/v1/files/{fileKey}/comments" \
  -H "X-Figma-Token: {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "{message}",
    "client_meta": {
      "node_id": "{nodeId}",
      "node_offset": {"x": {offsetX}, "y": {offsetY}}
    }
  }'
```

- nodeId가 없으면 `client_meta`를 생략한다
- `--offset`이 없으면 `{"x": 0, "y": 0}` 사용

### API 호출 — 답글

`--reply <comment_id>` 옵션이 있으면 해당 코멘트에 답글을 작성한다.

```bash
curl -s -X POST "https://api.figma.com/v1/files/{fileKey}/comments" \
  -H "X-Figma-Token: {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "{message}",
    "comment_id": "{comment_id}"
  }'
```

### 결과 출력

```
Figma 코멘트 작성 완료! (REST API)
- comment_id: {id}
- 작성자: {handle}
- 노드: {nodeId}
- 내용: {message 앞 100자}
```

---

## 동작: post --mention (REST API + playwright-cli Edit 모드)

`--mention <email>` 옵션이 **있을 때** 사용한다.
Figma REST API는 @멘션을 지원하지 않으므로, **2단계**로 처리한다:
1. REST API로 코멘트 본문을 먼저 작성한다
2. `playwright-cli`로 해당 코멘트를 **Edit(편집)**하여 @멘션만 추가한다

> 답글로 멘션을 추가하지 않는다 — 코멘트 본문 자체에 멘션이 포함되어야 한다.

### 사전 조건 확인

1. `~/.figma-token` 파일 존재 확인
2. `~/.figma-session.json` 파일 존재 확인. 없으면 에러 메시지 출력 후 종료:
   ```
   Figma 세션 파일이 없습니다. 먼저 Figma에 로그인하여 ~/.figma-session.json을 생성해주세요.
   ```

### Phase 1: REST API로 코멘트 작성

"동작: post (REST API 모드)"와 동일하게 코멘트를 작성한다.
- 응답에서 `comment_id`를 저장한다 (Phase 2에서 코멘트를 찾는 데 사용)

### Phase 2: playwright-cli로 기존 코멘트 Edit → 멘션 추가

#### Step 1: 세션 로드 및 Figma 페이지 열기

먼저 저장된 Figma 세션을 로드한다:
```bash
playwright-cli state-load ~/.figma-session.json
```

nodeId의 `:` 를 `-`로 변환하여 URL을 구성한다:

```
https://www.figma.com/design/{fileKey}/?node-id={nodeId_with_dashes}
```

```bash
playwright-cli goto "https://www.figma.com/design/{fileKey}/?node-id={nodeId_with_dashes}"
```

#### Step 2: 페이지 로딩 대기

```bash
playwright-cli run-code "async page => { await page.waitForTimeout(5000); return 'ready'; }"
```

#### Step 3: 코멘트 패널 열기

1. 스냅샷을 저장하고 Read 도구로 읽어서 현재 상태 확인:
   ```bash
   playwright-cli snapshot
   ```
   → Read 도구로 스냅샷 파일을 읽어 Comment 탭/버튼의 ref 확인
2. Comment 탭 또는 Comment 버튼(`Comment (N unread)`)을 `ref`로 클릭하여 코멘트 패널 열기:
   ```bash
   playwright-cli click {comment_button_ref}
   ```

#### Step 4: 방금 작성한 코멘트 찾기 & 선택

코멘트 패널에서 Phase 1에서 작성한 코멘트를 찾는다:
- 스냅샷을 다시 저장하고 Read 도구로 읽어서 코멘트 목록의 ref 확인
- 코멘트 목록에서 `💸`로 시작하고, 작성자가 본인이고, 시간이 "Just now"인 코멘트의 `ref`를 찾는다
- 해당 코멘트 `Select comment by ...` 버튼을 클릭하여 코멘트 스레드를 펼친다:
  ```bash
  playwright-cli click {comment_ref}
  ```

#### Step 5: 코멘트 Edit 모드 진입

1. 코멘트 스레드가 펼쳐지면, 스냅샷을 저장하고 Read 도구로 읽어서 **"Comment actions"** 버튼 (⋯ 아이콘)의 `ref`를 찾아 클릭한다:
   ```bash
   playwright-cli snapshot
   ```
   → Read 도구로 읽어서 actions 버튼 ref 확인
   ```bash
   playwright-cli click {actions_button_ref}
   ```
2. 스냅샷을 다시 저장하고 Read 도구로 읽어서 드롭다운 메뉴에서 **"Edit comment"** 항목의 ref를 찾아 클릭한다:
   ```bash
   playwright-cli snapshot
   ```
   → Read 도구로 읽어서 "Edit comment" ref 확인
   ```bash
   playwright-cli click {edit_comment_ref}
   ```

#### Step 6: 멘션 추가

Edit 모드에서 코멘트 텍스트가 편집 가능 상태가 된다.

**중요: `fill()` 사용 금지** — `fill()`은 멘션 데이터를 덮어쓴다.

1. **커서를 코멘트 맨 앞으로 이동**:
   ```bash
   playwright-cli press Home
   ```
   또는:
   ```bash
   playwright-cli press Meta+ArrowUp
   ```

2. **@멘션 입력**:
   ```bash
   playwright-cli run-code "async page => { await page.keyboard.type('@'); await page.waitForTimeout(1000); await page.keyboard.type('{email_prefix}', { delay: 80 }); await page.waitForTimeout(2000); return 'typed'; }"
   ```
   - `{email_prefix}`는 이메일의 `@` 앞부분 (예: `john.doe`)
   - 스냅샷을 저장하고 Read 도구로 읽어서 멘션 드롭다운을 확인:
     ```bash
     playwright-cli snapshot
     ```
     → Read 도구로 읽어서 해당 이메일 옵션(`option` role)의 `ref`를 찾음
   - 드롭다운에서 해당 이메일 옵션을 클릭:
     ```bash
     playwright-cli click {email_option_ref}
     ```

3. **스페이스 추가** (멘션과 본문 사이):
   ```bash
   playwright-cli run-code "async page => { await page.keyboard.type(' '); return 'spaced'; }"
   ```

#### Step 7: 저장

```bash
playwright-cli press Meta+Enter
```
또는 스냅샷에서 "Save" 버튼의 `ref`를 찾아 클릭한다:
```bash
playwright-cli snapshot
```
→ Read 도구로 읽어서 Save 버튼 ref 확인
```bash
playwright-cli click {save_button_ref}
```

#### Step 8: 결과 확인

스크린샷을 찍어 멘션이 정상 추가되었는지 확인한다:
```bash
playwright-cli screenshot mention-result.png
```
→ Read 도구로 스크린샷 이미지를 확인한다.

### 멀티 코멘트 작성 시

여러 노드에 순차적으로 코멘트를 작성할 때:
1. Phase 1: REST API로 모든 코멘트를 **먼저 일괄 작성** (comment_id 목록 수집)
2. Phase 2: `playwright-cli`로 브라우저를 열고, 각 코멘트에 대해 Step 3~8을 반복
3. 같은 페이지의 코멘트는 navigate 없이 코멘트 패널에서 바로 찾기
4. 다른 노드의 코멘트는 Step 1(goto)부터 반복
5. 모든 코멘트 처리 완료 후 `playwright-cli close`로 브라우저 닫기

### 결과 출력

```
Figma 코멘트 작성 완료! (REST API + playwright-cli Edit 멘션)
- comment_id: {id}
- 노드: {nodeId}
- 멘션: @{email}
- 내용: {message 앞 100자}
- 스크린샷: [첨부]
```

### 에러 처리

| 상황 | 대응 |
|------|------|
| 세션 만료 (로그인 페이지 리다이렉트) | "Figma 세션이 만료되었습니다. `~/.figma-session.json`을 갱신해주세요." |
| 멘션 자동완성 미표시 | 이메일 전체 입력 후 스냅샷 재확인. 실패 시 멘션 없이 REST API 본문만 유지 |
| Edit 메뉴 미표시 | 본인이 작성한 코멘트만 Edit 가능. 작성자 확인 |
| 코멘트를 찾지 못함 | comment_id로 REST API 조회하여 node_id 확인 후 해당 노드로 `playwright-cli goto` |

---

## 동작: delete

### API 호출

```bash
curl -s -X DELETE "https://api.figma.com/v1/files/{fileKey}/comments/{comment_id}" \
  -H "X-Figma-Token: {token}"
```

### 결과 출력

```
Figma 코멘트 삭제 완료! (comment_id: {comment_id})
```

삭제 전에 해당 코멘트 내용을 조회하여 사용자에게 확인을 받는다.

---

## 주의사항

- Figma REST API rate limit에 주의한다 (분당 요청 수 제한)
- 토큰은 절대 출력이나 문서에 기록하지 않는다
- 삭제는 본인이 작성한 코멘트만 가능하다
- AI가 작성하는 코멘트는 반드시 `💸` 로 시작한다
- **playwright-cli 모드에서 `fill()` 절대 사용 금지** — `type()` 또는 `pressSequentially()` 사용
- playwright-cli 모드에서 각 단계 사이에 적절한 대기 시간을 둔다 (UI 반응 대기)
- 멀티 코멘트 시 브라우저를 재사용하여 효율성을 높인다
- 작업 완료 후 `playwright-cli close`로 브라우저를 닫는다