---
name: diagram
description: 코드를 분석하여 Mermaid 다이어그램 문서를 생성합니다. 아키텍처, 시퀀스, 플로우차트 등을 자동 선택하고, --pdf 시 콘텐츠 크기에 맞춘 PDF도 만듭니다.
when_to_use: 사용자가 "다이어그램 그려줘", "아키텍처 도식화해줘", "시퀀스 다이어그램 만들어줘", "이 흐름 플로우차트로 그려줘", "구조도 만들어줘", "draw diagram", "Mermaid 다이어그램" 등 코드를 분석해 아키텍처·시퀀스·플로우차트 등을 그림으로 정리하려 할 때.
allowed-tools: Bash(git *), Bash(npx *), Read, Grep, Glob, Write, Edit, Agent
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

## 실행 절차

### 0. Worktree 생성 (`--source` 지정 시)

`--source`가 지정된 경우, 격리된 worktree를 생성하여 해당 브랜치 코드 기준으로 분석한다.
미지정 시 이 단계를 건너뛰고 현재 디렉토리에서 분석한다.

```bash
# 스테일 worktree 자기 치유 (이전 실행이 중단돼 남아 있으면 제거)
git worktree remove --force /tmp/wt-diagram 2>/dev/null; git worktree prune; rm -rf /tmp/wt-diagram
git worktree add --detach /tmp/wt-diagram <source>
```

- 이후 모든 코드 읽기(Read, Grep, Glob)는 worktree 경로(`/tmp/wt-diagram`)에서 수행한다
- 문서/PDF 출력은 원래 repo의 `--output` 경로에 생성한다
- 작업 완료 후 worktree를 정리한다:
  ```bash
  git worktree remove /tmp/wt-diagram
  ```

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

### 4. PDF 변환 (`--pdf` 플래그 시)

아래 절차로 PDF를 생성한다:

#### 4-1. Mermaid → SVG

```bash
npx --yes @mermaid-js/mermaid-cli -i <input>.mmd -o <output>.svg -b white
```

#### 4-2. SVG viewBox 파싱

```bash
grep -o 'viewBox="[^"]*"' <output>.svg | head -1
```

viewBox에서 width, height를 추출하여 비율을 계산한다.

#### 4-3. HTML 래핑 → Puppeteer PDF

puppeteer 모듈 경로를 동적으로 찾는다:

```bash
find ~/.npm/_npx -name "puppeteer" -type d -maxdepth 5 2>/dev/null | head -1
```

SVG를 HTML로 래핑하고, viewBox 비율에 맞춘 커스텀 페이지 크기로 PDF를 생성한다:

```javascript
NODE_PATH=<puppeteer_path> node -e "
const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

(async () => {
  const svgContent = fs.readFileSync('<output>.svg', 'utf8');
  // viewBox에서 추출한 width, height로 mm 단위 페이지 크기 계산
  // 기준: 긴 쪽을 420mm (A3)로 맞추고 비율 유지
  const html = '<!DOCTYPE html><html><head><meta charset=\"utf-8\">' +
    '<style>html,body{margin:0;padding:0;overflow:hidden}svg{display:block;width:100vw;height:100vh}</style>' +
    '</head><body>' + svgContent + '</body></html>';

  fs.writeFileSync('<tmp>.html', html);

  const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.goto('file://' + path.resolve('<tmp>.html'), { waitUntil: 'networkidle0' });
  await page.pdf({
    path: '<output>.pdf',
    width: '<계산된 width>mm',
    height: '<계산된 height>mm',
    printBackground: true,
    margin: { top: '3mm', bottom: '3mm', left: '3mm', right: '3mm' },
  });
  await browser.close();
})();
"
```

페이지 크기 계산 규칙:
- viewBox의 긴 쪽을 420mm (A3 장축)로 기준
- 짧은 쪽은 비율에 따라 자동 계산
- 여백: 3mm (상하좌우)

#### 4-4. 임시 파일 정리

`.mmd`, `.svg`, `.html` 임시 파일을 삭제한다. `.md`와 `.pdf`만 남긴다.

## 출력 예시

`--pdf` 없는 경우:
```
docs/<주제>.md          # Mermaid 다이어그램 포함 문서
```

`--pdf` 있는 경우:
```
docs/<주제>.md          # Mermaid 다이어그램 포함 문서
docs/<주제>.pdf         # 콘텐츠에 꽉 맞는 PDF
```