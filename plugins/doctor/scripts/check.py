#!/usr/bin/env python3
"""플러그인 환경 진단 — 각 플러그인이 동봉한 doctor.json 만 읽고 점검한다.

플러그인별 지식을 하드코딩하지 않는다. 점검 항목이 늘거나 줄면 해당 플러그인의
doctor.json 만 고친다. 스키마는 reference/manifest-schema.md.

사용법:
  check.py [--deep] [--json] [--source DIR] [--project DIR]

  --deep       훅 selfTest 까지 실행 (기본은 파일 존재·권한만)
  --json       기계 판독용 JSON 출력
  --source     매니페스트 탐색 루트를 직접 지정 (개발·CI 용)
  --project    .claude/plugins.json 을 읽을 프로젝트 경로
               (기본: 본체 레포 루트. worktree 안에서 실행돼도 본체를 본다 —
                plugins.json 은 gitignore 대상이라 worktree 에는 없다)

종료코드: 0 정상 · 1 경고만 · 2 오류 있음
"""
import argparse
import glob
import json
import os
import shutil
import stat
import subprocess
import sys

HOME = os.path.expanduser("~")
ERROR, WARN, OK, INFO = "error", "warn", "ok", "info"
MARK = {ERROR: "❌", WARN: "⚠️ ", OK: "✅", INFO: "·"}


