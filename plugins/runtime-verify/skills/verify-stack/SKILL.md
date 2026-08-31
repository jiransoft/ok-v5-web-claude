---
name: verify-stack
description: Jira 이슈별로 이슈번호에서 파생한 고유 포트 블록을 할당해 프로젝트의 애플리케이션 모듈들을 병렬 기동하고, 브라우저 자동화로 관리자/서비스 화면에서 이슈의 재현·기대결과를 검증한다. 이슈별 독립 실행(포트 충돌 없음) + 브라우저 context 격리 인증 + Jira 시나리오 대조를 수행하며, --source 지정 시 그 브랜치의 detached worktree에서 실행해 사용자 작업 트리에 영향을 주지 않는다. 이슈키 없이 --source만 주면 브랜치 모드로 동작 — 브랜치 고유 커밋을 분석해 검증 시나리오를 도출하고 사용자 리뷰 승인 후 검증한다.
when_to_use: 사용자가 "이슈 검증 스택 띄워", "PROJ-1234 검증 환경 실행", "이슈별 포트로 모듈 실행", "여러 이슈 동시 검증", "관리자페이지에서 이슈 확인", "이 브랜치 검증해줘", "verify-stack", "runtime0verify" 등 이슈·브랜치 재현·검증용 로컬 런타임 기동을 요청할 때.
allowed-tools: Bash(git *), Bash(curl *), Bash(lsof *), Bash, Read, Grep, Glob, Agent, AskUserQuestion, TaskStop
# lint-skip: BASH — 모듈 기동·준비 명령(gradlew·npm 등)이 plugins.json 사용자 설정에서 오므로 전체 스코핑 불가
argument-hint: "[이슈키] [--source <branch>]"
---

# Verify Stack Skill

여러 Jira 이슈를 **동시에** 검증하기 위해, 이슈마다 이슈번호 파생 포트 블록으로 모듈들을 병렬 기동하고, 브라우저로 이슈의 재현/기대결과를 검증한다.

**두 가지 모드:**

| 모드 | 진입 조건 | 포트 오프셋 | 시나리오 소스 |
|------|----------|------------|--------------|
| 이슈 모드 | 이슈키 지정 | 이슈번호 % 1000 | Jira 설명+댓글 |
| 브랜치 모드 | 이슈키 없이 `--source`만 지정 | cksum(브랜치명) % 1000 | 브랜치 고유 커밋 분석 → **사용자 리뷰 승인** |

> **전제**: 공유 인프라(DB·MQ 등)는 이미 떠 있고 모든 이슈가 그대로 사용한다 (이슈별 인프라 분리 없음).

## --help 처리

`$ARGUMENTS`가 `--help` 또는 `-h` 면 [reference/usage.md](reference/usage.md) 의 사용법 블록을 그대로 출력하고 즉시 종료한다.

## 진행 체크리스트

**아래 체크리스트를 응답에 복사해두고 단계마다 갱신한다.**

```
- [ ] 0. 설정 로드
- [ ] 1. 인자 파싱 (이슈키 · --source · 모드 판정)
- [ ] 2. 포트 블록 계산 + 선점 검사
- [ ] 3. worktree 해석·준비
- [ ] 4. 모듈 기동 (모듈별 백그라운드 호출)
- [ ] 5. 헬스 폴링 → 준비 완료 실측
- [ ] 6. 검증 시나리오 도출 (이슈 모드: Jira / 브랜치 모드: 커밋 분석 → 사용자 승인)
- [ ] 7. 브라우저 검증 (context 격리)
- [ ] 8. 결과 보고
- [ ] 9. 정리 (프로세스·worktree — 사용자 확인 후)
```

## 절차

### 0. 설정 로드

**본체 레포 루트의** `.claude/plugins.json` 에서 `runtime-verify` 섹션을 **Read 도구로 직접** 읽는다 (시스템 컨텍스트에 이미 로드된 값을 쓰지 않는다). 없으면 프로젝트 `CLAUDE.md` → 그래도 없으면 AskUserQuestion 순으로 폴백한다.

