# /impl-issue 사용법

`--help` / `-h` 로 호출됐을 때 아래 블록을 그대로 출력하고 종료한다.

```
/impl-issue - Jira 이슈 분석 및 TDD 구현

사용법:
  /impl-issue PROJ-123                                     이슈 키로 구현
  /impl-issue PROJ-123 --source main                        특정 브랜치 기준으로 구현
  /impl-issue https://xxx.atlassian.net/browse/PROJ-123     URL로 구현
  /impl-issue                                               대화형으로 이슈 입력
  /impl-issue --help                                        이 도움말 출력

옵션:
  --source <branch>      지정한 브랜치 기준으로 worktree를 생성하여 구현
                        자동으로 {prefix}/{이슈키} 브랜치를 생성하여 작업
                        미지정 시 현재 디렉토리에서 구현

동작:
  1. Jira 이슈 조회 (댓글 포함)
  2. Worktree 생성 (--source 지정 시)
  3. 코드베이스 분석 (원인/구현 방향 파악)
  4. 구현 계획 수립 및 사용자 확인
  5. 이슈 상태를 '진행 중'으로 전환
  6. TDD 방식으로 구현 (Red → Green → Refactor)
  7. 코드 리뷰
  8. 커밋
  9. 구현 결과 댓글 등록 (초안 전문 확인 후)
  10. 이슈 상태를 '확인중'으로 전환
  11. AI 라벨 추가
  12. Worktree 정리 (--source 사용 시)
```
