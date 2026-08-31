/**
 * Claude usage engine — reads the local Claude Code OAuth credentials and
 * queries Anthropic's usage endpoint for rate-limit windows (5h / weekly /
 * per-model), with a short-lived on-disk cache so the statusline can render
 * cheaply on every refresh.
 *
 * This is a clean-room implementation against Anthropic's public OAuth usage
 * API. It depends on nothing but Node built-ins.
 *
 * Auth sources (in order):
 *   1. macOS Keychain service "Claude Code-credentials[-<hash>]"
 *   2. <configDir>/.credentials.json   (nested under claudeAiOauth, or flat)
 *
 * Endpoints:
 *   - GET  https://api.anthropic.com/api/oauth/usage      (Bearer + oauth beta)
 *   - POST https://platform.claude.com/v1/oauth/token     (refresh_token grant)
 */

import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  existsSync,
  mkdirSync,
  readFileSync,
  renameSync,
  writeFileSync,
} from "node:fs";
import https from "node:https";
import { homedir, userInfo } from "node:os";
import { dirname, join } from "node:path";

const API_TIMEOUT_MS = 10_000;
const CACHE_TTL_MS = 90_000; // match Claude Code's HUD poll cadence
const CACHE_TTL_FAILURE_MS = 15_000; // back off briefly on hard failures
const OAUTH_CLIENT_ID =
  process.env.CLAUDE_CODE_OAUTH_CLIENT_ID ||
  "9d1c250a-e61b-44d9-88ed-5944d1962f5e";

function configDir() {
  return process.env.CLAUDE_CONFIG_DIR || join(homedir(), ".claude");
}

function cachePath() {
  return join(configDir(), "plugins", "hud", ".usage-cache.json");
}

// --- credentials ---------------------------------------------------------

function unwrap(parsed) {
  const c = parsed?.claudeAiOauth || parsed;
  if (!c || !c.accessToken) return null;
  return {
    accessToken: c.accessToken,
    expiresAt: c.expiresAt,
    refreshToken: c.refreshToken,
  };
}

function isExpired(creds) {
  return creds.expiresAt != null && creds.expiresAt <= Date.now();
}

function keychainServiceName() {
  const cd = process.env.CLAUDE_CONFIG_DIR;
  if (cd) {
    const hash = createHash("sha256").update(cd).digest("hex").slice(0, 8);
    return `Claude Code-credentials-${hash}`;
  }
  return "Claude Code-credentials";
}

function readKeychain() {
  if (process.platform !== "darwin") return null;
  const service = keychainServiceName();
  let account;
  try {
    account = userInfo().username?.trim() || undefined;
  } catch {
    account = undefined;
  }
  for (const acc of [account, undefined]) {
    try {
      const args = acc
        ? ["find-generic-password", "-s", service, "-a", acc, "-w"]
        : ["find-generic-password", "-s", service, "-w"];
      const out = execFileSync("/usr/bin/security", args, {
        encoding: "utf-8",
        timeout: 2000,
        stdio: ["pipe", "pipe", "pipe"],
      }).trim();
      if (!out) continue;
      const creds = unwrap(JSON.parse(out));
      if (creds) return creds;
    } catch {
      /* try next account */
    }
  }
  return null;
}

function readCredentialsFile() {
  try {
    const p = join(configDir(), ".credentials.json");
    if (!existsSync(p)) return null;
    return unwrap(JSON.parse(readFileSync(p, "utf-8")));
  } catch {
    return null;
  }
}

function getCredentials() {
  return readKeychain() || readCredentialsFile();
}

function writeBackCredentials(creds) {
  try {
    const p = join(configDir(), ".credentials.json");
    if (!existsSync(p)) return;
    const parsed = JSON.parse(readFileSync(p, "utf-8"));
    const target = parsed.claudeAiOauth || parsed;
    target.accessToken = creds.accessToken;
    if (creds.expiresAt != null) target.expiresAt = creds.expiresAt;
    if (creds.refreshToken) target.refreshToken = creds.refreshToken;
    const tmp = `${p}.tmp.${process.pid}`;
    writeFileSync(tmp, JSON.stringify(parsed, null, 2), { mode: 0o600 });
    renameSync(tmp, p);
  } catch {
    /* best-effort */
  }
}

// --- http ----------------------------------------------------------------

function refreshAccessToken(refreshToken) {
  return new Promise((resolve) => {
    const body = new URLSearchParams({
      grant_type: "refresh_token",
      refresh_token: refreshToken,
      client_id: OAUTH_CLIENT_ID,
    }).toString();
    const req = https.request(
      {
        hostname: "platform.claude.com",
        path: "/v1/oauth/token",
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          "Content-Length": Buffer.byteLength(body),
        },
        timeout: API_TIMEOUT_MS,
      },
      (res) => {
        let data = "";
        res.on("data", (c) => (data += c));
        res.on("end", () => {
          if (res.statusCode === 200) {
            try {
              const p = JSON.parse(data);
              if (p.access_token) {
                resolve({
                  accessToken: p.access_token,
                  refreshToken: p.refresh_token || refreshToken,
                  expiresAt: p.expires_in
                    ? Date.now() + p.expires_in * 1000
                    : p.expires_at,
                });
                return;
              }
            } catch {
              /* fallthrough */
            }
          }
          resolve(null);
        });
      },
    );
    req.on("error", () => resolve(null));
    req.on("timeout", () => {
      req.destroy();
      resolve(null);
    });
    req.end(body);
  });
}

