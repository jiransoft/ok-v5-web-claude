#!/bin/sh
# commit-router.sh 회귀 테스트 — 발동해야 할 발화와 발동하면 안 되는 발화를 함께 고정한다.
# 실행: sh plugins/git-workflow/hooks/test-commit-router.sh
set -u

ROUTER=$(dirname "$0")/commit-router.sh
PASS=0
FAIL=0

check() { # check <fire|skip> <prompt>
  want=$1
  prompt=$2
  out=$(printf '%s' "$prompt" | python3 -c 'import json,sys; print(json.dumps({"hook_event_name":"UserPromptSubmit","prompt":sys.stdin.read()}))' | sh "$ROUTER")
  if [ -n "$out" ]; then got=fire; else got=skip; fi
  if [ "$got" = "$want" ]; then
    PASS=$((PASS + 1))
  else
    FAIL=$((FAIL + 1))
    printf 'FAIL  want=%-4s got=%-4s  %s\n' "$want" "$got" "$prompt"
  fi
}

# 발동해야 한다 — 커밋 실행 요청
check fire '커밋해줘'
check fire '커밋'
check fire 'commit'
check fire '이거 커밋해줘'
check fire '방금 작업 커밋하고 푸시까지 해줘'
check fire '스테이징하고 커밋해줘'
check fire '커밋 메시지 만들어줘'
check fire '커밋 나눠서 두 개로 분리해줘'
check fire 'amend 해줘'
check fire 'commit this'
check fire 'OKEP-4815 커밋해줘'
check fire '지금까지 바뀐 것들 전부 커밋'

# 발동하면 안 된다 — 질문·조회·이력조작·메타·무관
check skip '커밋 스킬 트리거 확률 높이려면 어떻게해야하지?'
check skip 'commit 스킬 개선해봐'
check skip '커밋 컨벤션 알려줘'
check skip '마지막 커밋 되돌려줘'
check skip '커밋 로그 보여줘'
check skip '커밋 hash 뭐야'
check skip '아직 커밋하지 마'
check skip '커밋 취소해줘'
check skip 'PR 만들어줘'
check skip '3번에 A로 하자'
check skip '테스트 실행해줘'

printf '\n통과 %d건 / 실패 %d건\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
