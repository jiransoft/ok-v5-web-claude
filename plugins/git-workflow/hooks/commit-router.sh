#!/bin/sh
# UserPromptSubmit — 커밋 "실행" 요청을 git-workflow:commit 스킬로 라우팅한다.
#
# 3단계로 좁힌다: ① 커밋 어휘 → ② 질문·조회·이력조작·메타 제외 → ③ 실행 의도.
# 키워드만 보면 "커밋 컨벤션 알려줘" 같은 질문에도 걸려 답변 대신 커밋을 시도한다.
# 남는 오발은 주입 문구를 강제형이 아니라 라우팅형으로 둬서 모델 판단에 흡수시킨다.
#
# 자체 테스트: hooks/test-commit-router.sh
set -u

payload=$(cat)
if command -v jq >/dev/null 2>&1; then
  prompt=$(printf '%s' "$payload" | jq -r '.prompt // empty' 2>/dev/null)
elif command -v python3 >/dev/null 2>&1; then
  prompt=$(printf '%s' "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("prompt",""))' 2>/dev/null)
else
  # 프롬프트를 안전하게 꺼낼 수 없으면 아무것도 하지 않는다.
  # 페이로드 원문을 그대로 훑는 건 금물이다 — cwd·transcript_path 가 매칭에 섞인다.
  exit 0
fi
[ -n "${prompt:-}" ] || exit 0

match() { printf '%s' "$prompt" | grep -qiE "$1"; }

# ① 커밋 어휘가 없으면 관심 없음
match '커밋|commit|amend' || exit 0

# ② 질문·조회·이력 조작·메타(스킬·훅·규칙) 요청은 커밋 실행이 아니다
match '[?？]|뭐|무엇|어떻게|왜|알려|보여|설명|차이|비교|스킬|skill|훅|hook|규칙|컨벤션|convention|되돌|revert|reset|rebase|cherry|squash|취소|로그|log|history|이력|hash|해시|하지 ?(마|말)|말고' && exit 0

# ③ 실행 의도 — 명령·요청형이거나, 문장이 커밋으로 끝나거나, 짧은 단독 발화
# 길이 규칙은 로케일에 따라 `wc -m` 이 바이트를 세면(LANG 미설정) 한글에서 3배로 잡혀 느슨해진다.
# 그래서 길이에만 의존하지 않고 어미·종결 패턴을 먼저 본다 — 빠지는 방향이라 오발은 늘지 않는다.
LEN=$(printf '%s' "$prompt" | wc -m | tr -d ' ')
if match '커밋(해|하|할|하고|하자|부탁|만들|나눠|분리|진행)|커밋 (해|부탁|진행|메시지|메세지|나눠|분리)|커밋[[:space:]]*$|스테이징|amend|commit (it|this|these|them|now|please)|commit해' \
  || [ "$LEN" -le 30 ]; then
  cat <<'ROUTE'
[git-workflow] 커밋 실행 요청으로 보인다 — 직접 `git commit` 하지 말고 Skill 도구로 `git-workflow:commit` 을 먼저 호출한다. 커밋에 관한 질문·조회·이력 조작 요청이면 이 문장을 무시한다.
ROUTE
fi

exit 0
