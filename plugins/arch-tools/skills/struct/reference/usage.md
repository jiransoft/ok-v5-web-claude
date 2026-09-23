# /struct 사용법

`--help` / `-h` 로 호출됐을 때 아래 블록을 그대로 출력하고 종료한다.

```
/struct - 코드 분석 → 인터랙티브 HTML 다이어그램 (archify 엔진)

사용법:
  /struct <대상 설명>                          코드를 분석해 HTML + JSON 소스 생성 (기본 docs/)
  /struct <대상 설명> --type sequence          타입 지정: architecture|workflow|sequence|dataflow|lifecycle
  /struct <대상 설명> --describe               코드 분석 없이 설명만으로 작성
  /struct <대상 설명> --source feat/x          특정 브랜치 코드 기준으로 분석 → docs/struct-<슬러그> 브랜치에 커밋
  /struct <대상 설명> --output docs/arch/      출력 경로 지정 (기본: docs/)

예시:
  /struct 부서 생성 요청 흐름
  /struct RabbitMQ 토폴로지 --type architecture
  /struct 주문 상태 전이 --type lifecycle --source feat/order-v2
  /struct "브라우저 → API → Redis 캐시 미스 → PostgreSQL" --describe --type sequence

산출물:
  docs/<주제>.html           자립형 인터랙티브 HTML. 더블클릭으로 열림, 네트워크 불필요
  docs/<주제>.<type>.json    수정용 JSON 소스. 고쳐서 다시 요청하면 부분 수정 가능

Mermaid 문서·PDF 는 /arch-tools:diagram, 설계 의사결정 기록은 /arch-tools:adr 을 쓴다.
```
