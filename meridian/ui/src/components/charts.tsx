import { useMemo, useRef, useState } from "react";
import { compact, num } from "../format";

export const PALETTE = ["var(--c1)", "var(--c2)", "var(--c3)", "var(--c4)", "var(--c5)", "var(--c6)", "var(--c7)"];

function ticks(lo: number, hi: number, n: number): number[] {
  const span = hi - lo || Math.abs(hi) || 1;
  let step = Math.pow(10, Math.floor(Math.log10(span / n)));
  const err = span / n / step;
  step *= err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1;
  const out: number[] = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) out.push(+v.toFixed(12));
  return out;
}

export interface LineSeries { key: string; label: string; values: (number | null)[]; color?: string; dashed?: boolean }

/** Multi-series line chart over months with a hover readout. */
export function LineChart({ series, height = 260, unit = "", xUnit = "month", marker, area = false, xLabels, xTitle, logY = false }:
  { series: LineSeries[]; height?: number; unit?: string; xUnit?: string; marker?: number; area?: boolean;
    xLabels?: string[]; xTitle?: string; logY?: boolean }) {
  const W = 760, H = height, L = 64, R = 14, T = 12, B = 30;
  const [hover, setHover] = useState<number | null>(null);
  const box = useRef<HTMLDivElement>(null);
  const n = Math.max(...series.map((s) => s.values.length), 1);
  const tf = (v: number) => (logY ? Math.log10(Math.max(v, 1e-12)) : v);
  const { lo, hi } = useMemo(() => {
    let lo = Infinity, hi = -Infinity;
    series.forEach((s) => s.values.forEach((v) => { if (v !== null && isFinite(v) && (!logY || v > 0)) { lo = Math.min(lo, tf(v)); hi = Math.max(hi, tf(v)); } }));
    if (!isFinite(lo)) { lo = 0; hi = 1; }
    if (!logY) lo = Math.min(lo, 0);
    if (hi === lo) hi = lo + 1;
    return { lo, hi: hi + (hi - lo) * 0.04 };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [series, logY]);
  const x = (i: number) => L + ((W - L - R) * i) / Math.max(n - 1, 1);
  const y = (v: number) => T + (H - T - B) * (1 - (tf(v) - lo) / (hi - lo));
  const yt = logY
    ? Array.from({ length: Math.floor(hi) - Math.ceil(lo) + 1 }, (_, k) => Math.pow(10, Math.ceil(lo) + k))
    : ticks(lo, hi, 5);
  const yearStep = n > 400 ? 10 : 5;
  const xt: number[] = [];
  if (xUnit === "month" && !xLabels) for (let yr = 0; yr * 12 < n; yr += yearStep) xt.push(yr * 12);
  else for (let i = 0; i < n; i += Math.max(1, Math.round(n / 8))) xt.push(i);
  const xl = (i: number) => (xLabels ? xLabels[i] : xUnit === "month" ? (i === 0 ? "0" : `${i / 12}y`) : String(i));

  function onMove(e: React.MouseEvent) {
    const r = box.current!.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    const i = Math.round(((px - L) / (W - L - R)) * (n - 1));
    setHover(i >= 0 && i < n ? i : null);
  }
  return (
    <div className="chart" ref={box} onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={series.map((s) => s.label).join(", ")}>
        {yt.map((v) => (
          <g key={v}>
            <line className="gridline" x1={L} x2={W - R} y1={y(v)} y2={y(v)} />
            <text x={L - 8} y={y(v) + 4} textAnchor="end">{compact(v)}</text>
          </g>
        ))}
        {xt.map((i) => (
          <text key={i} x={x(i)} y={H - 10} textAnchor="middle">{xl(i)}</text>
        ))}
        {!logY && lo < 0 && <line className="axis" x1={L} x2={W - R} y1={y(0)} y2={y(0)} />}
        {xTitle && <text x={W - R} y={H - 10} textAnchor="end" style={{ fill: "var(--ink-3)" }}>{xTitle}</text>}
        {series.map((s, si) => {
          const color = s.color || PALETTE[si % PALETTE.length];
          let d = "";
          s.values.forEach((v, i) => { if (v !== null && isFinite(v)) d += `${d ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`; });
          return (
            <g key={s.key}>
              {area && si === 0 && d && <path d={`${d}L${x(s.values.length - 1)} ${y(Math.max(lo, 0))}L${x(0)} ${y(Math.max(lo, 0))}Z`} fill={color} opacity={0.08} />}
              <path d={d} fill="none" stroke={color} strokeWidth={1.8} strokeDasharray={s.dashed ? "5 4" : undefined} />
            </g>
          );
        })}
        {marker !== undefined && marker < n && <line x1={x(marker)} x2={x(marker)} y1={T} y2={H - B} stroke="var(--ref)" strokeDasharray="3 3" />}
        {hover !== null && (
          <g>
            <line x1={x(hover)} x2={x(hover)} y1={T} y2={H - B} stroke="var(--line-strong)" />
            {series.map((s, si) => {
              const v = s.values[hover];
              return v !== null && v !== undefined && isFinite(v)
                ? <circle key={s.key} cx={x(hover)} cy={y(v)} r={3.5} fill={s.color || PALETTE[si % PALETTE.length]} /> : null;
            })}
          </g>
        )}
      </svg>
      {hover !== null && (
        <div className="tooltip" style={{ left: `calc(${(x(hover) / W) * 100}% + ${x(hover) / W > 0.6 ? -190 : 12}px)`, top: 8 }}>
          <div className="faint mono" style={{ marginBottom: 4 }}>
            {xLabels ? `${xTitle || ""} ${xLabels[hover]}` : xUnit === "month" ? `month ${hover} · year ${Math.floor(hover / 12) + 1}` : `${xUnit} ${hover + 1}`}
          </div>
          {series.map((s, si) => (
            <div className="t-row" key={s.key}>
              <span style={{ color: s.color || PALETTE[si % PALETTE.length] }}>{s.label}</span>
              <span className="mono">{unit}{num(s.values[hover] ?? NaN)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** Horizontal bars, optionally signed. */
export function BarList({ items, unit = "", height = 26 }:
  { items: { label: string; value: number; color?: string; note?: string }[]; unit?: string; height?: number }) {
  const W = 560, L = 190, R = 110;
  const max = Math.max(...items.map((i) => Math.abs(i.value)), 1e-12);
  const hasNeg = items.some((i) => i.value < 0);
  const zero = hasNeg ? L + (W - L - R) / 2 : L;
  const scale = (hasNeg ? (W - L - R) / 2 : W - L - R) / max;
  const H = items.length * height + 6;
  return (
    <div className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Bar chart">
        {hasNeg && <line className="axis" x1={zero} x2={zero} y1={0} y2={H} />}
        {items.map((it, i) => {
          const w = Math.abs(it.value) * scale, y0 = i * height + 4;
          const x0 = it.value >= 0 ? zero : zero - w;
          return (
            <g key={it.label}>
              <text x={L - 10} y={y0 + height / 2 + 1} textAnchor="end" style={{ fill: "var(--ink-2)", fontFamily: "var(--font)", fontSize: 12 }}>{it.label}</text>
              <rect x={x0} y={y0 + 4} width={Math.max(w, 1.5)} height={height - 10} rx={3} fill={it.color || "var(--c1)"} />
              <text x={it.value >= 0 ? x0 + w + 6 : zero + 6} y={y0 + height / 2 + 1}>{compact(it.value, unit)}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export function Histogram({ hist, height = 56 }: { hist: number[]; height?: number }) {
  const W = 200, max = Math.max(...hist, 1), bw = W / hist.length;
  return (
    <svg viewBox={`0 0 ${W} ${height}`} style={{ width: "100%", height }} aria-hidden="true">
      {hist.map((h, i) => <rect key={i} x={i * bw + 0.5} y={height - (h / max) * (height - 2)} width={bw - 1} height={(h / max) * (height - 2)} rx={1} fill="var(--c1)" opacity={0.75} />)}
    </svg>
  );
}

export function Sparkline({ values, marker, height = 80 }: { values: (number | null)[]; marker?: number; height?: number }) {
  const W = 600, P = 6, n = values.length;
  const fin = values.filter((v): v is number => v !== null && isFinite(v));
  let lo = Math.min(...fin), hi = Math.max(...fin);
  if (!fin.length) { lo = 0; hi = 1; }
  if (hi === lo) hi = lo + 1;
  const x = (i: number) => P + ((W - 2 * P) * i) / Math.max(n - 1, 1);
  const y = (v: number) => P + (height - 2 * P) * (1 - (v - lo) / (hi - lo));
  let d = "";
  values.forEach((v, i) => { if (v !== null && isFinite(v)) d += `${d ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`; });
  const mv = marker !== undefined ? values[marker] : null;
  return (
    <svg viewBox={`0 0 ${W} ${height}`} style={{ width: "100%", height }} aria-hidden="true">
      {d && <path d={`${d}L${x(n - 1)} ${height - P}L${x(0)} ${height - P}Z`} fill="var(--accent-soft)" />}
      <path d={d} fill="none" stroke="var(--accent)" strokeWidth={1.6} />
      {mv !== null && mv !== undefined && isFinite(mv) && <circle cx={x(marker!)} cy={y(mv)} r={4.5} fill="var(--ref)" stroke="var(--surface)" strokeWidth={2} />}
    </svg>
  );
}

/** Scenario outcomes sorted worst to best, with the CTE70 tail highlighted. */
export function ScenarioBars({ values, unit = "" }: { values: number[]; unit?: string }) {
  const v = [...values].sort((a, b) => a - b), n = v.length;
  const W = 760, H = 220, L = 64, R = 10, T = 10, B = 26;
  const lo = Math.min(v[0], 0) * 1.02 || v[0] * 0.98, hi = v[n - 1] * 1.02;
  const base = Math.min(...v) > 0 ? v[0] * 0.97 : lo;
  const y = (x: number) => T + (H - T - B) * (1 - (x - base) / (hi - base));
  const bw = (W - L - R) / n, k = Math.max(1, Math.ceil(0.3 * n));
  const cte = v.slice(0, k).reduce((a, b) => a + b, 0) / k;
  return (
    <div className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Scenario results, worst to best">
        {ticks(base, hi, 4).map((t) => (
          <g key={t}><line className="gridline" x1={L} x2={W - R} y1={y(t)} y2={y(t)} /><text x={L - 8} y={y(t) + 4} textAnchor="end">{compact(t)}</text></g>
        ))}
        {v.map((val, i) => (
          <rect key={i} x={L + i * bw + (bw > 3 ? 0.5 : 0)} y={y(val)} width={Math.max(bw - (bw > 3 ? 1 : 0), 0.6)} height={Math.max(H - B - y(val), 0)}
            fill={i < k ? "var(--ref)" : "var(--c1)"} opacity={0.85} />
        ))}
        <line x1={L} x2={W - R} y1={y(cte)} y2={y(cte)} stroke="var(--ink)" strokeDasharray="4 3" />
        <text x={W - R} y={y(cte) - 6} textAnchor="end" style={{ fill: "var(--ink)" }}>CTE70 {compact(cte, unit)}</text>
        <text x={L} y={H - 8}>{n} scenarios, worst to best</text>
      </svg>
    </div>
  );
}
