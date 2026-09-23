#!/usr/bin/env bash
# 벤더링된 archify 엔진이 무설치로 동작하는지 확인한다 — doctor + 예제 5종 showcase validate.
# CI(.github/workflows/ci.yml) 와 주간 동기화(.github/workflows/sync-archify.yml) 가 함께 쓴다.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
ENGINE="${REPO_ROOT}/plugins/arch-tools/archify"
CLI="${ENGINE}/bin/archify.mjs"

[[ -f "$CLI" ]] || { echo "verify-archify-engine: 엔진이 없다: $CLI" >&2; exit 1; }

echo "· doctor"
node "$CLI" doctor

# 타입:예제 — 업스트림 examples/ 의 JSON 5종
EXAMPLES=(
  "architecture:web-app.architecture.json"
  "workflow:agent-tool-call.workflow.json"
  "sequence:cache-miss-request.sequence.json"
  "dataflow:product-analytics.dataflow.json"
  "lifecycle:agent-run.lifecycle.json"
)

for pair in "${EXAMPLES[@]}"; do
  type="${pair%%:*}"
  file="${pair##*:}"
  [[ -f "$ENGINE/examples/$file" ]] || { echo "예제가 없다: examples/$file" >&2; exit 1; }
  if node "$CLI" validate "$type" "$ENGINE/examples/$file" --quality showcase --json >/dev/null; then
    echo "· validate ${type}: ok"
  else
    echo "· validate ${type}: FAIL" >&2
    node "$CLI" validate "$type" "$ENGINE/examples/$file" --quality showcase --json || true
    exit 1
  fi
done

echo "archify 엔진 검증 통과"
