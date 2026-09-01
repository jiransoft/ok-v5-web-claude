# /create-pr 사용법

`--help` / `-h` 로 호출됐을 때 아래 블록을 그대로 출력하고 종료한다.

```
/create-pr - GitHub Pull Request 생성

사용법:
  /create-pr                                           타겟/소스 자동 감지하여 PR 생성
  /create-pr --target develop                          타겟 지정
  /create-pr --source feature/abcd --target develop    소스와 타겟 지정
  /create-pr --target develop --base feature/x         타겟은 develop, diff 분석은 feature/x 기준
  /create-pr --target develop -a <username>            assignee 지정
  /create-pr --target develop -r <username>            reviewer 지정
  /create-pr --target develop -l D-1                   라벨 지정
  /create-pr --target develop -i                       인터랙티브 모드
  /create-pr --help                                    이 도움말 출력

옵션:
  --source <branch>           소스 브랜치 지정 (PR의 출발점)
                              미지정 시 현재 브랜치를 사용한다.
  --target <branch>           타겟 브랜치 지정 (PR의 도착점, base)
                              미지정 시 merge-base 거리로 자동 감지한다.
  --base <branch>             diff 분석 기준 브랜치 지정
                              PR body 작성 시 이 브랜치와의 차이만 분석한다.
                              PR 타겟은 --target으로 유지된다.
                              미지정 시 --target 브랜치를 기준으로 분석한다.
  -a, --assignee <username>   PR 담당자 지정 (1명)
                              미지정 시 .claude/plugins.json의 기본 Assignee 사용. 없으면 질문
  -r, --reviewer <username>   PR 리뷰어 지정 (1명)
                              미지정 시 .claude/plugins.json의 기본 Reviewer 사용. 없으면 질문
  -l, --label <label>         PR 라벨 지정 (복수: 쉼표 구분)
                              미지정 시 .claude/plugins.json의 기본 Label 사용. 없으면 질문
  -i, --interactive           인터랙티브 모드: 저장소 멤버/라벨 목록을 보여주고
                              assignee/reviewer/label을 선택하게 한다

예시:
  /create-pr --target develop                              기본 assignee로 PR 생성
  /create-pr --target develop -r someone                   리뷰어 지정하여 PR 생성
  /create-pr --target develop -l D-1                       라벨 지정하여 PR 생성
  /create-pr --target develop -l "D-1,After Merged"        복수 라벨 지정
  /create-pr --target develop -a user1 -r user2 -l D-0    전체 옵션 지정
  /create-pr --target develop -i                           멤버/라벨 목록에서 선택
  /create-pr --source feature/abcd --target develop        다른 브랜치를 소스로 PR 생성
  /create-pr --target develop --base feature/PROJ-100      타겟은 develop, 분석은 feature/PROJ-100 기준

동작:
  1. gh 인증 확인
  2. 현재 브랜치 검증 (main/develop에서는 생성 불가)
  3. 타겟 브랜치 결정 (--target 미지정 시 merge-base 거리로 자동 감지)
     + base 브랜치 결정 (--base 미지정 시 타겟 브랜치 사용)
  4. 변경사항 분석 (base 브랜치 기준 git log/diff)
  5. 템플릿 선택(feature/default) → PR 본문·제목 작성 → 사용자 확인
  6. Assignee/Reviewer 결정
  7. 리모트에 push → 사용자 확인
  8. gh pr create로 PR 생성 (타겟 브랜치를 base로 PR 생성)
  9. PR URL 출력

사전 조건:
  - 저장소 origin 이 GitHub 일 것
  - gh CLI 설치 (brew install gh)
  - GitHub 인증 완료 (gh auth login, 또는 GH_TOKEN 환경변수)
```
