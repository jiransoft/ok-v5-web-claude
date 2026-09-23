#!/usr/bin/env bash
# archify 엔진(https://github.com/tt-a1i/archify)을 plugins/arch-tools/archify/ 로 벤더링한다.
#
# 사용법:
#   scripts/sync-archify.sh <tag|sha>        예) scripts/sync-archify.sh v2.17.0
#                                            예) scripts/sync-archify.sh 8809b27
#
# 동작:
#   1. 태그(vX.Y.Z)면 릴리즈 자산 archify.zip 을 내려받아 푼다. 업스트림 CI 가 zip 과
#      소스 트리의 일치를 검증하므로 업스트림 스크립트를 실행하지 않아도 된다.
#      zip 이 없거나 SHA 를 받았으면 클론한 뒤 업스트림의 stage-clean-skill.mjs 로
#      배포 파일만 골라낸다 (테스트·lockfile·생성기 제외, package.json 정리).
#   2. 우리 제외 목록을 적용한다: 렌더된 예제 HTML 5개, 업데이트 체커 3파일.
#      → 저장소 용량 4MB 절약, 네트워크 호출 경로 0.
#   3. rsync --delete 로 plugins/arch-tools/archify/ 를 갱신하고 UPSTREAM.md 를 새로 쓴다.
#
# 저장소 개발자용 도구다. 플러그인 사용자에게는 배포되지 않는다.
# 실행 후 반드시: python3 scripts/lint-skills.py && python3 scripts/preflight.py --deep
set -euo pipefail

UPSTREAM_URL="https://github.com/tt-a1i/archify"
UPSTREAM_GIT="${UPSTREAM_URL}.git"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
DEST="${REPO_ROOT}/plugins/arch-tools/archify"

# 우리 제외 목록 — 이유는 UPSTREAM.md 에 기록된다
EXCLUDE_FILES=(
  "examples/dataflow-product-analytics.html"
  "examples/lifecycle-agent-run.html"
  "examples/sequence-cache-miss-request.html"
  "examples/web-app-rendered.html"
  "examples/workflow-agent-tool-call-rendered.html"
  "scripts/check-update.mjs"
  "scripts/update-contract.mjs"
  "skill-release.json"
)

