#!/usr/bin/env bash
# Jira 이슈 생성·수정·사용자 검색.
#
# 값은 전부 인자나 파일로 받는다. 셸 변수를 JSON 이나 다른 언어 소스에 문자열로
# 보간하지 않는다 — 요약·설명에 흔히 들어오는 ' " $ \ ''' 가 페이로드를 깨뜨리거나
# 임의 코드로 해석되기 때문이다. 이스케이프는 전부 jq 에 위임한다.
#
# 사용법:
#   jira-issue.sh create --summary <텍스트> --type <이슈유형>
#                        [--description-file <경로>] [--project <키>]
#                        [--parent <이슈키>] [--component <이름>]
#                        [--field <필드ID>=<값>]...
#   jira-issue.sh edit   --key <이슈키> [--assignee <accountId>] [--reporter <accountId>]
#   jira-issue.sh label  --key <이슈키> --add <라벨>
#   jira-issue.sh user   --query <이름 또는 이메일>
#   jira-issue.sh env
#
# 설정은 본체 레포 루트의 .claude/plugins.json 의 jira-tools 섹션에서 읽는다
# (baseUrl · email · apiTokenFile · projectKey).
# 성공 시 이슈 키(create) 또는 accountId(user)를 stdout 에 한 줄로 낸다.

set -euo pipefail

die() { printf '오류: %s\n' "$*" >&2; exit 1; }

command -v jq   >/dev/null 2>&1 || die "jq 가 필요하다. brew install jq"
command -v curl >/dev/null 2>&1 || die "curl 이 필요하다"

