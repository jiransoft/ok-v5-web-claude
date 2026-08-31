#!/usr/bin/env python3
"""SKILL.md / 에이전트 문서 구조 린터.

CONTRIBUTION.md 의 저장소 컨벤션과 Anthropic 공식 Agent Skills 규격을 함께 검사한다.
python3 표준 라이브러리만 사용한다 (PyYAML 비의존 — 프론트매터는 정규식으로 읽는다).

사용법:
    python3 scripts/lint-skills.py            # 전체 검사, 위반 있으면 exit 1
    python3 scripts/lint-skills.py --warn-ok  # 경고는 exit code 에 반영하지 않음
    python3 scripts/lint-skills.py <path>...  # 특정 파일만 검사
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# ── 공식 규격 상수 ────────────────────────────────────────────────────────────
NAME_MAX = 64
DESC_MAX = 1024          # description 단독 상한
LISTING_MAX = 1536       # description + when_to_use 합계 (스킬 목록 절단선)
BODY_MAX_LINES = 500     # 공식 Tip
REF_TOC_MIN_LINES = 100  # 이 줄수를 넘는 reference 는 목차 필요

# Claude Code 내장 도구. 여기 없는 이름을 allowed-tools 에 쓰면 그 도구는 차단된다.
KNOWN_TOOLS = {
    "Agent", "Artifact", "AskUserQuestion", "Bash", "BashOutput", "CronCreate",
    "CronDelete", "CronList", "DesignSync", "Edit", "EndConversation",
    "EnterPlanMode", "EnterWorktree", "ExitPlanMode", "ExitWorktree", "Glob",
    "Grep", "KillShell", "ListMcpResourcesTool", "Monitor", "NotebookEdit",
    "PushNotification", "Read", "ReadMcpResourceTool", "RemoteTrigger",
    "ReportFindings", "ScheduleWakeup", "SendMessage", "Skill", "SlashCommand",
    "TaskCreate", "TaskGet", "TaskList", "TaskOutput", "TaskStop", "TaskUpdate",
    "TeamCreate", "TeamDelete", "TodoWrite", "ToolSearch", "WebFetch",
    "WebSearch", "Workflow", "Write",
}
# 과거 이름 → 현재 이름. Task 는 Agent 로 개명됐다.
RENAMED_TOOLS = {"Task": "Agent"}

# 프론트매터
REQUIRED_FM = {"name", "description"}
FORBIDDEN_FM = {
    "metadata": "버전·설정을 SKILL.md 에 이중 기재하면 /bump-version 대상 밖이라 드리프트한다",
    "license": "플러그인 단위 라이선스는 plugin.json 에 둔다",
}
# description 이 있어도 자동 호출을 원하면 둘 중 하나는 있어야 한다
INVOCATION_FM = {"when_to_use", "disable-model-invocation"}

# 본문에서 접두사 없이 쓰면 "tool not found" 를 유발하는 MCP 도구 이름들
BARE_MCP_NAMES = re.compile(
    r"(?<![\w:_])("
    r"browser_(?:navigate|snapshot|click|type|evaluate|take_screenshot|file_upload|"
    r"press_key|wait_for|network_requests|close|resize|hover|select_option)"
    r"|get_design_context|get_screenshot|get_metadata|get_variable_defs|get_figjam"
    r"|createJiraIssue|editJiraIssue|getJiraIssue|searchJiraIssuesUsingJql"
    r")(?![\w_])"
)


class Finding:
    def __init__(self, path, line, code, level, msg):
        self.path, self.line, self.code, self.level, self.msg = path, line, code, level, msg

    def __str__(self):
        try:
            loc = self.path.relative_to(REPO)
        except ValueError:  # 저장소 밖 경로를 직접 지정한 경우
            loc = self.path
        tag = "ERROR" if self.level == "error" else "warn "
        return f"{tag} {loc}:{self.line}  [{self.code}] {self.msg}"


def split_frontmatter(text):
    """(frontmatter_raw, body, body_start_line) 반환. 프론트매터가 없으면 (None, text, 1)."""
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return None, text, 1
    return m.group(1), m.group(2), m.group(1).count("\n") + 3


def parse_frontmatter(raw):
    """최상위 키만 뽑는다. 중첩 블록은 값을 None 으로 두고 키 존재만 기록한다."""
    out = {}
    if not raw:
        return out
    for line in raw.split("\n"):
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip("\"'")
    return out


def parse_skips(raw):
    """프론트매터의 `# lint-skip: CODE[,CODE] — 사유` 주석에서 면제 코드를 읽는다.

    사유가 없으면 면제하지 않는다 — 이유 없는 억제를 막기 위해서다.
    """
    skips = set()
    for line in (raw or "").split("\n"):
        m = re.match(r"^#\s*lint-skip:\s*([A-Z][A-Z,\s]*?)\s*(?:—|--)\s*(\S.*)$", line)
        if m:
            skips |= {c.strip() for c in m.group(1).split(",") if c.strip()}
    return skips


def fence_map(lines):
    """각 줄이 코드펜스 안인지 나타내는 불리언 리스트 + 펜스 문제 목록을 반환.

    CommonMark: 닫는 펜스는 여는 펜스와 같은 문자로 길이가 같거나 길어야 하고,
    info string 이 없어야 한다. 그래서 ``` 안의 ```bash 는 닫지 못한다.
    """
    inside = [False] * len(lines)
    problems = []
    open_char, open_len, open_line = None, 0, 0
    for i, line in enumerate(lines):
        m = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if m:
            marker, info = m.group(1), m.group(2).strip()
            char, length = marker[0], len(marker)
            if open_char is None:
                open_char, open_len, open_line = char, length, i + 1
                inside[i] = True
                continue
            if char == open_char and length >= open_len and not info:
                inside[i] = True
                open_char = None
                continue
            if char == open_char and length >= open_len and info:
                problems.append((
                    i + 1,
                    f"{open_line}행에서 연 ``` 블록 안에 같은 길이의 ```{info.split()[0]} 가 있다. "
                    f"info string 이 붙은 펜스는 블록을 닫지 못하므로 바깥 펜스를 백틱 4개로 바꾼다",
                ))
        if open_char is not None:
            inside[i] = True
    if open_char is not None:
        problems.append((open_line, "이 펜스가 파일 끝까지 닫히지 않는다 — 이후 섹션이 코드블록에 삼켜진다"))
    return inside, problems


def check_doc(path, is_agent=False):
    text = path.read_text(encoding="utf-8")
    fm_raw, body, body_off = split_frontmatter(text)
    fm = parse_frontmatter(fm_raw)
    lines = text.split("\n")
    body_lines = body.split("\n")
    inside, fence_problems = fence_map(lines)
    out = []
    skips = parse_skips(fm_raw)

    def add(line, code, level, msg):
        if code in skips:
            return
        out.append(Finding(path, line, code, level, msg))

    # ① 코드펜스 균형
    for line, msg in fence_problems:
        add(line, "FENCE", "error", msg)

    if fm_raw is None:
        add(1, "FM", "error", "YAML 프론트매터가 없다")
        return out

    # ④ 프론트매터 필수/금지 필드
    for key in sorted(REQUIRED_FM - set(fm)):
        add(1, "FM", "error", f"필수 필드 `{key}` 누락")
    if not is_agent and not (INVOCATION_FM & set(fm)):
        add(1, "FM", "warn",
            "`when_to_use` 또는 `disable-model-invocation` 중 하나가 필요하다 (자동 호출 판단 기준)")
    for key, why in FORBIDDEN_FM.items():
        if key in fm:
            add(1, "FM", "error", f"금지 필드 `{key}` — {why}")

    # ⑩ name 규격 · description 길이
    name = fm.get("name", "")
    if name:
        if len(name) > NAME_MAX:
            add(1, "NAME", "error", f"name {len(name)}자 — 공식 상한 {NAME_MAX}자")
        if not re.fullmatch(r"[a-z0-9-]+", name):
            add(1, "NAME", "error", f"name `{name}` — 소문자·숫자·하이픈만 허용")
        if re.search(r"anthropic|claude", name, re.I):
            add(1, "NAME", "error", f"name `{name}` — 예약어 anthropic/claude 사용 불가")
        if not is_agent and name != path.parent.name:
            add(1, "NAME", "warn", f"name `{name}` 이 디렉토리명 `{path.parent.name}` 과 다르다")
    desc, wtu = fm.get("description", ""), fm.get("when_to_use", "")
    if len(desc) > DESC_MAX:
        add(1, "DESC", "error", f"description {len(desc)}자 — 공식 상한 {DESC_MAX}자")
    if len(desc) + len(wtu) > LISTING_MAX:
        add(1, "DESC", "error",
            f"description+when_to_use {len(desc) + len(wtu)}자 — {LISTING_MAX}자 초과분은 스킬 목록에서 잘린다")
    if re.match(r"^\s*(이 skill|이 스킬|This skill)", desc):
        add(1, "DESC", "warn",
            "description 이 스킬 자신을 지칭한다. '무엇을 하는지'로 시작하고 '언제 쓰는지'는 when_to_use 에 둔다")

    # ② allowed-tools 실존 도구명 · ⑥ 무제한 Bash
    tools_raw = fm.get("allowed-tools", "") or fm.get("tools", "")
    if tools_raw:
        fm_line = next((i + 1 for i, l in enumerate(lines)
                        if re.match(r"^(allowed-tools|tools):", l)), 1)
        for tok in [t.strip() for t in re.split(r",(?![^(]*\))", tools_raw) if t.strip()]:
            base = tok.split("(")[0].strip()
            if base in RENAMED_TOOLS:
                add(fm_line, "TOOL", "error",
                    f"`{base}` 는 존재하지 않는 도구명 → `{RENAMED_TOOLS[base]}` 로 교체")
            elif base.startswith("mcp__"):
                continue
            elif base not in KNOWN_TOOLS:
                add(fm_line, "TOOL", "error", f"알 수 없는 도구 `{base}`")
            # 에이전트의 `tools:` 는 단순 도구명 목록이라 권한 스코핑 문법을 받지 않는다
            # (CONTRIBUTION.md 의 에이전트 예시도 `tools: Read, Grep, Glob, Bash`).
            # 스코핑 요구는 스킬의 allowed-tools 에만 적용한다.
            if not is_agent and base in ("Bash", "BashOutput") and "(" not in tok:
                add(fm_line, "BASH", "warn",
                    "무제한 `Bash` — `Bash(git *)` 처럼 명령 단위로 스코핑한다 (CONTRIBUTION.md 최소권한)")

    # ③ 본문 MCP 도구명 정규화 · ⑤ worktree --detach · ⑦ 번호 중복 · Windows 경로
    seen_steps = {}
    for i, line in enumerate(body_lines):
        n = i + body_off
        in_fence = inside[n - 1] if n - 1 < len(inside) else False

        if not in_fence:
            m = re.match(r"^(#{2,4})\s+(\d+(?:-\d+)?)\.\s", line)
            if m:
                key = (len(m.group(1)), m.group(2))
                if key in seen_steps:
                    add(n, "NUM", "error",
                        f"단계 번호 `{m.group(2)}.` 이 {seen_steps[key]}행과 중복 — 절차 번호는 유일해야 한다")
                else:
                    seen_steps[key] = n

        for mm in BARE_MCP_NAMES.finditer(line):
            add(n, "MCP", "error",
                f"MCP 도구 `{mm.group(1)}` 에 서버 접두사가 없다 — `mcp__<server>__{mm.group(1)}` 형태로 쓴다")

        if "git worktree add" in line and "--detach" not in line:
            add(n, "WT", "error",
                "`git worktree add` 에 `--detach` 가 없다 — 대상 브랜치가 잠겨 있으면 실패한다")
        if re.search(r"(?<![\w`])[\w.-]+\\[\w.-]+\.(md|py|sh|json)", line):
            add(n, "PATH", "warn", "Windows 스타일 경로 — forward slash 를 쓴다")

    # ⑪ 셸 변수 문자열 보간 (주입)
    check_injection(lines, inside, body_off, add)

    # ⑨ body 500줄
    n_body = len([l for l in body_lines if l.strip()]) and len(body_lines)
    if n_body > BODY_MAX_LINES:
        add(body_off, "LEN", "error",
            f"본문 {n_body}줄 — 공식 상한 {BODY_MAX_LINES}줄. reference/ 로 분리한다")
    elif n_body > BODY_MAX_LINES * 0.8:
        add(body_off, "LEN", "warn",
            f"본문 {n_body}줄 — {BODY_MAX_LINES}줄에 근접. 분리를 검토한다")

    return out


def check_injection(lines, inside, body_off, add):
    """셸 변수를 타 언어 소스나 JSON 리터럴에 문자열 보간하는 패턴을 찾는다.

    요약·설명 같은 자유 텍스트에 ' " $ \\ 가 들어오면 페이로드가 깨지거나
    임의 코드로 해석된다. jq --arg 나 번들 스크립트 인자로 넘겨야 한다.
    """
    SHELL_VAR = re.compile(r"\$\{?[A-Za-z_][A-Za-z0-9_]*")
    # ① python3 -c "..." / python -c "..." 안의 셸 변수 (여는 따옴표부터 닫힐 때까지)
    open_at = None
    for i, line in enumerate(lines):
        n = i + 1
        if not inside[i]:
            open_at = None
            continue
        if open_at is None and re.search(r"\bpython3?\s+-c\s+\"", line):
            open_at = n
            rest = line.split('-c', 1)[1]
            if rest.count('"') >= 2:      # 한 줄로 닫힌 경우
                if SHELL_VAR.search(rest):
                    add(n, "INJECT", "error",
                        "`python -c \"...\"` 안에 셸 변수를 보간한다 — 값에 ' \" $ \\ 가 오면 "
                        "구문이 깨지거나 임의 코드로 해석된다. jq --arg 또는 스크립트 인자로 넘긴다")
                open_at = None
            continue
        if open_at is not None:
            if SHELL_VAR.search(line):
                add(open_at, "INJECT", "error",
                    f"`python -c \"...\"` 블록({open_at}~{n}행) 안에 셸 변수를 보간한다 — "
                    "값에 ' \" $ \\ 가 오면 구문이 깨지거나 임의 코드로 해석된다. "
                    "jq --arg 또는 스크립트 인자로 넘긴다")
                open_at = None
            elif line.strip().startswith('"'):
                open_at = None

    # ② 작은따옴표 JSON 리터럴을 끊고 셸 변수를 끼워 넣는 패턴: "'$var'"
    for i, line in enumerate(lines):
        if inside[i] and re.search(r"\"'\$\{?[A-Za-z_]", line):
            add(i + 1, "INJECT", "error",
                "JSON 리터럴을 끊고 셸 변수를 끼워 넣는다(`\"'$var'\"`) — 값에 ' 가 하나만 "
                "있어도 깨진다. jq --arg 로 페이로드를 만든다")


def check_fences_only(path):
    """프론트매터가 없는 일반 문서(CONTRIBUTION.md, README.md, reference/*)의 펜스만 본다."""
    lines = path.read_text(encoding="utf-8").split("\n")
    _, problems = fence_map(lines)
    return [Finding(path, ln, "FENCE", "error", msg) for ln, msg in problems]


def check_reference(path, skill_md):
    """⑧ 100줄 초과 reference 의 목차 + SKILL.md 에서의 참조 여부."""
    out = []
    lines = path.read_text(encoding="utf-8").split("\n")
    if len(lines) > REF_TOC_MIN_LINES and not re.search(
        r"^#{2,3}\s+(Contents|목차)", "\n".join(lines), re.M | re.I
    ):
        out.append(Finding(path, 1, "TOC", "warn",
                           f"{len(lines)}줄 — {REF_TOC_MIN_LINES}줄 초과 reference 는 상단에 `## 목차` 가 필요하다"))
    if skill_md.exists() and path.name not in skill_md.read_text(encoding="utf-8"):
        out.append(Finding(path, 1, "REF", "warn",
                           f"SKILL.md 에서 `{path.name}` 를 참조하지 않는다 — 참조 없는 파일은 로드되지 않는다"))
    return out


def main(argv):
    warn_ok = "--warn-ok" in argv
    targets = [a for a in argv[1:] if not a.startswith("--")]

    findings = []
    if targets:
        for t in targets:
            p = Path(t).resolve()
            if p.name == "SKILL.md" or "/agents/" in str(p):
                findings += check_doc(p, is_agent="/agents/" in str(p))
            else:
                # 프론트매터가 없는 일반 문서는 펜스만 본다
                findings += check_fences_only(p)
    else:
        for p in sorted(REPO.glob("plugins/*/skills/*/SKILL.md")):
            findings += check_doc(p)
        for p in sorted(REPO.glob("plugins/*/agents/*.md")):
            findings += check_doc(p, is_agent=True)
        for p in sorted(REPO.glob("plugins/*/skills/*/reference/*.md")):
            findings += check_reference(p, p.parent.parent / "SKILL.md")
        for p in sorted(REPO.glob("plugins/*/reference/*.md")):
            findings += check_fences_only(p)
        for name in ("CONTRIBUTION.md", "README.md"):
            p = REPO / name
            if p.exists():
                findings += check_fences_only(p)

    errors = [f for f in findings if f.level == "error"]
    warns = [f for f in findings if f.level == "warn"]

    for f in sorted(findings, key=lambda f: (f.level != "error", str(f.path), f.line)):
        print(f)

    by_code = {}
    for f in findings:
        by_code[f.code] = by_code.get(f.code, 0) + 1
    print()
    print(f"검사 대상 {len(set(f.path for f in findings)) or 0}개 파일에서 "
          f"에러 {len(errors)}건 / 경고 {len(warns)}건")
    if by_code:
        print("  " + " · ".join(f"{k} {v}" for k, v in sorted(by_code.items())))

    return 1 if errors or (warns and not warn_ok) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
