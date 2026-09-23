# archify 엔진 벤더링 정보

이 디렉터리는 `scripts/sync-archify.sh` 가 생성한다. **손으로 고치지 않는다.** 고칠 것이 있으면
업스트림에 기여하거나, 스크립트의 제외 목록·후처리에 넣는다.

| 항목 | 값 |
|------|-----|
| 업스트림 | https://github.com/tt-a1i/archify |
| 요청 참조 | `8809b273c278a813a47fa37698864779c0d4cf08` |
| 커밋 SHA | `8809b273c278a813a47fa37698864779c0d4cf08` |
| 업스트림 버전 | `2.17.0-dev.1` (package.json) |
| 가져온 방법 | clone+stage |
| 동기화 시각 | 2026-09-23T05:01:02Z |
| 파일 수 / 크기 | 71 / 2468 KB |
| 라이선스 | MIT (`LICENSE`), 서드파티 고지 `THIRD_PARTY_NOTICES.md`, 폰트 `assets/JetBrainsMono-OFL.txt` |

## 업스트림 배포본에서 제외한 파일

| 파일 | 이유 |
|------|------|
| `examples/dataflow-product-analytics.html` | 렌더된 예제 HTML 약 800KB. JSON 예제만 있어도 doctor·validate·deliver 가 동작한다 |
| `examples/lifecycle-agent-run.html` | 렌더된 예제 HTML 약 800KB. JSON 예제만 있어도 doctor·validate·deliver 가 동작한다 |
| `examples/sequence-cache-miss-request.html` | 렌더된 예제 HTML 약 800KB. JSON 예제만 있어도 doctor·validate·deliver 가 동작한다 |
| `examples/web-app-rendered.html` | 렌더된 예제 HTML 약 800KB. JSON 예제만 있어도 doctor·validate·deliver 가 동작한다 |
| `examples/workflow-agent-tool-call-rendered.html` | 렌더된 예제 HTML 약 800KB. JSON 예제만 있어도 doctor·validate·deliver 가 동작한다 |
| `scripts/check-update.mjs` | 업데이트 알림 체커. 유일한 네트워크 호출 경로라 제거해 오프라인을 보장한다 |
| `scripts/update-contract.mjs` | 업데이트 알림 체커. 유일한 네트워크 호출 경로라 제거해 오프라인을 보장한다 |
| `skill-release.json` | 업데이트 알림 체커. 유일한 네트워크 호출 경로라 제거해 오프라인을 보장한다 |

## 로컬 패치

없음. 벤더 파일은 업스트림 배포본과 바이트 단위로 같다.

## 재동기화

```bash
scripts/sync-archify.sh v2.17.0          # 안정 태그 (릴리즈 zip 사용)
scripts/sync-archify.sh <40자 SHA>       # 특정 커밋 (클론 + stage-clean-skill)
python3 scripts/lint-skills.py && python3 scripts/preflight.py --deep
node plugins/arch-tools/archify/bin/archify.mjs doctor
```

매주 월요일 09:00 KST 에 `.github/workflows/sync-archify.yml` 이 최신 안정 태그를 확인하고,
새 버전이면 같은 절차로 동기화 PR 을 연다.

## 주의

- `archify examples` 명령은 이 디렉터리의 `examples/` 에 HTML 4MB 를 다시 쓴다. 스킬에서 호출하지 않는다.
- 뷰어 UI 로케일은 `en`·`zh-CN` 만 있다. 한글 다이어그램은 `meta.locale` 을 생략해 영어 UI 로 폴백한다.
