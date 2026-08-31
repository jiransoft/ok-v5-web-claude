#!/usr/bin/env python3
"""레포 정합성 게이트 — 배포 전에 문서·매니페스트·실제 선언이 어긋났는지 대조한다.

이 저장소 전용이며 사용자에게 배포되지 않는다. 사용자 환경 진단은 doctor 플러그인
(`/doctor:check`)이고, 이 스크립트는 그 doctor.json 이 실제 스킬 선언과 맞는지까지 본다.

lint-skills.py 는 SKILL.md '구조'를 본다. 여기서는 파일 사이의 '정합'을 본다 — 겹치지 않는다.

사용법: python3 scripts/preflight.py [--deep]
  --deep   훅 selfTest 와 lint-skills.py 까지 실행

종료코드: 0 정상 · 1 경고만 · 2 오류 있음
"""
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKETPLACE = os.path.join(REPO, ".claude-plugin", "marketplace.json")
README = os.path.join(REPO, "README.md")

# 셸 유틸은 외부 의존성이 아니다 — 매니페스트에 적을 대상에서 제외한다
SHELL_UTILS = {
    "cat", "chmod", "printf", "echo", "ls", "grep", "command", "mkdir", "rm", "cp", "mv",
    "sed", "awk", "find", "sh", "bash", "test", "wc", "tr", "sort", "head", "tail", "du",
    "date", "pwd", "which", "xargs", "diff", "open", "basename", "dirname", "touch", "sleep",
    "cd", "eval",
}

findings = []


def add(level, area, message):
    findings.append((level, area, message))


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f) if path.endswith(".json") else f.read()
    except (OSError, ValueError) as e:
        add("error", os.path.relpath(path, REPO), f"읽기·파싱 실패: {e}")
        return None


def plugin_dirs():
    root = os.path.join(REPO, "plugins")
    return sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))


def skill_files(plugin):
    base = os.path.join(REPO, "plugins", plugin, "skills")
    if not os.path.isdir(base):
        return []
    return [os.path.join(base, s, "SKILL.md") for s in sorted(os.listdir(base))
            if os.path.exists(os.path.join(base, s, "SKILL.md"))]


def check_versions(market, dirs):
    """marketplace metadata · 각 항목 · plugin.json · README 표가 한 버전이어야 한다."""
    declared = market.get("metadata", {}).get("version")
    if not declared:
        add("error", "version", "marketplace.json 에 metadata.version 이 없다")
        return
    for entry in market.get("plugins", []):
        if entry.get("version") != declared:
            add("error", "version",
                f"marketplace plugins[{entry.get('name')}].version={entry.get('version')} ≠ metadata {declared}")
    for p in dirs:
        pj = load(os.path.join(REPO, "plugins", p, ".claude-plugin", "plugin.json")) or {}
        if pj.get("version") != declared:
            add("error", "version", f"{p}/plugin.json version={pj.get('version')} ≠ {declared}")
    readme = load(README) or ""
    rows = re.findall(r"^\|\s*\*\*([\w-]+)\*\*\s*\|.*\|\s*([\d.]+)\s*\|$", readme, re.M)
    for name, ver in rows:
        if ver != declared:
            add("error", "version", f"README 표 {name} 버전 {ver} ≠ {declared}")
    if not rows:
        add("warn", "version", "README 플러그인 표에서 버전 열을 못 읽었다 — 표 형식이 바뀌었나")


def check_registration(market, dirs):
    """디렉토리 · marketplace 항목 · plugin.json name 이 서로 맞아야 한다."""
    entries = {e.get("name"): e for e in market.get("plugins", [])}
    for p in dirs:
        if p not in entries:
            add("error", "registration", f"`plugins/{p}` 가 marketplace.json 에 없다")
            continue
        src = entries[p].get("source", "")
        if src.strip("./") != f"plugins/{p}":
            add("error", "registration", f"{p} 의 source `{src}` 가 실제 경로와 다르다")
        pj = load(os.path.join(REPO, "plugins", p, ".claude-plugin", "plugin.json")) or {}
        if pj.get("name") != p:
            add("error", "registration", f"{p}/plugin.json name=`{pj.get('name')}` ≠ 디렉토리명")
    for name in entries:
        if name not in dirs:
            add("error", "registration", f"marketplace 에 등재됐지만 디렉토리 없음: {name}")


def manifest_of(plugin):
    path = os.path.join(REPO, "plugins", plugin, "doctor.json")
    if not os.path.exists(path):
        add("error", "manifest", f"{plugin} 에 doctor.json 이 없다 — /doctor:check 진단 대상에서 빠진다")
        return None
    m = load(path)
    if m is None:
        return None
    if m.get("schema") != 1:
        add("error", "manifest", f"{plugin}/doctor.json schema={m.get('schema')} — 지원 버전은 1")
    if m.get("plugin") != plugin:
        add("error", "manifest", f"{plugin}/doctor.json plugin=`{m.get('plugin')}` ≠ 디렉토리명")
    return m