usage() {
  sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

die() {
  echo "sync-archify: $*" >&2
  exit 1
}

REF="${1:-}"
[[ -z "$REF" || "$REF" == "-h" || "$REF" == "--help" ]] && { usage; exit 0; }

for tool in git curl unzip rsync node; do
  command -v "$tool" >/dev/null 2>&1 || die "필요한 도구가 없다: $tool"
done

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

METHOD=""
RESOLVED_SHA=""
SRC=""

# ── 1. 소스 확보 ─────────────────────────────────────────────────────────────
if [[ "$REF" =~ ^v[0-9]+\.[0-9]+\.[0-9]+ ]]; then
  echo "· 태그 ${REF}: 릴리즈 자산 archify.zip 시도"
  if curl -fsSL -o "$TMP/archify.zip" "${UPSTREAM_URL}/releases/download/${REF}/archify.zip"; then
    mkdir -p "$TMP/zip"
    unzip -q "$TMP/archify.zip" -d "$TMP/zip"
    [[ -f "$TMP/zip/archify/SKILL.md" ]] || die "zip 안에 archify/SKILL.md 가 없다"
    SRC="$TMP/zip/archify"
    METHOD="release-zip"
    # 주석 태그(annotated)는 ^{} 로 peel 해야 커밋 SHA 가 나온다
    RESOLVED_SHA="$(git ls-remote "$UPSTREAM_GIT" "refs/tags/${REF}^{}" | cut -f1)"
    [[ -n "$RESOLVED_SHA" ]] || RESOLVED_SHA="$(git ls-remote "$UPSTREAM_GIT" "refs/tags/${REF}" | cut -f1)"
    [[ -n "$RESOLVED_SHA" ]] || die "태그 ${REF} 의 SHA 를 조회할 수 없다"
  else
    echo "· 릴리즈 자산이 없다. 클론 경로로 전환"
  fi
fi

if [[ -z "$SRC" ]]; then
  echo "· ${REF}: 클론 후 stage-clean-skill.mjs 로 배포 파일 선별"
  git init -q "$TMP/src"
  git -C "$TMP/src" remote add origin "$UPSTREAM_GIT"
  if [[ "$REF" =~ ^[0-9a-f]{40}$ ]]; then
    git -C "$TMP/src" fetch -q --depth 1 origin "$REF"
  elif git -C "$TMP/src" fetch -q --depth 1 origin "refs/tags/${REF}" 2>/dev/null \
    || git -C "$TMP/src" fetch -q --depth 1 origin "$REF" 2>/dev/null; then
    :
  else
    # 짧은 SHA 는 원격에서 직접 받을 수 없다 — 전체 히스토리를 받아 해석한다
    echo "· 짧은 참조라 전체 히스토리를 받는다"
    git -C "$TMP/src" fetch -q origin
  fi
  git -C "$TMP/src" checkout -q "$REF" 2>/dev/null || git -C "$TMP/src" checkout -q FETCH_HEAD
  RESOLVED_SHA="$(git -C "$TMP/src" rev-parse HEAD)"
  [[ -f "$TMP/src/scripts/stage-clean-skill.mjs" ]] || die "업스트림에 scripts/stage-clean-skill.mjs 가 없다"
  node "$TMP/src/scripts/stage-clean-skill.mjs" --root "$TMP/src" --dest "$TMP/staged/archify" >/dev/null
  SRC="$TMP/staged/archify"
  METHOD="clone+stage"
fi

# ── 2. 우리 제외 목록 적용 ───────────────────────────────────────────────────
REMOVED=()
for rel in "${EXCLUDE_FILES[@]}"; do
  if [[ -e "$SRC/$rel" ]]; then
    rm -f "$SRC/$rel"
    REMOVED+=("$rel")
  fi
done
# 남은 예제 HTML 이 있으면 파일명이 바뀐 것이다 — 목록을 갱신하라고 알린다
if compgen -G "$SRC/examples/*.html" >/dev/null; then
  die "예제 HTML 이 남아 있다. EXCLUDE_FILES 를 갱신하라: $(ls "$SRC"/examples/*.html | xargs -n1 basename | tr '\n' ' ')"
fi

VERSION="$(node -p "require(process.argv[1]).version" "$SRC/package.json")"
FILE_COUNT="$(find "$SRC" -type f | wc -l | tr -d ' ')"
SIZE_KB="$(du -sk "$SRC" | cut -f1)"

# ── 3. 벤더 디렉터리 갱신 ────────────────────────────────────────────────────
mkdir -p "$DEST"
rsync -a --delete --exclude 'UPSTREAM.md' "$SRC/" "$DEST/"

SYNCED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
{
  echo "# archify 엔진 벤더링 정보"
  echo
  echo "이 디렉터리는 \`scripts/sync-archify.sh\` 가 생성한다. **손으로 고치지 않는다.** 고칠 것이 있으면"
  echo "업스트림에 기여하거나, 스크립트의 제외 목록·후처리에 넣는다."
  echo
  echo "| 항목 | 값 |"
  echo "|------|-----|"
  echo "| 업스트림 | ${UPSTREAM_URL} |"
  echo "| 요청 참조 | \`${REF}\` |"
  echo "| 커밋 SHA | \`${RESOLVED_SHA}\` |"
  echo "| 업스트림 버전 | \`${VERSION}\` (package.json) |"
  echo "| 가져온 방법 | ${METHOD} |"
  echo "| 동기화 시각 | ${SYNCED_AT} |"
  echo "| 파일 수 / 크기 | ${FILE_COUNT} / ${SIZE_KB} KB |"
  echo "| 라이선스 | MIT (\`LICENSE\`), 서드파티 고지 \`THIRD_PARTY_NOTICES.md\`, 폰트 \`assets/JetBrainsMono-OFL.txt\` |"
  echo
  echo "## 업스트림 배포본에서 제외한 파일"
  echo
  echo "| 파일 | 이유 |"
  echo "|------|------|"
  for rel in "${EXCLUDE_FILES[@]}"; do
    case "$rel" in
      examples/*.html) echo "| \`${rel}\` | 렌더된 예제 HTML 약 800KB. JSON 예제만 있어도 doctor·validate·deliver 가 동작한다 |" ;;
      scripts/check-update.mjs|scripts/update-contract.mjs|skill-release.json)
        echo "| \`${rel}\` | 업데이트 알림 체커. 유일한 네트워크 호출 경로라 제거해 오프라인을 보장한다 |" ;;
    esac
  done
  echo
  echo "## 로컬 패치"
  echo
  echo "없음. 벤더 파일은 업스트림 배포본과 바이트 단위로 같다."
  echo
  echo "## 재동기화"
  echo
  echo '```bash'
  echo "scripts/sync-archify.sh v2.17.0          # 안정 태그 (릴리즈 zip 사용)"
  echo "scripts/sync-archify.sh <40자 SHA>       # 특정 커밋 (클론 + stage-clean-skill)"
  echo "python3 scripts/lint-skills.py && python3 scripts/preflight.py --deep"
  echo "node plugins/arch-tools/archify/bin/archify.mjs doctor"
  echo '```'
  echo
  echo "매주 월요일 09:00 KST 에 \`.github/workflows/sync-archify.yml\` 이 최신 안정 태그를 확인하고,"
  echo "새 버전이면 같은 절차로 동기화 PR 을 연다."
  echo
  echo "## 주의"
  echo
  echo "- \`archify examples\` 명령은 이 디렉터리의 \`examples/\` 에 HTML 4MB 를 다시 쓴다. 스킬에서 호출하지 않는다."
  echo "- 뷰어 UI 로케일은 \`en\`·\`zh-CN\` 만 있다. 한글 다이어그램은 \`meta.locale\` 을 생략해 영어 UI 로 폴백한다."
} > "$DEST/UPSTREAM.md"

echo
echo "동기화 완료: ${DEST}"
echo "  참조 ${REF} → ${RESOLVED_SHA} (${VERSION}, ${METHOD})"
echo "  파일 ${FILE_COUNT}개, ${SIZE_KB} KB, 제외 ${#REMOVED[@]}개"
echo
echo "다음 단계:"
echo "  python3 scripts/lint-skills.py && python3 scripts/preflight.py --deep"
echo "  node plugins/arch-tools/archify/bin/archify.mjs doctor"