`plugins.json` 은 gitignore 대상이라 **worktree 에는 존재하지 않는다.** worktree 작업 중에는 본체 루트를 먼저 구해 절대경로로 읽는다:

```bash
gcd=$(git rev-parse --git-common-dir); case $gcd in /*) ;; *) gcd=$PWD/$gcd ;; esac
root=$(cd "$gcd/.." && pwd -P)
```

| 키 | 필수 | 설명 |
|----|:--:|------|
| `modules` | ✅ | 기동할 모듈 배열 `{name, dir, start, health}`. `start`·`health` 문자열의 `{sN}` 자리에 슬롯 N 포트가 치환된다 |
| `projectKey` | | Jira 프로젝트 키. 없으면 `jira-tools.projectKey` 를 폴백으로 읽고, 그래도 없으면 질문 |
| `credentialsFile` | | 로그인 계정 파일 경로 (`id:pw` 한 줄). UI 검증에 로그인이 필요할 때 사용 |
| `portBase` | | 포트 산식 기준값 (기본 `10000`) |
| `worktreeBase` | | worktree 생성 위치 (기본 `/tmp`) |
| `ui` | | `{module, slot, signinPath}` — 브라우저 검증 진입점 |
| `prepare` | | worktree 생성 직후 worktree 루트에서 실행할 준비 명령 배열. `$MAIN` 은 본체 레포 루트로 치환 |

모듈 스키마 상세와 작성 예시는 [reference/config-example.md](reference/config-example.md) 를 읽는다.

### 1. 인자 파싱

- `$ARGUMENTS` 에서 이슈 키(`<projectKey>-1234` 또는 숫자만)와 `--source <branch>` 를 파싱한다
- **모드 판정**:
  - 이슈 키가 있으면 **이슈 모드**. **이슈번호** = 키의 숫자부, 이후 산식은 이 숫자를 쓴다
  - 이슈 키가 없으면 **브랜치 모드**. 이 모드에서는 `--source` 가 필수 — 없으면 AskUserQuestion 으로 브랜치명을 받는다

### 2. 포트 블록 계산 + 선점 검사

```
포트(슬롯 N) = portBase + N × 1000 + 오프셋
오프셋 = 이슈 모드: 이슈번호 % 1000 · 브랜치 모드: cksum(브랜치명) % 1000
```

- 예: portBase 10000, 이슈 12345 → 슬롯0 `10345`, 슬롯1 `11345`, … 슬롯7 `17345`
- 브랜치 모드 오프셋 계산 (POSIX `cksum` — 셸에 무관하게 결정적이라 같은 브랜치는 항상 같은 포트):

```bash
printf %s "<브랜치명>" | cksum | awk '{print $1 % 1000}'
```
- ⚠️ **Bash 호출은 매번 새 셸이다 — 함수 정의·export 변수가 다음 호출로 이어지지 않는다.** 포트는 위 산식으로 직접 계산해 **모든 명령에 리터럴 숫자로 삽입**한다. 헬퍼 함수·환경변수 릴레이에 의존하지 않는다
- **충돌 조건**: 오프셋(0~999)이 같은 두 실행만 충돌한다 (이슈 모드 예: 12345·13345 — 마지막 3자리 동일). 동시 실행 목록과 겹치면 사용자에게 알리고 진행 여부를 확인한다
- **선점 검사**: 기동 전에 사용할 슬롯 포트 전체를 검사한다. 하나라도 물려 있으면 점유 프로세스를 보고하고 사용자 확인 후 진행한다:

```bash
lsof -nP -iTCP -sTCP:LISTEN | grep -E ":(<슬롯 포트를 |로 나열>)\b"
```

### 3. worktree 해석·준비

핵심 원칙: **사용자의 현재 작업 트리·브랜치에 영향을 주지 않는다.** 대상 브랜치를 절대 checkout 하지 않고 detached worktree 에서만 실행한다. 경로는 이슈 모드 `<worktreeBase>/wt-<이슈키>`, 브랜치 모드 `<worktreeBase>/wt-<브랜치명(슬래시→대시 치환)>`.

