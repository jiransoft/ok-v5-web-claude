---
name: diagram
description: 코드를 분석하여 Mermaid 다이어그램 문서를 생성합니다. 아키텍처, 시퀀스, 플로우차트 등을 자동 선택하고, --pdf 시 제목·설명·구성요소 표를 포함한 자립형 PDF도 만듭니다.
when_to_use: 사용자가 "다이어그램 그려줘", "아키텍처 도식화해줘", "시퀀스 다이어그램 만들어줘", "이 흐름 플로우차트로 그려줘", "구조도 만들어줘", "draw diagram", "Mermaid 다이어그램" 등 코드를 분석해 아키텍처·시퀀스·플로우차트 등을 그림으로 정리하려 할 때.
allowed-tools: Bash(git *), Bash(npx *), Bash(node *), Bash(find *), Bash(grep *), Bash(rm *), Bash(mkdir *), Bash(cd *), Read, Grep, Glob, Write, Edit, Agent
argument-hint: <대상 설명> [--source <branch>] [--pdf] [--output <path>]
---

# Diagram Skill

코드를 분석하여 Mermaid 다이어그램을 생성하고, 선택적으로 PDF로 변환한다.

## --help 처리

`$ARGUMENTS`가 `--help` 또는 `-h` 면 [reference/usage.md](reference/usage.md) 의 사용법 블록을 그대로 출력하고 즉시 종료한다.

## 인자 파싱

- `$ARGUMENTS`에서 플래그 추출:
  - `--source <branch>` → 분석할 브랜치 (미지정 시 현재 브랜치)
  - `--pdf` → PDF 생성 여부
  - `--output <path>` → 출력 디렉토리 (기본: `docs/`)
- 나머지 텍스트 → 다이어그램 대상 설명

### 출력 위치

**산출물은 분석한 코드와 같은 계보에 남는다.** 로컬에 체크아웃된 브랜치는 분석 대상과
전혀 무관할 수 있다. 거기에 문서를 떨구면 엉뚱한 브랜치의 변경분이 된다.

| `--source` | 산출물 위치 |
|------------|------------|
| 미지정 | 현재 워킹트리의 `--output` (커밋하지 않는다) |
| 지정 | 0절 worktree 안의 `--output` → `docs/diagram-<슬러그>` 브랜치에 커밋 |

`--source` 를 쓰면 **source 브랜치 자체는 건드리지 않는다.** 거기서 파생한 문서 전용
브랜치에 커밋하므로, 사용자는 그 브랜치를 보고 판단하면 된다.

산출물 디렉토리를 **하나의 절대경로로 확정**하고, 이 값을 아래에서 `<OUT_DIR>` 로 표기한다.

> **셸 변수를 쓰지 말 것.** Bash 호출마다 셸이 새로 뜨므로 변수는 다음 호출까지 살아남지 않는다.
> 빈 값으로 전개돼 `/` 아래에 쓰게 된다.
> 이후 모든 명령에는 확정한 절대경로를 **리터럴로 직접 써넣는다.**

## 실행 절차

### 0. Worktree 생성 (`--source` 지정 시)

`--source`가 지정된 경우, 격리된 worktree를 생성하여 해당 브랜치 코드 기준으로 분석한다.
미지정 시 이 단계를 건너뛰고 현재 디렉토리에서 분석한다.

`jira-tools:impl-issue` 1-1절과 같은 2단 구조를 쓴다:

```bash
# <slug> = source 브랜치명의 / 와 특수문자를 - 로 치환 (feat/x → feat-x)
# 스테일 worktree 자기 치유 (이전 실행이 중단돼 남아 있으면 제거)
git worktree remove --force /tmp/wt-diagram-<slug> 2>/dev/null; git worktree prune; rm -rf /tmp/wt-diagram-<slug>
# 1) detached HEAD로 worktree 생성 (브랜치 잠금 충돌 방지)
git worktree add --detach /tmp/wt-diagram-<slug> <source>

# 2) worktree로 이동하여 문서용 작업 브랜치 생성
cd /tmp/wt-diagram-<slug>
git checkout -b docs/diagram-<주제 슬러그>
```

- **1번의 `--detach` 를 빼지 않는다.** `<source>` 가 이미 다른 워크트리나 본체에
  체크아웃돼 있으면 `is already checked out at` 으로 실패한다