def declared_commands(plugin):
    """SKILL.md allowed-tools 의 Bash(<cmd> …) 에서 외부 CLI 만 추린다."""
    cmds = set()
    for f in skill_files(plugin):
        text = load(f) or ""
        head = text.split("---")[1] if text.startswith("---") else text
        for m in re.finditer(r"Bash\(([a-z0-9_.-]+)[\s*)]", head):
            name = m.group(1)
            if name not in SHELL_UTILS:
                cmds.add(name)
    return cmds


def declared_mcp(plugin):
    servers = set()
    for f in skill_files(plugin):
        servers |= set(re.findall(r"mcp__([a-z0-9_-]+)__", load(f) or ""))
    return servers


def check_manifest_truth(plugin, m):
    """매니페스트가 실제 스킬 선언과 맞는지 — 이 대조가 preflight 의 핵심이다."""
    # ① CLI
    real, listed = declared_commands(plugin), {c["name"] for c in m.get("commands", [])}
    for c in sorted(real - listed):
        add("error", "manifest", f"{plugin}: `{c}` 를 스킬이 쓰는데 doctor.json commands 에 없다")
    for c in sorted(listed - real):
        add("warn", "manifest", f"{plugin}: doctor.json 에 `{c}` 가 있는데 스킬 선언에는 없다")

    # ② MCP
    real, listed = declared_mcp(plugin), {s["server"] for s in m.get("mcp", [])}
    for s in sorted(real - listed):
        add("error", "manifest", f"{plugin}: mcp__{s}__ 를 쓰는데 doctor.json mcp 에 없다")
    for s in sorted(listed - real):
        add("error", "manifest", f"{plugin}: doctor.json 이 MCP `{s}` 를 요구하지만 쓰는 스킬이 없다")

    # ③ 설정 키 — setup SKILL.md 의 jsonc 예시가 근거다
    cfg = m.get("config")
    setup = os.path.join(REPO, "plugins", plugin, "skills", "setup", "SKILL.md")
    if cfg and os.path.exists(setup):
        text = load(setup) or ""
        block = re.search(r'"' + re.escape(cfg["key"]) + r'"\s*:\s*\{(.*?)\n  \}', text, re.S)
        if not block:
            add("warn", "manifest", f"{plugin}: setup 에서 `{cfg['key']}` 예시 블록을 못 찾았다")
        else:
            example = set(re.findall(r'^\s{4}"([\w-]+)"\s*:', block.group(1), re.M))
            known = set(cfg.get("required", [])) | set(cfg.get("optional", []))
            for k in sorted(example - known):
                add("error", "manifest", f"{plugin}: setup 예시의 `{k}` 가 doctor.json 에 없다")
            for k in sorted(known - example):
                add("warn", "manifest", f"{plugin}: doctor.json 의 `{k}` 가 setup 예시에 없다")
    elif cfg and not os.path.exists(setup):
        add("warn", "manifest", f"{plugin}: config 를 선언했지만 setup 스킬이 없다")

    # ④ 훅
    hooks_json = os.path.join(REPO, "plugins", plugin, "hooks", "hooks.json")
    listed = {h["script"] for h in m.get("hooks", [])}
    if os.path.exists(hooks_json) and not listed:
        add("error", "manifest", f"{plugin}: hooks/hooks.json 이 있는데 doctor.json hooks 가 비었다")
    for h in m.get("hooks", []):
        for key in ("script", "selfTest"):
            rel = h.get(key)
            if rel and not os.path.exists(os.path.join(REPO, "plugins", plugin, rel)):
                add("error", "manifest", f"{plugin}: 훅 {key} 경로 없음 — {rel}")

    # ⑤ setup 명령 표기
    setup_cmd = m.get("setup")
    if setup_cmd:
        want = f"/{plugin}:setup"
        if setup_cmd != want:
            add("error", "manifest", f"{plugin}: doctor.json setup=`{setup_cmd}` — `{want}` 여야 한다")
        if not os.path.exists(setup):
            add("error", "manifest", f"{plugin}: setup 명령을 선언했지만 setup 스킬이 없다")
    elif os.path.exists(setup):
        add("warn", "manifest", f"{plugin}: setup 스킬이 있는데 doctor.json setup 이 null 이다")


