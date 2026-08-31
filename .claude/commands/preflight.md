---
name: preflight
description: 배포 전 레포 정합성을 대조합니다 (버전·등록·매니페스트·문서·스킬 참조)
allowed-tools: Read, Grep, Bash(python3 *), Bash(git *)
argument-hint: "[--deep]"
---

# Preflight

이 저장소 전용 게이트다. **사용자에게 배포되지 않는다** — 사용자 환경 진단은 `doctor` 플러그인의
`/doctor:check` 이고, 이쪽은 레포 안의 파일들이 서로 어긋났는지만 본다.

## 실행

```bash
python3 scripts/preflight.py --deep
```

`$ARGUMENTS` 가 비어 있어도 `--deep` 을 붙인다. `--deep` 은 `lint-skills.py` 와 훅 selfTest 까지 돌린다.

| 종료코드 | 의미 |
|----------|------|
| `0` | 정상 |
| `1` | 경고만 |
| `2` | 오류 — 이 상태로 릴리즈하지 않는다 |

## 검사 항목

| 영역 | 대조 대상 |
|------|-----------|
| `version` | `marketplace.metadata.version` ↔ 각 `plugins[].version` ↔ 각 `plugin.json` ↔ README 표 |
| `registration` | `plugins/*` 디렉토리 ↔ marketplace 항목(`name`·`source`) ↔ `plugin.json.name` |
| `manifest` | `doctor.json` ↔ 실제 스킬 선언 — `allowed-tools` 의 CLI, `mcp__*` 서버, setup 예시의 설정 키, 훅 경로, setup 명령 |
| `readme` | 플러그인 표·전체 설치 목록·필요 설정 표 ↔ 실제 |
| `reference` | 문서·매니페스트에 적힌 `/플러그인:스킬` 이 실존하는지 |
| `lint` `hook` | `--deep` 에서 `lint-skills.py` 에러 0 · 훅 selfTest 통과 |

`lint-skills.py` 는 SKILL.md **구조**를, 이 스크립트는 파일 **사이의 정합**을 본다. 겹치지 않는다.

## 언제 돌리나

- **`/bump-version` 직전** — 버전을 올리기 전에 정합이 깨져 있으면 그 상태가 릴리즈된다
- 플러그인 추가·개명·삭제 직후
- `doctor.json` 을 손댔을 때 (매니페스트가 실제 선언과 어긋나면 사용자 진단이 거짓말을 한다)

## 결과 처리

- **오류는 고치고 다시 돌린다.** 통과 못 한 상태로 태그·푸시하지 않는다
- 경고는 판단 대상이다. 의도한 불일치면 그 이유를 커밋 메시지에 남긴다
- 스크립트가 틀렸을 수도 있다 — 검출이 사실과 다르면 `scripts/preflight.py` 를 고친다.
  결함을 심어 검출되는지 확인하는 방식으로 검사기 자체를 검증한다
- 매니페스트를 문서에 맞추지 말고 **실제 스킬 선언에 맞춘다**. README 가 낡은 쪽인 경우가 많다
