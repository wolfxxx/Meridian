// Number formatting used throughout the interface.

// Thousands separated by spaces, decimal point (the convention most actuaries use).
const groups = (x: number, dp: number) =>
  x.toLocaleString("en-US", { minimumFractionDigits: dp, maximumFractionDigits: dp }).replace(/,/g, " ");

/** Full-precision readable number: grouped thousands for large values, significant digits otherwise. */
export function num(v: number | null | undefined, dp?: number): string {
  if (v === null || v === undefined || !isFinite(v)) return "–";
  if (dp !== undefined) return groups(v, dp);
  const a = Math.abs(v);
  if (a === 0) return "0";
  if (a >= 1e5) return groups(v, 0);
  if (a >= 100) return groups(v, 2);
  if (a >= 1) return String(+v.toPrecision(7));
  if (a >= 1e-3) return String(+v.toPrecision(5));
  return v.toExponential(3);
}

/** Compact number for axes and tiles: 1.2m, 45.6bn. */
export function compact(v: number, unit = ""): string {
  if (v === null || v === undefined || !isFinite(v)) return "–";
  const a = Math.abs(v), s = v < 0 ? "−" : "";
  const pre = unit ? unit + " " : "";
  if (a >= 1e9) return `${s}${pre}${(a / 1e9).toFixed(a >= 1e10 ? 1 : 2)}bn`;
  if (a >= 1e6) return `${s}${pre}${(a / 1e6).toFixed(a >= 1e7 ? 1 : 2)}m`;
  if (a >= 1e3) return `${s}${pre}${(a / 1e3).toFixed(a >= 1e4 ? 0 : 1)}k`;
  if (a >= 1) return `${s}${pre}${+a.toPrecision(3)}`;
  if (a === 0) return `${pre}0`;
  return `${s}${pre}${+a.toPrecision(2)}`;
}

export function money(v: number, unit = ""): string {
  if (v === null || v === undefined || !isFinite(v)) return "–";
  const s = v < 0 ? "−" : "";
  return `${s}${unit ? unit + " " : ""}${groups(Math.abs(v), 0)}`;
}

export function pct(v: number, dp = 1): string {
  if (!isFinite(v)) return "–";
  return `${(v * 100).toFixed(dp)}%`;
}

export function seconds(s: number | null | undefined): string {
  if (s === null || s === undefined) return "–";
  if (s < 1) return `${(s * 1000).toFixed(0)} ms`;
  if (s < 60) return `${s.toFixed(1)} s`;
  return `${Math.floor(s / 60)} min ${Math.round(s % 60)} s`;
}

export function ago(ts: number | null): string {
  if (!ts) return "";
  const d = Date.now() / 1000 - ts;
  if (d < 60) return "just now";
  if (d < 3600) return `${Math.round(d / 60)} min ago`;
  const date = new Date(ts * 1000);
  const time = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  if (date.toDateString() === new Date().toDateString()) return time;
  return `${date.toLocaleDateString("en-ZA", { day: "numeric", month: "short" })} ${time}`;
}

export function kpiValue(k: { value: number; unit: string; format: string }): string {
  return k.format === "percent" ? pct(k.value) : money(k.value, k.unit);
}

export function sentence(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