- **2번을 건너뛰지 않는다.** detached HEAD 에서 커밋하면 어느 ref에도 닿지 않는
  고아 커밋이 되어, worktree 제거와 함께 사라진다
- 경로에 `<slug>` 를 넣어 source 별로 분리한다. 고정 경로를 쓰면 동시에 돌린
  다른 분석의 산출물을 덮어쓴다
- 이후 모든 코드 읽기(Read, Grep, Glob)와 산출물 생성은 worktree 경로에서 수행한다

### 1. 코드 분석

대상 설명을 기반으로 관련 코드를 탐색한다:
- Grep/Glob으로 관련 클래스, 설정, 흐름 파악
- 필요시 Agent(Explore)로 깊은 탐색

### 2. 다이어그램 유형 결정

분석 대상에 맞는 Mermaid 다이어그램 유형을 선택한다:

| 대상 | 다이어그램 유형 |
|------|----------------|
| API 흐름, E2E | `sequenceDiagram` |
| 아키텍처, 토폴로지, 인프라 | `graph TB` / `graph LR` |
| 상태 변화 | `stateDiagram-v2` |
| 클래스 관계 | `classDiagram` |
| 프로세스, 워크플로우 | `flowchart` |

### 3. Markdown 문서 생성

출력 디렉토리에 `<주제>.md` 파일을 생성한다:
- Mermaid 코드 블록 포함
- 구성요소 설명 표
- 클래스/파일 위치 참조

다이어그램마다 **번호 · 제목 · 1줄 설명**을 정해 기록한다.
4절 PDF의 제목 바와 표지 목차가 이 값을 그대로 사용한다.

### 4. PDF 변환 (`--pdf` 플래그 시)

PDF는 `.md`와 같은 정보를 담은 **자립형 문서**여야 한다. 그림만 있는 PDF를 만들지 않는다.
다이어그램 장수에 따라 두 경로로 갈린다:

| 조건 | 페이지 구성 | 페이지 크기 |
|------|------------|------------|
| 1장 | 제목 바 + 다이어그램 (1p) | 콘텐츠 비율에 맞춘 가변 크기 |
| 2장 이상 | 표지 → 다이어그램 n p → 구성요소 표 | A3 가로 고정 (420×297mm) |

**PDF 병합 도구는 쓰지 않는다.** 모든 페이지를 하나의 HTML에 담아 puppeteer가 한 번에 렌더한다.

#### 4-1. Mermaid → SVG

다이어그램마다 실행한다:

```bash
npx --yes @mermaid-js/mermaid-cli -i <OUT_DIR>/<n>.mmd -o <OUT_DIR>/<n>.svg -b white
```

#### 4-2. SVG viewBox 파싱

```bash
grep -o 'viewBox="[^"]*"' <OUT_DIR>/<n>.svg | head -1
```

1장인 경우 여기서 얻은 width, height로 4-4의 페이지 크기를 계산한다.
2장 이상이면 페이지 크기가 고정이므로 이 단계는 건너뛴다.

#### 4-3. HTML 조립

모든 다이어그램 페이지에 높이 18mm의 제목 바를 넣는다:
- 상단 좌측: 섹션 번호 + 다이어그램 제목
- 상단 우측: 문서 제목 (2장 이상일 때만)
- 그 아래 1줄: 해당 다이어그램 설명

3절에서 정한 번호·제목·설명을 그대로 쓴다.

**SVG 높이는 반드시 제목 바를 뺀 값으로 준다.** `height:100vh`를 그대로 두면 제목 바 높이만큼
다이어그램 아래쪽이 잘린다. 아래 flex 레이아웃이 이를 자동으로 처리한다:

```css
html, body { margin:0; padding:0 }
.page { width:100vw; height:100vh; overflow:hidden; page-break-after:always;
        display:flex; flex-direction:column }
.page:last-child { page-break-after:auto }
.hdr  { flex:0 0 18mm; padding:0 6mm; border-bottom:1px solid #ddd;
        display:flex; flex-direction:column; justify-content:center }
.hdr h2 { margin:0; font:600 13pt/1.3 sans-serif }
.hdr p  { margin:1.5mm 0 0; font:10pt/1.3 sans-serif; color:#555 }
.body { flex:1 1 auto; min-height:0; display:flex;
        align-items:center; justify-content:center; padding:3mm }
/* mermaid-cli 가 SVG 루트에 style="max-width:<n>px" 를 인라인으로 박는다.
   !important 로 덮지 않으면 다이어그램이 페이지 폭을 못 채우고 작게 렌더된다. */
.body svg { width:100% !important; height:100% !important; max-width:none !important }
```