def check_readme(dirs, manifests):
    readme = load(README) or ""
    rows = set(re.findall(r"^\|\s*\*\*([\w-]+)\*\*\s*\|", readme, re.M))
    for p in dirs:
        if p not in rows:
            add("error", "readme", f"README 표에 `{p}` 행이 없다")
    installs = set(re.findall(r"claude plugin install ([\w-]+)@", readme))
    for p in dirs:
        if p not in installs:
            add("warn", "readme", f"README 전체 설치 목록에 `{p}` 가 없다")

    # 필요 설정 표 ↔ 매니페스트.
    # 같은 `| **플러그인** |` 형태의 표가 README 에 셋(플러그인·Setup·필요 설정) 있으므로
    # 섹션을 먼저 잘라내지 않으면 엉뚱한 표를 읽는다.
    section = re.search(r"### 플러그인별 필요 설정\n(.*?)(?=\n###|\n---)", readme, re.S)
    if not section:
        add("warn", "readme", "README 에서 `### 플러그인별 필요 설정` 섹션을 못 찾았다")
        return
    table = section.group(1)
    for p, m in manifests.items():
        cfg = m.get("config")
        if not cfg:
            continue
        row = re.search(r"^\|\s*\*\*" + re.escape(p) + r"\*\*\s*\|(.*)$", table, re.M)
        if not row:
            add("warn", "readme", f"README 필요 설정 표에 `{p}` 행이 없다")
            continue
        listed = set(re.findall(r"`([\w-]+)`", row.group(1)))
        known = set(cfg.get("required", [])) | set(cfg.get("optional", []))
        for k in sorted(listed - known):
            add("warn", "readme", f"README 필요 설정 표의 `{p}.{k}` 가 doctor.json 에 없다")
        for k in sorted(known - listed):
            add("warn", "readme", f"doctor.json 의 `{p}.{k}` 가 README 필요 설정 표에 없다")


def check_slash_references(dirs):
    """문서에 적힌 `/플러그인:스킬` 이 실제로 존재하는지 — 개명·삭제 후 낡은 참조를 잡는다."""
    real = {f"/{p}:{s}" for p in dirs
            for s in (os.listdir(os.path.join(REPO, "plugins", p, "skills"))
                      if os.path.isdir(os.path.join(REPO, "plugins", p, "skills")) else [])}
    targets = [README, os.path.join(REPO, "docs", "marketplace-architecture.md")]
    for p in dirs:
        targets += skill_files(p)
        targets += [os.path.join(REPO, "plugins", p, "doctor.json")]
    for path in targets:
        if not os.path.exists(path):
            continue
        text = load(path) or ""
        if not isinstance(text, str):
            text = json.dumps(text, ensure_ascii=False)
        for ref in set(re.findall(r"/([a-z][\w-]*):([a-z][\w-]*)", text)):
            cmd = f"/{ref[0]}:{ref[1]}"
            if ref[0] in dirs and cmd not in real:
                add("error", "reference",
                    f"{os.path.relpath(path, REPO)}: 존재하지 않는 스킬 참조 {cmd}")


def check_config_path(dirs):
    """설정 파일을 상대경로로 읽거나 쓰면 worktree 안에서 깨진다.

    `.claude/plugins.json` 은 gitignore 대상이라 worktree 에 체크아웃되지 않는다. cwd 가
    worktree 로 옮겨간 뒤 상대경로로 접근하면 파일을 못 찾고 인증 정보가 조용히 빈 값이
    된다 — 실패가 아니라 빈 값이라 발견이 늦다. `.gitignore` 쪽은 반대로, worktree 의
    트래킹된 파일에 써서 작업 브랜치를 오염시킨다.
    본체 레포 기준으로 해석해야 한다 (CONTRIBUTION.md '설정 경로' 규약 참조).
    """
    # 앞에 $VAR·/·따옴표가 붙으면 절대경로 조립이므로 제외한다.
    BARE = r'(?<![\w/$"\'])\.(?:claude/plugins\.json|gitignore)\b'
    rel = [
        # ① 명령의 인자로 넘어가는 상대경로
        re.compile(r'\b(jq|cat|grep|test|python3|node|sed|awk|tr|echo|printf)\b[^\n]*?' + BARE),
        # ② 변수에 상대경로를 대입 — CONF=${X:-.claude/plugins.json} 같은 형태.
        #    명령어가 없어 ①에 안 걸리지만 나중에 그대로 읽히므로 결과는 같다.
        re.compile(r'^\s*\w+=[^\n]*?' + BARE),
        # ③ 리다이렉션 대상
        re.compile(r'>>?\s*' + BARE),
    ]
    targets = []
    for p in dirs:
        base = os.path.join(REPO, "plugins", p)
        targets += skill_files(p)
        sdir = os.path.join(base, "scripts")
        if os.path.isdir(sdir):
            targets += [os.path.join(sdir, f) for f in sorted(os.listdir(sdir))
                        if f.endswith((".sh", ".py"))]
    for path in targets:
        text = load(path) or ""
        if not isinstance(text, str):
            continue
        is_md = path.endswith(".md")
        in_bash = not is_md          # 스크립트는 전부 실행 컨텍스트다
        for i, line in enumerate(text.splitlines(), 1):
            if is_md:
                st = line.strip()
                if st.startswith("```"):
                    in_bash = st.startswith("```bash")
                    continue
                if not in_bash:
                    continue          # 산문 속 백틱 표기는 대상이 아니다
            if line.lstrip().startswith("#"):
                continue              # 주석
            if any(r.search(line) for r in rel):
                add("error", "config-path",
                    f"{os.path.relpath(path, REPO)}:{i}: 설정·gitignore 를 상대경로로 접근한다"
                    " — worktree 에서 깨진다. 본체 레포 루트 기준으로 해석한다")


