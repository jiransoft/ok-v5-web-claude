---
name: bump-version
description: 전체 플러그인 버전을 일괄 변경하고 커밋합니다
allowed-tools: Read, Edit, Grep, Glob, Bash(git *)
argument-hint: <새 버전 (예: 1.4.0)>
---

# Bump Version Skill

전체 플러그인의 버전을 일괄 업데이트한다.

## 버전 수정 대상

**개수를 외우지 말고 매번 실측한다.** 플러그인이 늘면 아래 숫자는 바로 낡는다:

```bash
cur=$(jq -r '.metadata.version' .claude-plugin/marketplace.json)
grep -rn --include='*.json' --include='*.md' -F "$cur" . | grep -v '^\./\.git/'
```

| 파일 | 역할 |
|------|------|
| `.claude-plugin/marketplace.json` | marketplace 인덱스 (`metadata.version` 1곳 + 각 `plugins[].version`) |
| `plugins/*/.claude-plugin/plugin.json` | 각 플러그인 정의 |
| `README.md` 테이블 | 사용자 문서 (Version 컬럼, 플러그인당 1곳) |

> 저장소 루트에는 `plugin.json` 이 없다. 버전은 위 세 갈래에만 있다.

## 절차

0. **정합성 게이트** — `python3 scripts/preflight.py --deep` 를 먼저 돌린다. 오류가 있으면
   버전을 올리지 않는다. 깨진 정합을 그대로 릴리즈하는 것이 가장 비싼 실수다.
1. `$ARGUMENTS`에서 새 버전 번호를 파싱한다. 없으면 사용자에게 묻는다.
2. 현재 버전을 확인한다:
   - `.claude-plugin/marketplace.json`의 `metadata.version` 값을 읽어 현재 버전으로 사용
   - 위 grep 으로 **총 출현 횟수를 먼저 센다** (치환 후 대조용)
3. 위에서 찾은 모든 위치의 버전을 현재 버전 → 새 버전으로 일괄 변경한다.
   개수를 가정하지 말고 2번에서 센 만큼 바뀌었는지 확인한다.
4. README.md 내용을 실제 스킬/설정과 동기화한다:
   - 각 플러그인의 SKILL.md에서 `plugins.json` 관련 설정 키를 추출한다
   - README.md의 **설정 파일 예시** (`plugins.json` jsonc 블록)와 **플러그인별 필요 설정 테이블**이 실제 SKILL.md와 일치하는지 대조한다
   - 새로 추가되거나 삭제된 설정 키가 있으면 README.md를 업데이트한다
   - 플러그인 테이블의 Description, Skills 컬럼도 각 플러그인의 `plugin.json`, SKILL.md와 대조하여 불일치가 있으면 업데이트한다
5. 변경 결과를 검증한다:
   - `grep`으로 전체 json/md 파일에서 이전 버전이 남아있지 않은지 확인
   - `grep`으로 새 버전이 올바르게 반영되었는지 확인
6. 검증 통과 시 변경 파일을 스테이징하고 커밋한다:
   - 커밋 메시지: `chore: 전체 플러그인 버전 {새 버전}으로 업데이트`
7. git tag를 생성한다:
   - 태그명: `v{새 버전}` (예: `v1.4.1`)
   - `git tag v{새 버전}`
8. 커밋과 태그를 푸시한다:
   - `git push && git push --tags`

## 주의사항

- README.md에 버전이 박힌 경로(예: `<plugin>/1.x.x/scripts/`)가 있으면 함께 업데이트한다
- 버전 형식은 semver (`x.y.z`)를 따른다
- 이전 버전이 잔존하는 파일이 있으면 커밋 전에 경고한다
- 0단계 `preflight --deep` 이 `lint-skills.py` 를 포함해 돌린다. 별도로 다시 돌릴 필요는 없다
  (오류가 있으면 릴리즈하지 않는다 — 경고는 판단 대상)
