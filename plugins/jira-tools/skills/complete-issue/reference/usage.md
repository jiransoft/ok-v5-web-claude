# /complete-issue 사용법

`--help` / `-h` 로 호출됐을 때 아래 블록을 그대로 출력하고 종료한다.

```
/complete-issue - 구현 완료 이슈의 실동작 검증 및 보고

사용법:
  /complete-issue PROJ-123                                  이슈 키로 검증 (브랜치 자동 추론)
  /complete-issue PROJ-123 --source feature/PROJ-123        검증할 브랜치 직접 지정
  /complete-issue https://xxx.atlassian.net/browse/PROJ-123 URL로 검증
  /complete-issue --help                                    이 도움말 출력

옵션:
  --source <branch>      검증할 브랜치를 직접 지정
                         미지정 시 이슈 키·커밋·기존 댓글에서 추론해 승인을 받는다

동작:
  1. 사전 점검 (pandoc · runtime-verify 설정)
  2. 검증 대상 브랜치 결정 (자동 추론 후 승인)
  3. 이슈·댓글 조회 — resolve/impl 댓글에서 원인·수정 원본 수집
  4. 커밋 diff 교차 검증 — 댓글과 코드가 어긋나면 보고
  5. detached worktree 에서 모듈 병렬 기동 (이슈번호 파생 포트)
  6. 브라우저 검증 + 증거 수집 (스크린샷 → API 응답 → 로그 순)
  7. [원인] [수정] [결과] 3항목 보고용 댓글 초안
  8. 초안 전문 확인
  9. 스크린샷을 이슈 첨부로 업로드
  10. 댓글 등록 (첨부 이미지 인라인 렌더)
  11. 상태 전환 — statusCategory 로 판별 (통과→done, 실패→indeterminate)
  12. AI 라벨 추가
  13. 런타임·worktree 정리

전제:
  구현과 커밋이 끝나 있어야 한다. 이 스킬은 코드를 고치지 않는다.
  검증에 실패하면 보고하고 멈춘다 — 수정은 /impl-issue 로 다시 돈다.

필요 설정:
  jira-tools     baseUrl · email · apiTokenFile
                 transitions (선택) — 상태 전환 이름 고정. 미지정 시 statusCategory 로 자동 판별
  runtime-verify modules (기동할 모듈), ui · credentialsFile (브라우저 검증 시)
```