def check_worktree_source_path(dirs):
    """worktree 스킬의 bash 가 소스를 상대경로로 읽으면 엉뚱한 브랜치를 본다.

    `--source` 로 worktree 를 만들어놓고 `grep ... src/main` 처럼 상대경로로 읽으면 cwd
    (=본체 레포)를 읽는다. 지정한 브랜치가 아닌 현재 브랜치의 코드로 판단하게 되는데,
    에러가 아니라 '그럴듯하게 틀린 결과'라 발견이 가장 늦다.
    앞의 config-path 룰과 방향이 반대다 — 저건 worktree 를 보면 안 되는 것, 이건 봐야 하는 것.
    """
    src = re.compile(r'\b(grep|rg|find|cat|ls|head|tail|wc|xargs)\b.*?'
                     r'(?<![\w/$"\'-])(src/|apps?/|lib/|build\.gradle|pom\.xml|package\.json)')
    for p in dirs:
        for path in skill_files(p):
            text = load(path) or ""
            if "worktree add" not in text:
                continue
            in_bash, buf, start = False, "", None
            for i, line in enumerate(text.splitlines(), 1):
                st = line.strip()
                if st.startswith("```"):
                    in_bash, buf, start = st.startswith("```bash"), "", None
                    continue
                if not in_bash or not st or st.startswith("#"):
                    continue
                if start is None:
                    start = i
                buf += " " + st.rstrip("\\")
                if line.rstrip().endswith("\\"):
                    continue          # 백슬래시로 다음 줄에 이어진다
                if src.search(buf):
                    add("error", "worktree-path",
                        f"{os.path.relpath(path, REPO)}:{start}: worktree 스킬인데 소스를"
                        " 상대경로로 읽는다 — --source 지정 시 다른 브랜치를 보게 된다."
                        " 탐색 루트를 변수로 잡아 붙인다")
                buf, start = "", None


def run_deep(manifests):
    r = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "lint-skills.py")],
                       capture_output=True, text=True)
    if "에러 0건" not in r.stdout:
        add("error", "lint", "lint-skills.py 에 에러가 있다 — 출력을 직접 확인한다")
    for p, m in manifests.items():
        for h in m.get("hooks", []):
            test = h.get("selfTest")
            if not test:
                continue
            path = os.path.join(REPO, "plugins", p, test)
            rc = subprocess.run(["sh", path], capture_output=True, text=True).returncode
            if rc != 0:
                add("error", "hook", f"{p}: 훅 selfTest 실패 ({test})")


def main():
    deep = "--deep" in sys.argv
    market = load(MARKETPLACE)
    if market is None:
        return 2
    dirs = plugin_dirs()

    check_versions(market, dirs)
    check_registration(market, dirs)
    manifests = {}
    for p in dirs:
        m = manifest_of(p)
        if m:
            manifests[p] = m
            check_manifest_truth(p, m)
    check_readme(dirs, manifests)
    check_slash_references(dirs)
    check_config_path(dirs)
    check_worktree_source_path(dirs)
    if deep:
        run_deep(manifests)

    errors = [f for f in findings if f[0] == "error"]
    warns = [f for f in findings if f[0] == "warn"]
    for level, area, msg in errors + warns:
        print(f"{'❌' if level == 'error' else '⚠️ '} [{area}] {msg}")
    print(f"\n플러그인 {len(dirs)}개 · 매니페스트 {len(manifests)}개"
          f" · 오류 {len(errors)}건 · 경고 {len(warns)}건" + ("" if deep else " (--deep 미실행)"))
    return 2 if errors else (1 if warns else 0)


if __name__ == "__main__":
    sys.exit(main())