1. **`--source <branch>` 지정 시**: self-heal 가드 후 detached worktree 를 만든다:

   ```bash
   # 스테일 worktree 자기 치유 (이전 실행이 중단돼 남아 있으면 제거)
   git worktree remove --force <PATH> 2>/dev/null; git worktree prune; rm -rf <PATH>
   git worktree add --detach <PATH> <source>
   ```

2. **미지정 시** (이슈 모드만 해당 — 브랜치 모드는 1단계에서 `--source` 를 확보한다): `git worktree list` 로 이슈 키 포함 경로를 찾아 **있으면 재사용**, 없으면 사용자에게 "바라볼 브랜치 이름"을 **재질의**한 뒤 1번 방식으로 만든다. 임의 추정 금지.

3. **worktree 준비**: 새로 만든 worktree 에는 **gitignore 된 로컬 설정(`.env` 등)과 설치 산출물(`node_modules` 등)이 없다.** `prepare` 명령들을 worktree 루트에서 순서대로 실행한다 (`$MAIN` → 본체 레포 루트 치환). `prepare` 미설정 상태에서 모듈 기동이 실패하면 이 원인부터 의심하고 사용자에게 알린다.

### 4. 모듈 기동

`modules` 의 각 모듈을 **모듈마다 별도의 Bash 호출**로, `run_in_background: true` 로 기동한다. 오래 도는 프로세스이므로 한 호출에 여러 모듈을 묶으면 첫 모듈에서 블로킹된다.

```bash
cd "<worktree>/<dir>" && <start 명령 — {sN} 을 계산된 리터럴 포트로 치환>
```

### 5. 헬스 폴링

각 모듈 `health` 의 url(`{sN}` 치환)을 **10초 간격으로 폴링**한다. 기본 타임아웃 5분 — JVM 계열은 초기 부팅이 느리므로 첫 1분의 `000`(연결 불가)은 정상이다.

```bash
curl -s -o /dev/null -w "%{http_code}" --max-time 4 <health url>
```

- 응답 코드가 `expect` 와 일치하면 그 모듈 준비 완료
- 타임아웃 초과 시 해당 모듈의 백그라운드 출력(로그)을 확인해 원인과 함께 보고하고 중단한다

### 6. 검증 시나리오 도출

**이슈 모드:**

- **기본: Jira 자동 조회** (jira-tools 플러그인 또는 Jira REST). 이슈 **설명 + 댓글**까지 읽어 재현 절차·기대결과를 도출한다 — 댓글에 재현 방법·추가 요구가 실리는 경우가 많으므로 반드시 확인한다
- **보완**: 사용자가 제공한 시나리오/주의점을 Jira 내용 위에 우선 적용한다
- 두 소스를 합쳐 항목별 체크리스트를 만든다 (7단계에서 항목별 통과/실패 판정)

**브랜치 모드:**

1. 기본 브랜치와의 merge-base 기준으로 source 브랜치 **고유 커밋**을 분석한다:

   ```bash
   git log --oneline $(git merge-base <기본브랜치> <source>)..<source>
   git diff --stat $(git merge-base <기본브랜치> <source>)..<source>
   ```

   기본 브랜치는 `origin/HEAD` 로 판별하고, 판별이 애매하면 사용자에게 확인한다. 필요하면 개별 커밋의 diff 까지 읽어 변경 의도를 파악한다

2. 커밋·diff 분석으로 변경 지점별 검증 시나리오 체크리스트 초안을 만들어 **사용자에게 보고**한다 — 항목마다 근거 커밋/파일을 함께 제시한다
3. **사용자가 리뷰·수정·승인한 뒤에만 7단계로 진행한다** (AskUserQuestion 으로 승인/수정 여부를 확인). Jira 라는 정답지가 없는 모드이므로 이 승인 게이트를 생략하지 않는다

### 7. 브라우저 검증

