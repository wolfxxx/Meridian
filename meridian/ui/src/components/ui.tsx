import { ReactNode, useCallback, useEffect, useRef, useState } from "react";
import { Kpi as KpiT } from "../api";
import { kpiValue } from "../format";

// ---- icons (24px grid, stroke) -----------------------------------------------------------------
const PATHS: Record<string, string> = {
  home: "M3 10.5 12 3l9 7.5V21h-6v-6H9v6H3z",
  overview: "M4 4h7v7H4zM13 4h7v4h-7zM13 10h7v10h-7zM4 13h7v7H4z",
  formula: "M9 4c-2 0-3 1-3 3v10c0 2-1 3-3 3M5 10h6M14 9l6 6M20 9l-6 6",
  table: "M3 5h18v14H3zM3 10h18M3 15h18M9 5v14",
  people: "M8 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM16 11a3 3 0 1 0 0-6M2 20c0-3 3-5 6-5s6 2 6 5M14 15c3 0 6 2 6 5",
  play: "M7 4v16l13-8z",
  explain: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM21 21l-5-5M11 8v4M11 14.5v.5",
  check: "M5 12.5 10 17 19 7",
  shield: "M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6zM8.5 12l2.5 2.5 4.5-5",
  search: "M10.5 4a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13zM20 20l-4.8-4.8",
  sun: "M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10zM12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4",
  moon: "M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z",
  arrow: "M5 12h14M13 6l6 6-6 6",
  back: "M19 12H5M11 18l-6-6 6-6",
  reset: "M4 12a8 8 0 1 0 2.3-5.7M4 4v5h5",
  edit: "M4 20h4L19 9l-4-4L4 16zM14 6l4 4",
  alert: "M12 3 2 20h20zM12 10v4M12 17v.5",
  lock: "M6 11h12v9H6zM8 11V8a4 4 0 0 1 8 0v3",
  term: "M4 18c4 0 5-12 8-12s4 12 8 12M4 18h16",
  savings: "M4 17l5-5 4 3 7-8M15 7h5v5",
  family: "M7 9a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zM17 9a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zM12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM2 20c0-3 2-6 5-6 1.2 0 2 .3 3 1M22 20c0-3-2-6-5-6-1.2 0-2 .3-3 1M8.5 20c0-2 1.5-3.5 3.5-3.5s3.5 1.5 3.5 3.5",
  history: "M3 12a9 9 0 1 0 3-6.7M3 4v5h5M12 7v5l3 3",
  info: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 11v6M12 7.5v.5",
  sliders: "M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1M15 4v4M9 10v4M17 16v4",
  upload: "M12 15V4M7 9l5-5 5 5M4 15v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4",
  download: "M12 4v11M7 10l5 5 5-5M4 15v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4",
  help: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6v.6M12 17v.5",
  close: "M6 6l12 12M18 6 6 18",
  compare: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  file: "M6 3h8l4 4v14H6zM14 3v4h4M9 12h6M9 16h6",
};

export function Icon({ name, size = 18 }: { name: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ flex: "none" }}>
      <path d={PATHS[name] || PATHS.info} />
    </svg>
  );
}

export function Logo({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <circle cx="16" cy="16" r="12.5" fill="none" stroke="var(--accent)" strokeWidth="2.6" />
      <path d="M16 3.5c5.2 4 5.2 21 0 25" fill="none" stroke="var(--accent)" strokeWidth="2.6" />
      <path d="M4 16h24" stroke="var(--accent)" strokeWidth="1.4" opacity="0.45" />
    </svg>
  );
}

export function Badge({ tone = "", children }: { tone?: string; children: ReactNode }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function Spinner() { return <span className="spinner" role="status" aria-label="Working" />; }

export function Progress({ value }: { value: number }) {
  return <div className="progress" role="progressbar" aria-valuenow={Math.round(value * 100)} aria-valuemin={0} aria-valuemax={100}>
    <div style={{ width: `${Math.max(2, Math.min(100, value * 100))}%` }} /></div>;
}

export function KpiTile({ k, baseline }: { k: KpiT; baseline?: KpiT }) {
  let delta: ReactNode = null;
  if (baseline && baseline.value !== 0 && k.format !== "percent") {
    const d = k.value - baseline.value;
    const rel = d / Math.abs(baseline.value);
    delta = <span className="k-delta" style={{ color: d === 0 ? "var(--ink-3)" : "var(--ink-2)" }}>
      {d >= 0 ? "▲" : "▼"} {(Math.abs(rel) * 100).toFixed(1)}% vs baseline</span>;
  }
  return (
    <div className="card kpi">
      <span className="k-label">{k.label}</span>
      <span className="k-value">{kpiValue(k)}</span>
      {k.note && <span className="k-note">{k.note}</span>}
      {delta}
    </div>
  );
}

export function Segmented<T extends string | number>({ value, options, onChange, label, compact = false }:
  { value: T; options: [T, string][]; onChange: (v: T) => void; label: string; compact?: boolean }) {
  return (
    <div className={"seg" + (compact ? " compact" : "")} role="group" aria-label={label}>
      {options.map(([v, l]) => (
        <button key={String(v)} type="button" aria-pressed={v === value} onClick={() => onChange(v)}>{l}</button>
      ))}
    </div>
  );
}

export function Empty({ icon = "info", title, children }: { icon?: string; title: string; children?: ReactNode }) {
  return <div className="empty"><span className="faint"><Icon name={icon} size={28} /></span><h3>{title}</h3>{children}</div>;
}

/** A dialog over the page. Escape or the close button calls onClose. */
export function Modal({ title, children, onClose, width = 760, footer }:
  { title: string; children: ReactNode; onClose: () => void; width?: number; footer?: ReactNode }) {
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    box.current?.focus();
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", key);
    return () => { window.removeEventListener("keydown", key); prev?.focus?.(); };
  }, [onClose]);
  return (
    <div className="modal-back" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal card" role="dialog" aria-modal="true" aria-label={title} tabIndex={-1} ref={box} style={{ width }}>
        <div className="card-head"><h2>{title}</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Close"><Icon name="close" /></button></div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-foot">{footer}</div>}
      </div>
    </div>
  );
}

export function ErrorNote({ error }: { error: string }) {
  return <div className="callout"><Icon name="alert" /><div><strong>Something went wrong.</strong> {error}</div></div>;
}

/** Load data once per key; returns [data, error, reload]. */
export function useAsync<T>(fn: () => Promise<T>, deps: any[]): [T | null, string | null, () => void] {
  const [data, setData] = useState<T | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [n, setN] = useState(0);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    setErr(null);
    fn().then((d) => alive.current && setData(d)).catch((e) => alive.current && setErr(String(e.message || e)));
    return () => { alive.current = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, n]);
  const reload = useCallback(() => setN((x) => x + 1), []);
  return [data, err, reload];
}

export function useInterval(fn: () => void, ms: number | null) {
  const ref = useRef(fn);
  ref.current = fn;
  useEffect(() => {
    if (ms === null) return;
    const id = setInterval(() => ref.current(), ms);
    return () => clearInterval(id);
  }, [ms]);
}