def load_json(path):
    try:
        with open(os.path.expanduser(path), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def find_manifests(source=None):
    """doctor.json 을 설치 레이아웃 양쪽에서 찾는다. 이름 중복은 처음 것을 쓴다."""
    patterns = []
    if source:
        patterns += [os.path.join(source, "*", "doctor.json"),
                     os.path.join(source, "plugins", "*", "doctor.json")]
    else:
        root = os.environ.get("CLAUDE_PLUGIN_ROOT")
        if root:
            # 마켓플레이스 클론 레이아웃: <mp>/plugins/<플러그인>/
            patterns.append(os.path.join(root, "..", "*", "doctor.json"))
            # 캐시 레이아웃: cache/<mp>/<플러그인>/<버전>/
            patterns.append(os.path.join(root, "..", "..", "*", "*", "doctor.json"))
        patterns += [
            os.path.join(HOME, ".claude/plugins/marketplaces/*/plugins/*/doctor.json"),
            os.path.join(HOME, ".claude/plugins/cache/*/*/*/doctor.json"),
        ]
    found = {}
    for pat in patterns:
        for path in sorted(glob.glob(pat)):
            m = load_json(path)
            if not m or not m.get("plugin"):
                continue
            found.setdefault(m["plugin"], (os.path.dirname(os.path.abspath(path)), m))
    return found


def mcp_servers(project):
    cfg = load_json(os.path.join(HOME, ".claude.json")) or {}
    names = set(cfg.get("mcpServers") or {})
    names |= set((cfg.get("projects", {}).get(os.path.abspath(project), {})
                  .get("mcpServers") or {}))
    local = load_json(os.path.join(project, ".mcp.json")) or {}
    names |= set(local.get("mcpServers") or {})
    return names


def major_version(cmd):
    try:
        out = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    text = (out.stdout or "") + (out.stderr or "")
    digits = ""
    for ch in text:
        if ch.isdigit():
            digits += ch
        elif digits:
            break
    return int(digits) if digits else None


def check_config(spec, project, add):
    """설정은 '깨졌을 때'만 오류다.

    프로젝트가 이 플러그인을 안 쓰면 섹션이 없는 게 정상이다 — 설치된 모든 플러그인의
    설정을 모든 프로젝트가 갖출 이유는 없다. 그래서 파일 없음은 정보, 섹션 없음은 경고,
    섹션이 있는데 필수 키가 빈 경우만 오류로 둔다.
    """
    key = spec.get("key")
    path = os.path.join(project, ".claude", "plugins.json")
    if not os.path.exists(path):
        add(INFO, f"`{key}` 섹션 미설정 (프로젝트에 plugins.json 없음)")
        return
    cfg = load_json(path)
    if cfg is None:
        add(ERROR, "`.claude/plugins.json` 이 유효한 JSON 이 아니다")
        return
    section = cfg.get(key)
    if section is None:
        lvl = WARN if spec.get("required") else INFO
        add(lvl, f"`{key}` 섹션 없음 — 이 프로젝트에서 쓰려면 설정이 필요하다",
            setup=bool(spec.get("required")))
        return
    missing = [k for k in spec.get("required", []) if not section.get(k)]
    if missing:
        add(ERROR, f"`{key}` 필수 키 누락: {', '.join(missing)}", setup=True)
    known = set(spec.get("required", [])) | set(spec.get("optional", []))
    unknown = [k for k in section if k not in known]
    if unknown:
        add(WARN, f"`{key}` 에 알 수 없는 키: {', '.join(unknown)} — 오타 또는 구 키")
    if not missing and not unknown:
        add(OK, f"`{key}` 섹션 정상 ({len(section)}개 키)")


def check_files(specs, add):
    for f in specs:
        path = os.path.expanduser(f["path"])
        if not os.path.exists(path):
            lvl = ERROR if f.get("required") else INFO
            msg = f"`{f['path']}` 없음"
            if f.get("usedBy"):
                msg += f" (필요: {f['usedBy']})"
            if f.get("hint"):
                msg += f" — {f['hint']}"
            add(lvl, msg, setup=f.get("required", False))
            continue
        if os.path.getsize(path) == 0:
            add(ERROR if f.get("required") else WARN, f"`{f['path']}` 가 비어 있다")
            continue
        want = f.get("mode")
        if want:
            actual = stat.S_IMODE(os.stat(path).st_mode)
            if actual & ~int(want, 8):
                add(WARN, f"`{f['path']}` 권한 {actual:03o} — {want} 권장 · `chmod {want} {f['path']}`")
                continue
        add(OK, f"`{f['path']}` 정상")


def check_commands(specs, add):
    for c in specs:
        name = c["name"]
        if not shutil.which(name):
            lvl = ERROR if c.get("required") else INFO
            msg = f"`{name}` 없음"
            if c.get("note"):
                msg += f" ({c['note']})"
            if c.get("install"):
                msg += f" · `{c['install']}`"
            add(lvl, msg)
            continue
        need = c.get("minVersion")
        if need:
            got = major_version(name)
            if got is not None and got < need:
                add(ERROR if c.get("required") else WARN,
                    f"`{name}` {got} — {need} 이상 필요")
                continue
            add(OK, f"`{name}` {got if got is not None else ''} 확인".replace("  ", " "))
            continue
        add(OK, f"`{name}` 확인")


def check_mcp(specs, servers, add):
    for m in specs:
        name = m["server"]
        if name in servers:
            add(OK, f"MCP `{name}` 설정됨")
        else:
            add(ERROR if m.get("required") else WARN,
                f"MCP 서버 `{name}` 미설정 (필요: {m.get('usedBy', '전체')}) — `claude mcp add {name} …`")


def check_settings(specs, add):
    settings = load_json(os.path.join(HOME, ".claude/settings.json")) or {}
    for s in specs:
        node = settings
        for part in s["path"].split("."):
            node = node.get(part) if isinstance(node, dict) else None
        text = node if isinstance(node, str) else ""
        if s.get("contains", "") in text and text:
            add(OK, f"`settings.json` {s['path']} 배선됨")
        else:
            fix = f" · `{s['fix']}`" if s.get("fix") else ""
            add(ERROR, f"`settings.json` {s['path']} 미배선{fix}")


def check_hooks(specs, plugin_dir, deep, add):
    for h in specs:
        script = os.path.join(plugin_dir, h["script"])
        if not os.path.exists(script):
            add(ERROR, f"훅 스크립트 없음: {h['script']}")
            continue
        add(OK, f"훅 `{h['event']}` → {h['script']}")
        test = h.get("selfTest")
        if deep and test:
            tpath = os.path.join(plugin_dir, test)
            if not os.path.exists(tpath):
                add(WARN, f"훅 selfTest 없음: {test}")
                continue
            r = subprocess.run(["sh", tpath], capture_output=True, text=True, timeout=120)
            tail = (r.stdout or r.stderr or "").strip().splitlines()
            add(OK if r.returncode == 0 else ERROR,
                f"훅 selfTest {'통과' if r.returncode == 0 else '실패'}"
                + (f" — {tail[-1]}" if tail else ""))


def project_hygiene(project, manifests, add):
    path = os.path.join(project, ".claude", "plugins.json")
    if not os.path.exists(path):
        add(INFO, "`.claude/plugins.json` 없음 — 이 프로젝트에서는 스킬이 값을 되묻는다")
        return
    cfg = load_json(path)
    if cfg is None:
        add(ERROR, "`.claude/plugins.json` 파싱 실패 — 쉼표·따옴표 확인")
    else:
        # 어떤 매니페스트도 주장하지 않는 섹션 — 플러그인 개명 후 남은 구 키가 여기 걸린다
        claimed = {m.get("config", {}).get("key") for _, m in manifests.values()}
        claimed.discard(None)
        orphans = [k for k in cfg if k not in claimed]
        if orphans:
            add(WARN, f"매니페스트가 없는 설정 섹션: {', '.join(orphans)}"
                      " — 플러그인 개명 후 남은 구 키이거나 오타다")
    ignore = os.path.join(project, ".gitignore")
    listed = False
    if os.path.exists(ignore):
        with open(ignore, encoding="utf-8") as f:
            listed = any(".claude/plugins.json" in line for line in f)
    if listed:
        add(OK, "`.claude/plugins.json` 이 .gitignore 에 등록됨")
    else:
        add(WARN, "`.claude/plugins.json` 이 .gitignore 에 없다 — 토큰·Cloud ID 유출 위험"
                  f" · `echo '.claude/plugins.json' >> {os.path.join(project, '.gitignore')}`")


def marketplace_of(path):
    """매니페스트 경로에서 마켓플레이스 이름을 뽑는다. 못 뽑으면 None."""
    parts = os.path.abspath(path).split(os.sep)
    for anchor in ("marketplaces", "cache"):
        if anchor in parts:
            i = parts.index(anchor)
            if i + 1 < len(parts):
                return parts[i + 1]
    return None


def orphan_plugins(manifests, add):
    """활성 플러그인 중 매니페스트가 없는 것을 가린다.

    doctor 를 동봉하는 마켓플레이스의 플러그인인데 매니페스트가 없으면 개명·미갱신 신호다.
    외부 마켓플레이스 플러그인은 애초에 doctor 대상이 아니므로 정보로만 남긴다.
    """
    known_markets = {marketplace_of(d) for d, _ in manifests.values()} - {None}
    settings = load_json(os.path.join(HOME, ".claude/settings.json")) or {}
    enabled = [k for k, v in (settings.get("enabledPlugins") or {}).items() if v]
    for entry in enabled:
        name, _, market = entry.partition("@")
        if name in manifests:
            continue
        if market in known_markets:
            add(WARN, f"`{entry}` 활성 상태인데 매니페스트가 없다 — 개명됐거나 갱신 전이다"
                      " · `claude plugin marketplace update`")
        else:
            add(INFO, f"`{entry}` — doctor 매니페스트 없는 외부 플러그인 (진단 대상 아님)")
    return enabled


def version_drift(manifests, add):
    """캐시에 설치된 버전이 마켓플레이스 클론이 선언한 버전보다 낡았는지 본다."""
    for name, (plugin_dir, _) in sorted(manifests.items()):
        installed = (load_json(os.path.join(plugin_dir, ".claude-plugin", "plugin.json")) or {}).get("version")
        market = marketplace_of(plugin_dir)
        if not installed or not market:
            continue
        mpath = os.path.join(HOME, ".claude/plugins/marketplaces", market,
                             ".claude-plugin", "marketplace.json")
        declared = None
        for entry in (load_json(mpath) or {}).get("plugins", []):
            if entry.get("name") == name:
                declared = entry.get("version")
        if declared and declared != installed:
            add(WARN, f"`{name}` 설치본 {installed} · 마켓플레이스 {declared} — 갱신 필요"
                      " · `claude plugin marketplace update`")


def main_repo_root():
    """cwd 가 worktree 안이면 본체 레포 루트를, 아니면 cwd 를 준다.

    plugins.json 은 gitignore 대상이라 worktree 에 체크아웃되지 않는다. cwd 를 그대로
    쓰면 worktree 에서 진단할 때 설정이 있는데도 "설정 없음" 으로 오진한다.
    --git-common-dir 는 worktree 안에서도 본체의 .git 을 준다.
    """
    try:
        out = subprocess.run(["git", "rev-parse", "--git-common-dir"],
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return os.getcwd()
    gcd = out.stdout.strip()
    if out.returncode != 0 or not gcd:
        return os.getcwd()
    if not os.path.isabs(gcd):
        gcd = os.path.join(os.getcwd(), gcd)
    root = os.path.realpath(os.path.join(gcd, os.pardir))
    return root if os.path.isdir(root) else os.getcwd()


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--deep", action="store_true")
    ap.add_argument("--json", dest="as_json", action="store_true")
    ap.add_argument("--source")
    ap.add_argument("--project", default=main_repo_root())
    args = ap.parse_args()

    manifests = find_manifests(args.source)
    servers = mcp_servers(args.project)
    report, counts = {}, {ERROR: 0, WARN: 0, OK: 0, INFO: 0}

    def section(title):
        items = report.setdefault(title, [])

        def add(level, message, setup=False):
            items.append({"level": level, "message": message, "setup": setup})
            counts[level] += 1
        return add

    if not manifests:
        print("❌ doctor.json 매니페스트를 찾지 못했다. 플러그인이 설치·갱신됐는지 확인한다"
              " (`claude plugin marketplace update`).")
        return 2

    for name in sorted(manifests):
        plugin_dir, m = manifests[name]
        add = section(name)
        if m.get("config"):
            check_config(m["config"], args.project, add)
        check_files(m.get("files", []), add)
        check_commands(m.get("commands", []), add)
        check_mcp(m.get("mcp", []), servers, add)
        check_settings(m.get("settings", []), add)
        check_hooks(m.get("hooks", []), plugin_dir, args.deep, add)
        if not report[name]:
            add(INFO, "점검 항목 없음 (설정 불필요)")

    hy = section("프로젝트 · 설치 위생")
    project_hygiene(args.project, manifests, hy)
    version_drift(manifests, hy)
    orphan_plugins(manifests, hy)

    if args.as_json:
        print(json.dumps({"report": report, "counts": counts}, ensure_ascii=False, indent=2))
    else:
        for title, items in report.items():
            worst = ERROR if any(i["level"] == ERROR for i in items) else (
                WARN if any(i["level"] == WARN for i in items) else OK)
            print(f"\n{MARK[worst]} {title}")
            for i in items:
                print(f"   {MARK[i['level']]} {i['message']}")
            setup = manifests.get(title, (None, {}))[1].get("setup")
            needs_fix = any(i["setup"] and i["level"] in (ERROR, WARN) for i in items)
            if needs_fix and setup:
                print(f"   → 조치: {setup}")
        print(f"\n오류 {counts[ERROR]}건 · 경고 {counts[WARN]}건 · 정상 {counts[OK]}건")
        print(f"진단 대상 플러그인 {len(manifests)}개 · 프로젝트 {args.project}")

    return 2 if counts[ERROR] else (1 if counts[WARN] else 0)


if __name__ == "__main__":
    sys.exit(main())