다이어그램이 2장 이상이면 앞뒤에 다음 페이지를 추가한다:

- **표지**: 문서 제목, 대상 설명, 분석 브랜치(`--source` 지정 시), 생성일, 목차(번호 + 다이어그램 제목)
- **말미**: 3절에서 만든 구성요소 설명 표와 클래스/파일 위치 참조를 HTML 표로 옮긴 페이지

#### 4-4. Puppeteer PDF

puppeteer 모듈 경로를 동적으로 찾는다:

```bash
find ~/.npm/_npx -name "puppeteer" -type d -maxdepth 5 2>/dev/null | head -1
```

```javascript
NODE_PATH=<puppeteer_path> node -e "
const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage();
  // cwd 에 의존하지 않도록 절대경로 리터럴을 쓴다 (셸 변수 금지)
  await page.goto('file://<OUT_DIR>/<tmp>.html', { waitUntil: 'networkidle0' });
  await page.pdf({
    path: '<OUT_DIR>/<주제>.pdf',
    width: '<W>mm',
    height: '<H>mm',
    printBackground: true,
    margin: { top: '3mm', bottom: '3mm', left: '3mm', right: '3mm' },
  });
  await browser.close();
})();
"
```

페이지 크기 계산 규칙:

- **1장**: viewBox의 긴 쪽을 420mm (A3 장축)로 맞추고 짧은 쪽은 비율대로 계산한 뒤,
  **높이에 제목 바 18mm를 더한다**
- **2장 이상**: 420×297mm 고정. 다이어그램은 `.body` 안에서 자동 축소되므로 페이지별 조정이 필요 없다
- 여백: 3mm (상하좌우)

#### 4-5. 임시 파일 정리

`<OUT_DIR>` 안의 `.mmd`, `.svg`, `.html` 임시 파일을 삭제한다. `.md`와 `.pdf`만 남긴다.

### 5. 커밋 & Worktree 정리 (`--source` 사용 시)

`--source` 를 쓰지 않았으면 이 단계를 건너뛴다 — 산출물만 남기고 커밋하지 않는다.

4-5의 임시 파일 정리를 **먼저** 끝낸 뒤 커밋한다. `.mmd`/`.svg`/`.html` 이 남아 있으면
`git status` 를 더럽히고 의도치 않게 스테이징된다.

```bash
git -C /tmp/wt-diagram-<slug> add <OUT_DIR 의 worktree 기준 상대경로>
git -C /tmp/wt-diagram-<slug> commit -m "docs: <주제> 다이어그램 추가"
git worktree remove /tmp/wt-diagram-<slug>
```

- 커밋이 `docs/diagram-<주제 슬러그>` 브랜치에 남으므로 worktree를 제거해도 유실되지 않는다
- **푸시하지 않는다.** 사용자가 브랜치를 확인한 뒤 판단한다
- `git worktree remove` 가 실패하면 정리 안 된 임시 파일이 남은 것이다.
  지우고 다시 시도한다

## 결과 안내

`--source` 사용 시 산출물이 로컬 워킹트리에 없으므로, 어디에 있는지 반드시 알린다:

```
docs/<주제>.md, docs/<주제>.pdf 를 생성했습니다.

  브랜치: docs/diagram-<주제 슬러그>  (<source> 에서 파생)
  확인:   git log -p docs/diagram-<주제 슬러그>
  체크아웃: git switch docs/diagram-<주제 슬러그>

현재 체크아웃된 브랜치는 건드리지 않았습니다. 푸시는 하지 않았습니다.
```

## 출력 예시

`--pdf` 없는 경우:
```
docs/<주제>.md          # Mermaid 다이어그램 포함 문서
```

`--pdf` 있는 경우:
```
docs/<주제>.md          # Mermaid 다이어그램 포함 문서
docs/<주제>.pdf         # 제목·설명·구성요소 표를 포함한 자립형 PDF
```

`--source` 를 함께 쓴 경우 위 파일들은 현재 워킹트리가 아니라
`docs/diagram-<주제 슬러그>` 브랜치의 커밋으로 남는다.
