# /verify-stack 사용법

`--help` / `-h` 로 호출됐을 때 아래 블록을 그대로 출력하고 종료한다.

```
/verify-stack - Jira 이슈/브랜치별 포트 블록으로 검증 스택 기동 + 브라우저 검증

사용법:
  /verify-stack PROJ-1234                       이슈 검증 스택 기동 (기존 worktree 탐색)
  /verify-stack PROJ-1234 --source develop      그 브랜치에서 detached worktree를 따서 기동
  /verify-stack 1234                             이슈번호만으로 기동 (projectKey는 설정에서)
  /verify-stack --source feature/xxx             브랜치 모드 — 이슈 없이 브랜치 커밋 분석으로 검증
  /verify-stack --help                           이 도움말 출력

옵션:
  --source <branch>     그 브랜치로부터 detached worktree 생성 (checkout 안 함,
                        사용자 작업 트리 무영향). 이슈 모드에서 미지정 시 기존
                        worktree 탐색 → 없으면 브랜치 재질의. 브랜치 모드(이슈키
                        없음)에서는 필수

동작:
  1. 포트 블록 계산 — portBase + 슬롯×1000 + 오프셋, 선점 검사
     (오프셋: 이슈 모드 이슈번호%1000 / 브랜치 모드 cksum(브랜치명)%1000)
  2. worktree 해석·준비 (prepare 명령으로 의존성·로컬 설정 구성)
  3. 모듈 병렬 기동 (plugins.json의 modules 설정)
  4. 헬스 폴링으로 준비 완료 실측
  5. 검증 시나리오 도출 — 이슈 모드: Jira 설명+댓글 /
     브랜치 모드: 브랜치 고유 커밋 분석 → 시나리오 보고 → 사용자 리뷰 승인 후 진행
  6. 브라우저 검증 (이슈/브랜치별 context 격리) 후 항목별 통과/실패 보고
  7. 정리 — 프로세스 종료·worktree 제거 (사용자 확인 후)

필요 설정 (.claude/plugins.json → "runtime-verify"):
  modules(필수), projectKey, credentialsFile, portBase, worktreeBase, ui, prepare
```