function fetchUsage(accessToken) {
  return new Promise((resolve) => {
    const req = https.request(
      {
        hostname: "api.anthropic.com",
        path: "/api/oauth/usage",
        method: "GET",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "anthropic-beta": "oauth-2025-04-20",
          "Content-Type": "application/json",
        },
        timeout: API_TIMEOUT_MS,
      },
      (res) => {
        let data = "";
        res.on("data", (c) => (data += c));
        res.on("end", () => {
          if (res.statusCode === 200) {
            try {
              resolve({ data: JSON.parse(data) });
            } catch {
              resolve({ data: null });
            }
          } else if (res.statusCode === 429) {
            resolve({ data: null, rateLimited: true });
          } else {
            resolve({ data: null });
          }
        });
      },
    );
    req.on("error", () => resolve({ data: null }));
    req.on("timeout", () => {
      req.destroy();
      resolve({ data: null });
    });
    req.end();
  });
}

// --- parse / cache -------------------------------------------------------

function clampPct(v) {
  if (v == null || !isFinite(v)) return 0;
  return Math.max(0, Math.min(100, v));
}

function parseUsage(r) {
  const fiveHour = r.five_hour?.utilization;
  const sevenDay = r.seven_day?.utilization;
  if (fiveHour == null && sevenDay == null) return null;
  const out = {
    fiveHourPercent: clampPct(fiveHour),
    weeklyPercent: clampPct(sevenDay),
    fiveHourResetsAt: r.five_hour?.resets_at ?? null,
    weeklyResetsAt: r.seven_day?.resets_at ?? null,
  };
  if (r.seven_day_sonnet?.utilization != null) {
    out.sonnetWeeklyPercent = clampPct(r.seven_day_sonnet.utilization);
    out.sonnetWeeklyResetsAt = r.seven_day_sonnet.resets_at ?? null;
  }
  if (r.seven_day_opus?.utilization != null) {
    out.opusWeeklyPercent = clampPct(r.seven_day_opus.utilization);
    out.opusWeeklyResetsAt = r.seven_day_opus.resets_at ?? null;
  }
  return out;
}

function readCache() {
  try {
    const p = cachePath();
    if (!existsSync(p)) return null;
    return JSON.parse(readFileSync(p, "utf-8"));
  } catch {
    return null;
  }
}

function writeCache(entry) {
  try {
    const p = cachePath();
    const dir = dirname(p);
    if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
    const tmp = `${p}.tmp.${process.pid}`;
    writeFileSync(tmp, JSON.stringify(entry, null, 2));
    renameSync(tmp, p);
  } catch {
    /* ignore */
  }
}

function cacheFresh(cache) {
  if (!cache) return false;
  const ttl = cache.error ? CACHE_TTL_FAILURE_MS : CACHE_TTL_MS;
  return Date.now() - cache.timestamp < ttl;
}

/**
 * Returns { rateLimits, error?, stale? }.
 *   rateLimits: parsed usage object, or null when unavailable
 *   error: 'no_credentials' | 'auth' | 'network' | 'rate_limited'
 *   stale: true when serving older cached data after a failed refresh
 */
export async function getUsage() {
  const cache = readCache();
  if (cacheFresh(cache)) {
    if (cache.data) return { rateLimits: cache.data, stale: cache.error ? true : undefined };
    if (cache.error) return { rateLimits: null, error: cache.errorReason };
  }

  let creds = getCredentials();
  if (!creds) {
    writeCache({ timestamp: Date.now(), error: true, errorReason: "no_credentials" });
    return { rateLimits: null, error: "no_credentials" };
  }

  if (isExpired(creds)) {
    if (!creds.refreshToken) {
      writeCache({ timestamp: Date.now(), error: true, errorReason: "auth" });
      return { rateLimits: null, error: "auth" };
    }
    const refreshed = await refreshAccessToken(creds.refreshToken);
    if (!refreshed) {
      writeCache({ timestamp: Date.now(), error: true, errorReason: "auth" });
      return { rateLimits: null, error: "auth" };
    }
    creds = { ...creds, ...refreshed };
    writeBackCredentials(creds);
  }

  const result = await fetchUsage(creds.accessToken);
  if (result.rateLimited) {
    // keep prior data if we have it; just flag the limited state
    writeCache({
      timestamp: Date.now(),
      data: cache?.data ?? null,
      error: true,
      errorReason: "rate_limited",
    });
    if (cache?.data) return { rateLimits: cache.data, error: "rate_limited", stale: true };
    return { rateLimits: null, error: "rate_limited" };
  }
  if (!result.data) {
    writeCache({
      timestamp: Date.now(),
      data: cache?.data ?? null,
      error: true,
      errorReason: "network",
    });
    if (cache?.data) return { rateLimits: cache.data, error: "network", stale: true };
    return { rateLimits: null, error: "network" };
  }

  const usage = parseUsage(result.data);
  writeCache({ timestamp: Date.now(), data: usage, error: !usage });
  return { rateLimits: usage };
}
