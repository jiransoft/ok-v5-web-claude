# /release-note 사용법

`--help` / `-h` 로 호출됐을 때 아래 블록을 그대로 출력하고 종료한다.

```
/release-note - GitHub Release Note 생성

사용법:
  /release-note 5.0.5.0-alpha.6                           이전 태그 자동 감지
  /release-note 5.0.5.0-alpha.6 --base 5.0.5.0-alpha.5    이전 태그 직접 지정
  /release-note 5.0.5.0-alpha.6 --no-base                 이전 태그 비교 없이 전체 API 스냅샷
  /release-note 5.0.5.0-alpha.6 --dry-run                 릴리즈 생성 없이 미리보기만
  /release-note --help                                     이 도움말 출력

옵션:
  <source-tag>               릴리즈 대상 태그 (필수)
  --base <tag>                비교 기준 이전 태그. 미지정 시 직전 태그 자동 감지.
  --no-base                   이전 태그 비교 생략(스냅샷 모드). source-tag의 전체 API 목록을 출력. --base와 상호 배타
  --dry-run                   릴리즈 생성 없이 미리보기만 출력

Swagger 링크는 .claude/plugins.json의 release-tools.swaggerBaseUrl 설정으로 자동 생성됩니다.
```
