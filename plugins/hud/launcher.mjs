#!/usr/bin/env node
/**
 * Stable hud launcher.
 *
 * `/hud:setup` copies this file to <configDir>/hud/hud.mjs and points the
 * user's statusLine at it. At render time it locates the newest installed
 * `hud` plugin version under the plugin cache and runs its statusline entry,
 * so the statusLine keeps working across `claude plugin marketplace update`
 * without the user re-running setup.
 *
 * Falls back silently (prints an empty line) if no install is found.
 */

import { existsSync, readdirSync, statSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

function configDir() {
  return process.env.CLAUDE_CONFIG_DIR || join(homedir(), ".claude");
}

function resolveEntry() {
  const base = join(
    configDir(),
    "plugins",
    "cache",
    "okep-butler",
    "hud",
  );
  if (!existsSync(base)) return null;
  let versions;
  try {
    versions = readdirSync(base).filter((v) => {
      try {
        return (
          statSync(join(base, v)).isDirectory() &&
          existsSync(join(base, v, "bin", "statusline.mjs"))
        );
      } catch {
        return false;
      }
    });
  } catch {
    return null;
  }
  if (versions.length === 0) return null;
  // Newest version wins (numeric-aware compare).
  versions.sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  const latest = versions[versions.length - 1];
  return join(base, latest, "bin", "statusline.mjs");
}

const entry = resolveEntry();
if (entry) {
  // Importing runs the entry's main(), which reads stdin (fd 0) and prints.
  await import(pathToFileURL(entry).href);
} else {
  process.stdout.write("\n");
}