# 설정 파일은 항상 본체 레포 루트 기준으로 찾는다. plugins.json 은 gitignore 대상이라
# worktree 에는 체크아웃되지 않으므로, worktree 안에서 실행돼도 본체를 가리켜야 한다.
# --git-common-dir 는 worktree 에서도 본체의 .git 을 준다 (--git-dir 은 worktree 전용을 준다).
# --path-format=absolute 는 git 2.31+ 이라 쓰지 않고 직접 절대화한다.
main_repo_root() {
  local gcd
  gcd=$(git rev-parse --git-common-dir 2>/dev/null) || return 1
  [ -n "$gcd" ] || return 1
  case "$gcd" in /*) ;; *) gcd="$PWD/$gcd" ;; esac
  ( cd "$gcd/.." 2>/dev/null && pwd -P )
}

if [ -n "${JIRA_PLUGINS_JSON:-}" ]; then
  CONF=$JIRA_PLUGINS_JSON
else
  CONF=$(main_repo_root)/.claude/plugins.json \
    || die "git 저장소 안에서 실행해야 한다 (또는 JIRA_PLUGINS_JSON 으로 경로를 직접 지정한다)"
fi
[ -f "$CONF" ] || die "$CONF 이 없다. /jira-tools:setup 을 먼저 실행한다"

conf() { jq -re --arg k "$1" '."jira-tools"[$k] // empty' "$CONF" 2>/dev/null || true; }

baseUrl=$(conf baseUrl);   [ -n "$baseUrl" ]   || die "plugins.json 에 jira-tools.baseUrl 이 없다"
email=$(conf email);       [ -n "$email" ]     || die "plugins.json 에 jira-tools.email 이 없다"
tokenFile=$(conf apiTokenFile)
[ -n "$tokenFile" ] || die "plugins.json 에 jira-tools.apiTokenFile 이 없다"
tokenFile=${tokenFile/#\~/$HOME}
[ -f "$tokenFile" ] || die "토큰 파일이 없다: $tokenFile"
token=$(tr -d '\n\r' < "$tokenFile")
[ -n "$token" ] || die "토큰 파일이 비어 있다: $tokenFile"

baseUrl=${baseUrl%/}
AUTH=(-u "$email:$token" -H "Content-Type: application/json")

# HTTP 상태를 본문과 분리해 받는다. 2xx 가 아니면 Jira 의 errorMessages 를 그대로 보여준다.
api() { # api <METHOD> <PATH> [<PAYLOAD>]
  local method=$1 path=$2 payload=${3-} out code
  if [ -n "$payload" ]; then
    out=$(curl -sS -w '\n%{http_code}' "${AUTH[@]}" -X "$method" "$baseUrl$path" -d "$payload")
  else
    out=$(curl -sS -w '\n%{http_code}' "${AUTH[@]}" -X "$method" "$baseUrl$path")
  fi
  code=${out##*$'\n'}; body=${out%$'\n'*}
  case "$code" in
    2*) printf '%s' "$body" ;;
    *)  die "$method $path → HTTP $code
$(printf '%s' "$body" | jq -r '(.errorMessages // [])[], (.errors // {} | to_entries[] | "\(.key): \(.value)")' 2>/dev/null || printf '%s' "$body")" ;;
  esac
}

# 마크다운 평문을 ADF 로 감싼다. 빈 문단은 버리고, 전부 비면 공백 문단 하나를 둔다
# (Jira v3 는 description 이 비어 있으면 400 을 낸다).
adf_from_file() { # adf_from_file <경로|-->
  local src=${1:-}
  if [ -z "$src" ] || [ "$src" = "--" ]; then printf '%s' ""; return; fi
  [ -f "$src" ] || die "설명 파일이 없다: $src"
  jq -Rs '
    split("\n\n")
    | map(select(test("\\S")) | {type:"paragraph", content:[{type:"text", text:(.|ltrimstr("\n")|rtrimstr("\n"))}]})
    | {type:"doc", version:1, content: (if length == 0 then [{type:"paragraph",content:[{type:"text",text:" "}]}] else . end)}
  ' < "$src"
}

cmd=${1-}; [ -n "$cmd" ] || die "하위 명령이 필요하다 (create|edit|label|user|env)"
shift

case "$cmd" in
env)
  # 스킬이 curl 을 직접 부를 때 쓰는 설정 로더. 경로 해석·검증을 이 스크립트 한 곳에 모으고
  # 스킬 쪽에는 상대경로 jq 를 남기지 않기 위한 것이다.
  # 토큰 값은 내지 않는다 — stdout 은 트랜스크립트에 그대로 남는다. 경로만 넘기고 읽기는
  # 호출자가 한다. 위쪽에서 토큰 파일 존재·비어있음 검증은 이미 끝났다.
  printf 'baseUrl=%q\n'     "$baseUrl"
  printf 'email=%q\n'       "$email"
  printf 'tokenFile=%q\n'   "$tokenFile"
  printf 'projectKey=%q\n'  "$(conf projectKey)"
  printf 'pluginsJson=%q\n' "$CONF"
  ;;

create)
  summary=""; issuetype=""; descfile=""; project=$(conf projectKey); parent=""; component=""
  fields_json='{}'; dryrun=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --dry-run)          dryrun=1; shift ;;
      --summary)          summary=${2-}; shift 2 ;;
      --type)             issuetype=${2-}; shift 2 ;;
      --description-file) descfile=${2-}; shift 2 ;;
      --project)          project=${2-}; shift 2 ;;
      --parent)           parent=${2-}; shift 2 ;;
      --component)        component=${2-}; shift 2 ;;
      --field)
        [ "${2-}" != "${2#*=}" ] || die "--field 는 <필드ID>=<값> 형식이다: ${2-}"
        fields_json=$(printf '%s' "$fields_json" \
          | jq --arg k "${2%%=*}" --arg v "${2#*=}" '. + {($k): $v}')
        shift 2 ;;
      *) die "알 수 없는 옵션: $1" ;;
    esac
  done
  [ -n "$summary" ]   || die "--summary 가 필요하다"
  [ -n "$issuetype" ] || die "--type 이 필요하다"
  [ -n "$project" ]   || die "--project 가 없고 plugins.json 에 projectKey 도 없다"

  desc=$(adf_from_file "$descfile")
  payload=$(jq -n \
    --arg p "$project" --arg t "$issuetype" --arg s "$summary" \
    --arg parent "$parent" --arg comp "$component" \
    --argjson desc "${desc:-null}" --argjson extra "$fields_json" '
    {fields: (
      {project:{key:$p}, issuetype:{name:$t}, summary:$s}
      + (if $desc == null then {} else {description:$desc} end)
      + (if $parent == "" then {} else {parent:{key:$parent}} end)
      + (if $comp   == "" then {} else {components:[{name:$comp}]} end)
      + $extra
    )}')
  if [ "$dryrun" = 1 ]; then printf '%s\n' "$payload" | jq .; exit 0; fi
  api POST /rest/api/3/issue "$payload" | jq -re '.key'
  ;;

edit)
  key=""; assignee=""; reporter=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --key)      key=${2-}; shift 2 ;;
      --assignee) assignee=${2-}; shift 2 ;;
      --reporter) reporter=${2-}; shift 2 ;;
      *) die "알 수 없는 옵션: $1" ;;
    esac
  done
  [ -n "$key" ] || die "--key 가 필요하다"

  # reporter 변경은 권한 부족으로 자주 실패한다. assignee 까지 같이 날려버리지 않도록
  # 한 번에 보내지 않고, reporter 실패는 경고로만 처리한다.
  if [ -n "$assignee" ]; then
    api PUT "/rest/api/3/issue/$key" \
      "$(jq -n --arg a "$assignee" '{fields:{assignee:{accountId:$a}}}')" >/dev/null
    printf '담당자 설정 완료: %s\n' "$key" >&2
  fi
  if [ -n "$reporter" ]; then
    if api PUT "/rest/api/3/issue/$key" \
         "$(jq -n --arg r "$reporter" '{fields:{reporter:{accountId:$r}}}')" >/dev/null 2>&1; then
      printf '보고자 설정 완료: %s\n' "$key" >&2
    else
      printf '경고: 보고자 변경 실패(권한 부족일 수 있음). 설명에 이름을 기록한다.\n' >&2
    fi
  fi
  ;;

label)
  key=""; add=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --key) key=${2-}; shift 2 ;;
      --add) add=${2-}; shift 2 ;;
      *) die "알 수 없는 옵션: $1" ;;
    esac
  done
  [ -n "$key" ] && [ -n "$add" ] || die "--key 와 --add 가 필요하다"
  api PUT "/rest/api/3/issue/$key" \
    "$(jq -n --arg l "$add" '{update:{labels:[{add:$l}]}}')" >/dev/null
  printf '라벨 추가 완료: %s += %s\n' "$key" "$add" >&2
  ;;

user)
  query=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --query) query=${2-}; shift 2 ;;
      *) die "알 수 없는 옵션: $1" ;;
    esac
  done
  [ -n "$query" ] || die "--query 가 필요하다"
  # --data-urlencode 로 인코딩을 curl 에 맡긴다 (python 으로 따로 인코딩하지 않는다)
  out=$(curl -sS -G "${AUTH[@]}" --data-urlencode "query=$query" \
          "$baseUrl/rest/api/3/user/search")
  printf '%s' "$out" | jq -re '.[0].accountId // empty' \
    || die "일치하는 사용자를 찾지 못했다: $query"
  ;;

*) die "알 수 없는 하위 명령: $cmd (create|edit|label|user|env)" ;;
esac
