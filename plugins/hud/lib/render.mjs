/**
 * Statusline formatting helpers — ANSI colors and element renderers.
 * No dependencies; pure string building.
 */

export const C = {
  reset: "\x1b[0m",
  dim: "\x1b[2m",
  bold: "\x1b[1m",
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  cyan: "\x1b[36m",
};

export const SEP = `${C.dim} │ ${C.reset}`;

// Usage/context coloring: high == bad.
function loadColor(pct) {
  if (pct >= 90) return C.red;
  if (pct >= 70) return C.yellow;
  return C.green;
}

// Format an ISO reset timestamp as a short countdown ("3h42m", "2d5h").
// Returns "" when missing or already elapsed.
function resetIn(iso) {
  if (!iso) return "";
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return "";
  const diff = t - Date.now();
  if (diff <= 0) return "";
  const mins = Math.floor(diff / 60_000);
  const hours = Math.floor(mins / 60);
  const days = Math.floor(hours / 24);
  if (days > 0) return `${days}d${hours % 24}h`;
  return `${hours}h${mins % 60}m`;
}

function bucket(label, pct, resetsAt, dimLabel = true) {
  const r = resetIn(resetsAt);
  const tail = r ? `${C.dim}(${r})${C.reset}` : "";
  const lab = dimLabel ? `${C.dim}${label}:${C.reset}` : `${label}:`;
  return `${lab}${loadColor(pct)}${pct}%${C.reset}${tail}`;
}

/**
 * Render the rate-limit segment from a parsed usage object.
 * Shape: 5h:22%(3h3m) wk:19%(1h43m) sn:0% op:5%
 */
export function renderUsage(u, stale) {
  if (!u) return "";
  const parts = [bucket("5h", u.fiveHourPercent, u.fiveHourResetsAt, false)];
  if (u.weeklyPercent != null) {
    parts.push(bucket("wk", u.weeklyPercent, u.weeklyResetsAt));
  }
  if (u.sonnetWeeklyPercent != null) {
    parts.push(bucket("sn", u.sonnetWeeklyPercent, u.sonnetWeeklyResetsAt));
  }
  if (u.opusWeeklyPercent != null) {
    parts.push(bucket("op", u.opusWeeklyPercent, u.opusWeeklyResetsAt));
  }
  let seg = parts.join(" ");
  if (stale) seg = `${C.dim}~${C.reset}${seg}`;
  return seg;
}

// Friendly message for the no-data states.
export function renderUsageError(error) {
  if (error === "no_credentials") return ""; // API-key users: stay quiet
  if (error === "auth") return `${C.dim}usage:auth${C.reset}`;
  if (error === "rate_limited") return `${C.dim}usage:429${C.reset}`;
  return `${C.dim}usage:--${C.reset}`;
}

export function renderContext(pct) {
  if (pct == null) return "";
  const p = Math.min(100, Math.max(0, Math.round(pct)));
  return `${C.dim}ctx:${C.reset}${loadColor(p)}${p}%${C.reset}`;
}

export function renderModel(name) {
  if (!name) return "";
  return `${C.cyan}${name}${C.reset}`;
}

export function renderCost(usd) {
  if (usd == null || !isFinite(usd)) return "";
  return `${C.dim}$${usd.toFixed(2)}${C.reset}`;
}
