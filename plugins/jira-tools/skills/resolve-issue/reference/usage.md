# /resolve-issue 사용법

`--help` / `-h` 로 호출됐을 때 아래 블록을 그대로 출력하고 종료한다.

```
/resolve-issue - Jira 이슈 분석 및 댓글 등록

사용법:
  /resolve-issue PROJ-123                                     이슈 키로 분석
  /resolve-issue PROJ-123 --source main                        특정 브랜치 기준으로 분석
  /resolve-issue https://xxx.atlassian.net/browse/PROJ-123     URL로 분석
  /resolve-issue                                               대화형으로 이슈 입력
  /resolve-issue --help                                        이 도움말 출력

옵션:
  --source <branch>      지정한 브랜치의 코드 기준으로 분석 (worktree 격리)
                        미지정 시 현재 디렉토리에서 분석

동작:
  1. Jira 이슈 조회
  2. Worktree 생성 (--source 지정 시)
  3. 코드베이스 분석 (원인 파악)
  4. 분석 결과 댓글 등록 (초안 전문 확인 후)
  5. 이슈 상태를 '확인중'으로 전환
  6. AI 라벨 추가
  7. Worktree 정리 (--source 사용 시)
```
