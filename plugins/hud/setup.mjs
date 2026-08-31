#!/usr/bin/env node
/**
 * hud setup — activates the statusline in the user's Claude Code config.
 *
 * Claude Code does NOT let a plugin auto-enable the main statusLine (only
 * `agent` / `subagentStatusLine` are honored from plugin settings), so this
 * script does the wiring the plugin can't:
 *
 *   1. Copy launcher.mjs → <configDir>/hud/hud.mjs   (version-stable launcher)
 *   2. Set statusLine in <configDir>/settings.json   (backing up the old one)
 *
 * Idempotent and safe to re-run. Aborts rather than clobbering an unparseable
 * settings.json.
 */

import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
} from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));

function configDir() {
  return process.env.CLAUDE_CONFIG_DIR || join(homedir(), ".claude");
}

function log(msg) {
  process.stdout.write(msg + "\n");
}

function main() {
  const cfg = configDir();
  const hudDir = join(cfg, "hud");
  const launcherDest = join(hudDir, "hud.mjs");
  const launcherSrc = join(HERE, "launcher.mjs");

  // 1) install the stable launcher
  if (!existsSync(hudDir)) mkdirSync(hudDir, { recursive: true });
  copyFileSync(launcherSrc, launcherDest);
  log(`✓ launcher 설치: ${launcherDest}`);

  // 2) wire statusLine into settings.json
  const settingsPath = join(cfg, "settings.json");
  let settings = {};
  if (existsSync(settingsPath)) {
    let raw;
    try {
      raw = readFileSync(settingsPath, "utf-8");
      settings = JSON.parse(raw || "{}");
    } catch {
      log(
        `✗ ${settingsPath} 를 파싱할 수 없습니다. 수동으로 statusLine을 추가하세요:\n` +
          `    "statusLine": { "type": "command", "command": "node ${launcherDest}" }`,
      );
      process.exitCode = 1;
      return;
    }
    // back up the previous settings before changing them
    const backup = `${settingsPath}.bak`;
    try {
      writeFileSync(backup, raw);
      log(`✓ 기존 settings 백업: ${backup}`);
    } catch {
      /* best-effort */
    }
  }

  const prev = settings.statusLine;
  settings.statusLine = {
    type: "command",
    command: `node ${launcherDest}`,
  };
  writeFileSync(settingsPath, JSON.stringify(settings, null, 2) + "\n");

  if (prev && JSON.stringify(prev) !== JSON.stringify(settings.statusLine)) {
    log(`✓ statusLine 교체 (이전: ${prev.command ?? JSON.stringify(prev)})`);
  } else {
    log(`✓ statusLine 설정: node ${launcherDest}`);
  }
  log("완료. 새 세션부터 적용됩니다 (실행 중이면 statusline이 곧 갱신됨).");
}

main();