세션에 연결된 브라우저 자동화 도구(예: `mcp__playwright__browser_navigate` 등 Playwright 계열)로 실제 화면을 사람이 하듯 조작하며 검증한다. API 직접 호출로 대체하지 않는다.

- **격리 단위는 browser context 다.** 이슈 1개 = context 1개(시크릿창 등가물). 같은 context 의 탭들은 쿠키를 공유하므로 **탭을 격리 단위로 쓰지 않는다**. 이슈마다 포트(origin)가 달라 쿠키가 origin 단위로도 분리되는 이중 안전이다
- 로그인 필요 시 `credentialsFile` 에서 계정을 읽는다 — **로그·출력·코드에 평문으로 남기지 않는다**:

  ```bash
  IFS=':' read -r ADMIN_ID ADMIN_PW < <credentialsFile>
  ```

- `ui.module` 슬롯 포트의 `signinPath` 로 이동해 로그인 → 시나리오 항목별로 화면 이동·조작·확인
- mutation(등록/수정/삭제) 검증은 응답만이 아니라 **새로고침 후 재렌더링된 데이터**로 영구 반영을 확인한다
- 스크린샷·콘솔·네트워크 기록으로 증거를 수집한다

**UI 만으로 검증할 수 없는 경우** (필요한 데이터 조합을 화면에서 만들 수 없음 등): 임의 추정·검증 생략 금지. 사용자에게 수행 방법을 인터뷰한 뒤, 다음을 권고안으로 제시하고 **승인 후** 진행한다 — ① 현재 DB 백업 → ② 필요한 fixture 를 DB 에 직접 주입 → ③ 검증 후 주입분 롤백 → ④ 롤백 곤란 시 ①의 백업으로 복원. 인터뷰로 확정할 것: 주입 방식, 백업/복원 명령, 롤백 책임 주체.

### 8. 결과 보고

체크리스트 항목별 통과/실패와 증거(스크린샷 경로·관찰 내용)를 이슈 단위로 정리해 보고한다.

### 9. 정리

1. 백그라운드 task 를 TaskStop 으로 종료한다
2. 슬롯 포트로 잔존 리스너를 확인한다 (2단계의 lsof 명령 재사용)
3. 이 스킬이 만든 worktree 는 **사용자 확인 후** `git worktree remove` 로 정리한다. detached 이므로 브랜치는 그대로 남는다

## 다중 이슈 동시 운영 메모

- **공유 인프라 간섭**: 모든 이슈가 같은 DB 를 본다. 한 이슈의 mutation 검증이 다른 이슈의 데이터 검증에 간섭할 수 있으니, 데이터 변경 검증은 이슈 간 시점을 겹치지 않게 하거나 대상 데이터를 분리한다
- **빌드 간섭**: 실행 중인 모듈 아래서 컴파일하면 클래스패스 불일치로 특정 요청만 500 이 날 수 있다. 검증 중에는 컴파일을 피하고, 했다면 해당 모듈을 재기동한다
- 이슈 N개 = 프로세스 N × 모듈 수 — 동시 개수는 머신 여력 내에서

## 주의사항

- 사용자의 현재 작업 트리·브랜치에 영향을 주지 않는다 — checkout 금지, detached worktree 만 사용
- credential 을 로그·출력·코드에 평문으로 남기지 않는다
- 서브에이전트 분석 결과를 그대로 수용하지 않는다 — 핵심 주장은 직접 확인하고, 미검증분은 "추정"으로 표기한다

## plugins.json 설정 권고 (작업 후)

이번 실행에서 AskUserQuestion 으로 받은 값이 있었다면, 작업 완료 후
[../../reference/config-recommendation.md](../../reference/config-recommendation.md) 의 출력 포맷대로 안내 블록을 출력한다. 모든 값을 plugins.json 에서 얻었으면 생략한다.

- **포함**: AskUserQuestion 으로 받은 값 (예: `projectKey`, `credentialsFile`, `modules` 구성)
- **제외**: CLI 인자(이슈키, `--source`), 재질의로 받은 브랜치명
