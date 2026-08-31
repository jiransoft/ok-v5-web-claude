---
name: adr
description: 코드를 분석하여 Architecture Decision Record(설계 의사결정 문서)를 생성합니다. 인수인계/온보딩/향후 확장 참고용.
when_to_use: 사용자가 "ADR 만들어줘", "설계 의사결정 문서 작성해줘", "이 구조 왜 이렇게 짰는지 정리해줘", "아키텍처 결정 기록 남겨줘", "create ADR", "architecture decision record" 등 특정 설계의 배경·대안·확장 방향을 문서로 정리하려 할 때.
allowed-tools: Bash(git *), Read, Grep, Glob, Write, Edit, Agent
argument-hint: <대상 설명> [--source <branch>] [--output <path>] [--status <status>] [--with-diagram]
---

# ADR (Architecture Decision Record) Skill

코드를 분석하여 설계 의사결정 문서를 생성한다. "왜 이렇게 만들었는가", "대안은 뭐였는가", "향후 어떻게 확장하는가"를 정리한다.

## --help 처리

`$ARGUMENTS`가 `--help` 또는 `-h` 면 [reference/usage.md](reference/usage.md) 의 사용법 블록을 그대로 출력하고 즉시 종료한다.

## 인자 파싱

- `$ARGUMENTS`에서 플래그 추출:
  - `--source <branch>` → 분석할 브랜치 (미지정 시 현재 브랜치)
  - `--output <path>` → 출력 디렉토리 (기본: `docs/`)
  - `--status <status>` → 문서 상태 (기본: `Accepted`)
  - `--with-diagram` → Mermaid 다이어그램 포함 여부
- 나머지 텍스트 → ADR 대상 설명

## 실행 절차

### 0. Worktree 생성 (`--source` 지정 시)

`--source`가 지정된 경우, 격리된 worktree를 생성하여 해당 브랜치 코드 기준으로 분석한다.
미지정 시 이 단계를 건너뛰고 현재 디렉토리에서 분석한다.

```bash
# 스테일 worktree 자기 치유 (이전 실행이 중단돼 남아 있으면 제거)
git worktree remove --force /tmp/wt-adr 2>/dev/null; git worktree prune; rm -rf /tmp/wt-adr
git worktree add --detach /tmp/wt-adr <source>
```

- 이후 모든 코드 읽기(Read, Grep, Glob)는 worktree 경로(`/tmp/wt-adr`)에서 수행한다
- 문서 출력은 원래 repo의 `--output` 경로에 생성한다
- 작업 완료 후 worktree를 정리한다:
  ```bash
  git worktree remove /tmp/wt-adr
  ```

### 1. 코드 분석

대상 설명을 기반으로 관련 코드를 탐색한다:

- Grep/Glob으로 관련 클래스, 설정, 인터페이스 파악
- 필요시 Agent(Explore)로 의존 관계, 호출 흐름 추적
- 설정 파일 (application.properties, build.gradle 등) 확인

### 2. 설계 의사결정 포인트 식별

코드에서 다음을 추출한다:

- **어떤 패턴/기술을 선택했는가** (예: WATCH/MULTI/EXEC, Outbox 패턴)
- **왜 그 선택을 했는가** (성능, 정합성, 단순성 등)
- **어떤 대안이 있었는가** (업계 사례 포함)
- **어떤 트레이드오프가 있는가** (알려진 한계)

### 3. 문서 생성

아래 포맷으로 Markdown 파일을 생성한다.

#### 파일명 규칙

`<날짜>-<kebab-case-제목>.md`

예: `2026-03-23-redis-atomicity-and-scaling.md`

#### 문서 포맷

```markdown
# [제목]

> ADR: [한 줄 요약]

## Status

[Accepted | Proposed | Deprecated | Superseded by [링크]]

## Context

왜 이 설계가 필요했는가.

- 해결하려는 문제
- 요구사항과 제약조건
- 기존 시스템과의 관계

## Decision

무엇을 선택했는가.

- 현재 구현 방식 설명
- 핵심 동작 원리 (코드 흐름 포함)
- 적용 위치 (클래스, 패키지)

## Alternatives Considered

검토한 대안과 비교.

| 대안 | 장점 | 단점 | 탈락 사유 |
|------|------|------|----------|
| ... | ... | ... | ... |

## Consequences

현재 구현의 결과.

- 장점 / 얻은 것
- 단점 / 트레이드오프
- 알려진 한계

## Scaling Strategy

향후 확장 로드맵.

| 단계 | 시점 | 전략 | 변경 범위 |
|------|------|------|----------|
| 현재 | ... | ... | ... |
| 다음 | ... | ... | ... |

## References

관련 파일 위치.

| 파일 | 역할 |
|------|------|
| ... | ... |
```

### 4. 다이어그램 포함 (`--with-diagram`)

`--with-diagram` 플래그가 있으면:

- 구현 흐름에 맞는 Mermaid 다이어그램을 문서 내 `## Decision` 또는 별도 섹션에 포함
- 다이어그램 유형은 대상에 맞게 자동 선택:
  - 데이터 흐름 → `sequenceDiagram`
  - 아키텍처/토폴로지 → `graph TB` / `graph LR`
  - 상태 변화 → `stateDiagram-v2`
  - 비교/분기 → `flowchart`

## 작성 원칙

- **Why 중심**: 코드가 What을 말해주므로, 문서는 Why와 트레이드오프에 집중한다
- **대안 비교 필수**: "왜 A를 선택했는가"는 "왜 B를 선택하지 않았는가"와 함께 설명해야 의미가 있다
- **업계 사례 참조**: 대안 비교 시 Netflix, Stripe 등 대규모 서비스의 접근법을 참고로 포함한다
- **확장 로드맵 포함**: 현재 결정이 향후 어떤 시점에 재검토되어야 하는지 명시한다
- **코드 위치 명시**: 후임자가 관련 코드를 바로 찾을 수 있도록 클래스/파일 경로를 References에 정리한다
- **서브에이전트 결과 검증**: Explore 등 서브에이전트의 분석 결과를 그대로 수용하지 않는다. 핵심 주장은 반드시 코드를 직접 읽어서 검증한다. 검증되지 않은 내용은 "확인된 사실"과 구분하여 "추정 — 추가 확인 필요"로 표기한다