# /figma-comment 사용법

`--help` / `-h` 로 호출됐을 때 아래 블록을 그대로 출력하고 종료한다.

```
/figma-comment - Figma 코멘트 조회/작성/삭제 (멘션 지원)

사용법:
  /figma-comment list <figma-url>                              코멘트 목록 조회
  /figma-comment list <figma-url> --unresolved                  미해결 코멘트만
  /figma-comment post <figma-url> <message>                     코멘트 작성 (REST API)
  /figma-comment post <figma-url> <message> --mention <email>   코멘트 작성 + @멘션 (playwright-cli)
  /figma-comment post <figma-url> <message> --reply <id>        답글 작성
  /figma-comment delete <figma-url> <comment-id>                코멘트 삭제
  /figma-comment                                                인터랙티브 모드
  /figma-comment --help                                         이 도움말 출력

옵션:
  --unresolved         미해결 코멘트만 조회
  --reply <id>         특정 코멘트에 답글 작성
  --mention <email>    @멘션 포함 (playwright-cli 모드 자동 전환)
  --node <nodeId>      코멘트를 달 정확한 노드 ID (예: 37485:24245)
  --offset <x>,<y>     노드 내 코멘트 핀 위치 (기본값: 0,0)

사전 조건:
  - ~/.figma-token 파일에 Figma Personal Access Token 저장
  - ~/.figma-session.json 파일에 브라우저 세션 상태 저장 (멘션 사용 시)
  - playwright-cli 설치 (npm install -g @playwright/cli)
```
