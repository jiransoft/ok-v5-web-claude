#!/usr/bin/env node
/**
 * HUD statusline (clean-room).
 *
 * Reads the Claude Code statusline JSON on stdin and prints a single line:
 *   <usage limits> │ ctx:NN% │ <model> │ <git> │ $cost │ 📋 <task progress>
 *
 * - Usage limits come from the local Claude OAuth credentials + Anthropic's
 *   usage API (see lib/usage.mjs), cached for 90s so renders stay cheap.
 * - Task progress reads Claude Code's native Task state (see lib/progress.mjs).
 *
 * Implemented from scratch on Node built-ins only — no third-party code.
 * Requires Node >= 20.
 */

import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import {
  C,
  SEP,
  renderContext,
  renderCost,
  renderModel,
  renderUsage,
  renderUsageError,
} from "../lib/render.mjs";
import { renderProgress } from "../lib/progress.mjs";
import { getUsage } from "../lib/usage.mjs";

function readStdin() {
  try {
    return readFileSync(0, "utf-8");
  } catch {
    return "";
  }
}

function parseInput(raw) {
  try {
    return JSON.parse(raw || "{}");
  } catch {
    return {};
  }
}

function contextPercent(input) {
  const cw = input.context_window;
  if (!cw) return null;
  if (typeof cw.used_percentage === "number" && !Number.isNaN(cw.used_percentage)) {
    return cw.used_percentage;
  }
  const size = cw.context_window_size;
  const u = cw.current_usage;
  if (size > 0 && u) {
    const total =
      (u.input_tokens ?? 0) +
      (u.cache_creation_input_tokens ?? 0) +
      (u.cache_read_input_tokens ?? 0);
    return (total / size) * 100;
  }
  return null;
}

// Read the current git branch directly from .git/HEAD — no subprocess.
function gitBranch(cwd) {
  if (!cwd) return "";
  try {
    let dir = cwd;
    for (let i = 0; i < 8; i++) {
      const head = join(dir, ".git", "HEAD");
      if (existsSync(head)) {
        const txt = readFileSync(head, "utf-8").trim();
        const m = txt.match(/ref:\s*refs\/heads\/(.+)$/);
        return m ? m[1] : txt.slice(0, 7); // detached: short sha
      }
      const parent = join(dir, "..");
      if (parent === dir) break;
      dir = parent;
    }
  } catch {
    /* ignore */
  }
  return "";
}

async function main() {
  const raw = readStdin();
  const input = parseInput(raw);

  const sessionId = input.session_id || input.sessionId || null;
  const cwd = input.cwd || input.workspace?.current_dir || null;
  const model = input.model?.display_name || input.model?.id || "";
  const cost = input.cost?.total_cost_usd;

  // Usage is the only async/network piece; everything else is local.
  let usageSeg = "";
  try {
    const { rateLimits, error, stale } = await getUsage();
    usageSeg = rateLimits ? renderUsage(rateLimits, stale) : renderUsageError(error);
  } catch {
    usageSeg = "";
  }

  const branch = gitBranch(cwd);
  const segments = [
    usageSeg,
    renderContext(contextPercent(input)),
    renderModel(model),
    branch ? `${C.dim}git:(${C.reset}${branch}${C.dim})${C.reset}` : "",
    renderCost(cost),
    renderProgress(sessionId),
  ].filter(Boolean);

  process.stdout.write(segments.join(SEP) + "\n");
}

main().catch(() => {
  // Never let the statusline crash; emit nothing on catastrophic failure.
  process.stdout.write("\n");
});
