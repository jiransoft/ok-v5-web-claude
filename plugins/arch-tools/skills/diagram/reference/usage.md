# /diagram 사용법

`--help` / `-h` 로 호출됐을 때 아래 블록을 그대로 출력하고 종료한다.

```
/diagram - 코드 분석 → Mermaid 다이어그램 생성

사용법:
  /diagram <대상 설명>                    Mermaid 다이어그램을 .md에 포함하여 생성
  /diagram <대상 설명> --source feat/x    특정 브랜치 코드 기준으로 분석
  /diagram <대상 설명> --pdf              추가로 PDF 파일도 생성
  /diagram <대상 설명> --output docs/     출력 경로 지정 (기본: docs/)

예시:
  /diagram 부서 생성 E2E 시퀀스
  /diagram RabbitMQ 전체 토폴로지 --pdf
  /diagram 인증 플로우 --output docs/auth/
  /diagram 결제 흐름 --source feat/payment-v2
```
