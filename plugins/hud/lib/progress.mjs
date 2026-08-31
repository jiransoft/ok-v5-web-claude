/**
 * Task-progress segment — reads Claude Code's native Task state from
 * <configDir>/tasks/session-<short>/N.json and renders a progress bar.
 *
 * Task file schema: { id, subject, description, activeForm, status, ... }
 * status: pending | in_progress | completed  (deleted tasks remove the file)
 */

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { C } from "./render.mjs";

function configDir() {
  return process.env.CLAUDE_CONFIG_DIR || join(homedir(), ".claude");
}

// Progress coloring: high == good (opposite of usage).
function pctColor(pct) {
  if (pct >= 100) return C.green;
  if (pct >= 70) return C.cyan;
  if (pct >= 20) return C.yellow;
  return C.red;
}

function readTaskDir(dir) {
  if (!dir || !existsSync(dir)) return [];
  const out = [];
  for (const f of readdirSync(dir)) {
    if (!/^\d+\.json$/.test(f)) continue;
    try {
      out.push(JSON.parse(readFileSync(join(dir, f), "utf-8")));
    } catch {
      /* skip unreadable task */
    }
  }
  return out;
}

function loadTasks(sessionId) {
  if (!sessionId) return [];
  const short = sessionId.split("-")[0];
  const candidates = [
    join(configDir(), "tasks", `session-${short}`), // current format
    join(configDir(), "tasks", sessionId), // older full-UUID format
  ];
  for (const dir of candidates) {
    const tasks = readTaskDir(dir);
    if (tasks.length > 0) return tasks;
  }
  return [];
}

function bar(done, total, width = 10) {
  const filled = total > 0 ? Math.round((done / total) * width) : 0;
  return "▓".repeat(filled) + "░".repeat(Math.max(0, width - filled));
}

function trunc(s, n) {
  if (!s) return "";
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

export function renderProgress(sessionId) {
  const tasks = loadTasks(sessionId);
  if (tasks.length === 0) return "";
  const total = tasks.length;
  const done = tasks.filter((t) => t.status === "completed").length;
  const active = tasks.find((t) => t.status === "in_progress");
  const pending = tasks.filter((t) => t.status === "pending").length;
  // floor so we never show 100% until every task is actually done
  const pct = Math.floor((done / total) * 100);
  const allDone = done === total;

  let seg = `${pctColor(pct)}📋 ${bar(done, total)} ${done}/${total} ${pct}%${C.reset}`;

  if (pending > 0) {
    seg += ` ${C.dim}·${C.reset} ${C.dim}대기 ${pending}${C.reset}`;
  }
  if (active) {
    const label = trunc(active.activeForm || active.subject || "", 24);
    if (label) seg += ` ${C.dim}·${C.reset} ${C.yellow}${label}${C.reset}`;
  } else if (allDone) {
    seg += ` ${C.green}✓${C.reset}`;
  }
  return seg;
}
