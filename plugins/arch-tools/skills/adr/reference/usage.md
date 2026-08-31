# /adr 사용법

`--help` / `-h` 로 호출됐을 때 아래 블록을 그대로 출력하고 종료한다.

```
/adr - Architecture Decision Record 생성

코드를 분석하여 설계 의사결정 문서를 생성한다.
인수인계, 온보딩, 향후 확장 시 참고할 수 있는 기술 문서.

사용법:
  /adr <대상 설명>                        ADR 문서 생성
  /adr <대상 설명> --source feat/x        특정 브랜치 코드 기준으로 분석
  /adr <대상 설명> --output docs/adr/     출력 경로 지정 (기본: docs/)
  /adr <대상 설명> --status Proposed      문서 상태 지정 (기본: Accepted)
  /adr <대상 설명> --with-diagram         Mermaid 다이어그램 포함

예시:
  /adr Redis 원자적 연산 설계
  /adr Outbox 패턴 선택 이유
  /adr 멀티테넌시 데이터소스 라우팅 --with-diagram
  /adr Rate Limiting 전략 --status Proposed
  /adr 인증 미들웨어 설계 --source feat/auth-refactor
```
