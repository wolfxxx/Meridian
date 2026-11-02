import { useEffect, useMemo, useState } from "react";
import { api, Kpi, Lever, ModelDetail, RunBrief, RunFull } from "../api";
import { LineChart, PALETTE } from "../components/charts";
import { Badge, ErrorNote, Icon, Progress, Segmented, Spinner, useInterval } from "../components/ui";
import { ago, compact, kpiValue, pct, sentence } from "../format";
import { go } from "../router";

const MINUS = "−";

function leverText(l: Lever, v: number): string {
  if (!v) return "0";
  const sign = v > 0 ? "+" : MINUS;
  return l.unit === "%" ? `${sign}${Math.abs(v)}%` : `${sign}${Math.abs(v)} pp`;
}

function presetText(model: ModelDetail): string[] {
  const seen = new Map<string, number>();
  model.sensitivities.forEach((s) => Object.entries(s.levers).forEach(([k, v]) => seen.set(k, Math.abs(v))));
  return [...seen].map(([k, v]) => {
    const l = model.levers.find((x) => x.key === k)!;
    return `${l.label} ±${v}${l.unit === "%" ? "%" : " pp"}`;
  });
}

function delta(k: Kpi, base: Kpi, unit: string): string {
  const d = k.value - base.value;
  if (k.format === "percent") return `${d >= 0 ? "+" : MINUS}${Math.abs(d * 100).toFixed(2)} pp`;
  return `${d >= 0 ? "+" : MINUS}${compact(Math.abs(d), unit)}`;
}

export function WhatIf({ model }: { model: ModelDetail }) {
  const zero = () => Object.fromEntries(model.levers.map((l) => [l.key, 0]));
  const [vals, setVals] = useState<Record<string, number>>(zero);
  const [runs, setRuns] = useState<RunBrief[]>([]);
  const [full, setFull] = useState<Record<string, RunFull>>({});
  const [picked, setPicked] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const unit = model.currency;
  const defaults = useMemo(() => Object.fromEntries(model.run_options.map((o) => [o.key, o.default])), [model]);

  const load = () => api.runs(model.id).then(setRuns).catch((e) => setError(String(e.message || e)));
  useEffect(() => { load(); }, [model.id]); // eslint-disable-line react-hooks/exhaustive-deps
  const active = runs.some((r) => r.status === "queued" || r.status === "running");
  useInterval(load, active ? 600 : null);
  useEffect(() => {
    runs.filter((r) => r.status === "done" && !full[r.id]).forEach((r) =>
      api.run(r.id).then((f) => setFull((m) => ({ ...m, [r.id]: f }))));
  }, [runs]); // eslint-disable-line react-hooks/exhaustive-deps

  const moved = Object.entries(vals).filter(([, v]) => v !== 0);

  async function runWhatIf() {
    setError(null); setStarting(true);
    try {
      const dataName = model.data_source?.name ?? null;
      const base = runs.find((r) => r.status !== "failed" && !Object.keys(r.levers || {}).length && !r.modified_tables.length && r.data === dataName);
      const ids: string[] = [];
      if (!base) ids.push((await api.startRun(model.id, { ...defaults })).id);
      const r = await api.startRun(model.id, { ...defaults, levers: Object.fromEntries(moved) });
      ids.push(r.id);
      setPicked((p) => [...new Set([...(base ? [base.id] : []), ...ids, ...(p || [])])].slice(0, 4));
      load();
    } catch (e: any) { setError(String(e.message || e)); } finally { setStarting(false); }
  }

  async function runStandard() {
    setError(null); setStarting(true);
    try {
      const group = Math.random().toString(36).slice(2, 10);
      await api.startRun(model.id, { ...defaults }, "Base run", group);
      for (const s of model.sensitivities) await api.startRun(model.id, { ...defaults, levers: s.levers }, undefined, group);
      load();
    } catch (e: any) { setError(String(e.message || e)); } finally { setStarting(false); }
  }

  // the latest set of standard sensitivities
  const lastGroup = runs.find((r) => r.group)?.group;
  const groupRuns = runs.filter((r) => r.group && r.group === lastGroup);
  const groupDone = groupRuns.filter((r) => r.status === "done").length;

  return (
    <div className="split" style={{ gridTemplateColumns: "340px minmax(0, 1fr)" }}>
      <div className="grid" style={{ gap: 16 }}>
        <div className="card" data-tour="levers">
          <div className="card-head"><h3>Build a what-if</h3><Icon name="sliders" /></div>
          <div className="card-body" style={{ paddingTop: 4 }}>
            {model.levers.map((l) => {
              const v = vals[l.key];
              return (
                <div key={l.key} className="lever">
                  <div className="spread" style={{ flexWrap: "nowrap" }}>
                    <label htmlFor={`lv-${l.key}`} className="stack" style={{ gap: 0 }}>
                      <strong style={{ fontSize: 13.5 }}>{l.label}</strong>
                      <span className="faint" style={{ fontSize: 12 }}>{l.help}</span>
                    </label>
                    <span className={"lever-val" + (v ? " moved" : "")}>{leverText(l, v)}</span>
                  </div>
                  <input id={`lv-${l.key}`} type="range" min={l.min} max={l.max} step={l.step} value={v}
                    onChange={(e) => setVals({ ...vals, [l.key]: Number(e.target.value) })}
                    aria-valuetext={leverText(l, v)} />
                  <div className="ticks"><span>{leverText(l, l.min)}</span>
                    {v !== 0 && <button className="btn small ghost" style={{ padding: "0 6px", fontSize: 11 }} onClick={() => setVals({ ...vals, [l.key]: 0 })}>reset</button>}
                    <span>{leverText(l, l.max)}</span></div>
                </div>
              );
            })}
            <p className="faint" style={{ fontSize: 12, margin: "6px 0 12px" }}>
              {model.id === "term" ? "Premiums stay as charged; only the projection assumptions change. " : ""}
              Applied on top of {model.modified_tables.length ? `your edited ${model.modified_tables.join(", ")}` : "the model’s assumptions"}.
            </p>
            <div className="row">
              <button className="btn primary" disabled={!moved.length || starting} onClick={runWhatIf}>
                <Icon name="play" size={15} /> Run what-if
              </button>
              {moved.length > 0 && <button className="btn ghost" onClick={() => setVals(zero())}>Reset all</button>}
            </div>
          </div>
        </div>

        <div className="card card-body stack" style={{ gap: 10 }}>
          <h3>Standard sensitivities</h3>
          <p className="muted" style={{ fontSize: 13 }}>One click runs the base and each assumption up and down, then shows which matters most.</p>
          <div className="chips">{presetText(model).map((t) => <span key={t} className="chip static">{t}</span>)}</div>
          <button className="btn" disabled={starting || active} onClick={runStandard}>
            <Icon name="compare" size={15} /> Run {model.sensitivities.length + 1} runs
          </button>
        </div>
      </div>

      <div className="grid" style={{ gap: 16 }}>
        {error && <ErrorNote error={error} />}
        {lastGroup && <TornadoCard model={model} runs={groupRuns} full={full} done={groupDone} unit={unit} />}
        <CompareCard model={model} runs={runs} full={full} picked={picked} setPicked={setPicked} unit={unit} />
      </div>
    </div>
  );
}

function TornadoCard({ model, runs, full, done, unit }:
  { model: ModelDetail; runs: RunBrief[]; full: Record<string, RunFull>; done: number; unit: string }) {
  const [kpiIdx, setKpiIdx] = useState(0);
  const base = runs.find((r) => !Object.keys(r.levers || {}).length);
  const baseRes = base && full[base.id]?.result;
  if (done < runs.length || !baseRes) {
    return (
      <div className="card card-pad stack" style={{ gap: 12 }}>
        <div className="spread"><h2>Running standard sensitivities…</h2><Spinner /></div>
        <Progress value={done / Math.max(runs.length, 1)} />
        <span className="muted">{done} of {runs.length} runs finished</span>
      </div>
    );
  }
  const k0 = baseRes.kpis[kpiIdx];
  const keys = [...new Set(model.sensitivities.flatMap((s) => Object.keys(s.levers)))];
  const rows = keys.map((key) => {
    const l = model.levers.find((x) => x.key === key)!;
    const find = (sign: number) => runs.find((r) => Math.sign((r.levers || {})[key] || 0) === sign);
    const up = find(1), down = find(-1);
    const val = (r?: RunBrief) => (r && full[r.id]?.result ? full[r.id].result!.kpis[kpiIdx].value - k0.value : null);
    return { l, up: val(up), down: val(down), upV: up?.levers[key], downV: down?.levers[key] };
  }).sort((a, b) => Math.max(Math.abs(b.up || 0), Math.abs(b.down || 0)) - Math.max(Math.abs(a.up || 0), Math.abs(a.down || 0)));
  const max = Math.max(...rows.flatMap((r) => [Math.abs(r.up || 0), Math.abs(r.down || 0)]), 1e-12);
  const fmt = (d: number) => k0.format === "percent"
    ? `${d >= 0 ? "+" : MINUS}${Math.abs(d * 100).toFixed(2)} pp`
    : `${d >= 0 ? "+" : MINUS}${compact(Math.abs(d), unit)}`;
  const bar = (d: number | null, cls: string) => {
    if (d === null) return null;
    const w = (Math.abs(d) / max) * 38;
    const left = d >= 0 ? 50 : 50 - w;
    return <>
      <div className={`tor-bar ${cls}`} style={{ left: `${left}%`, width: `${Math.max(w, 0.3)}%` }} />
      <span className="tor-num" style={{ [cls === "up" ? "top" : "bottom"]: 2, ...(d >= 0 ? { left: `calc(${50 + w}% + 6px)` } : { right: `calc(${50 + w}% + 6px)` }) }}>{fmt(d)}</span>
    </>;
  };
  return (
    <div className="card card-body stack" style={{ gap: 14 }}>
      <div className="spread">
        <div className="stack" style={{ gap: 2 }}>
          <h2>What moves the result most</h2>
          <span className="faint">Change in {k0.label.toLowerCase()} from the base of <strong className="mono">{kpiValue(k0)}</strong> · {base!.data ? `on ${base!.data} · ` : ""}{ago(base!.finished)}</span>
        </div>
        <Segmented label="Measure" value={kpiIdx} onChange={setKpiIdx} options={baseRes.kpis.map((k, i) => [i, k.label] as [number, string])} />
      </div>
      <div className="tornado" role="img" aria-label={`Sensitivity of ${k0.label}`}>
        {rows.map((r) => (
          <div key={r.l.key} className="tor-row">
            <div className="tor-label">{r.l.label}<small>{r.upV !== undefined ? leverText(r.l, r.upV) : ""} / {r.downV !== undefined ? leverText(r.l, r.downV) : ""}</small></div>
            <div className="tor-track">{bar(r.up, "up")}{bar(r.down, "down")}</div>
          </div>
        ))}
      </div>
      <div className="row faint" style={{ fontSize: 12 }}>
        <span><i className="swatch" style={{ background: "var(--c1)" }} />Assumption up</span>
        <span><i className="swatch" style={{ background: "var(--c4)" }} />Assumption down</span>
        <span>Bars to the right increase {k0.label.toLowerCase()}.</span>
      </div>
    </div>
  );
}

function CompareCard({ model, runs, full, picked, setPicked, unit }:
  { model: ModelDetail; runs: RunBrief[]; full: Record<string, RunFull>; picked: string[] | null;
    setPicked: (p: string[]) => void; unit: string }) {
  const done = runs.filter((r) => r.status === "done");
  const auto = useMemo(() => {
    // The latest plain base run is the reference; compare it only with runs on the same policy data.
    const base = done.find((r) => !Object.keys(r.levers || {}).length && !r.modified_tables.length);
    const same = done.filter((r) => r !== base && (!base || r.data === base.data));
    const others = same.slice(0, base ? 3 : 4);
    return [...(base ? [base.id] : []), ...others.map((r) => r.id)];
  }, [done.map((r) => r.id).join()]); // eslint-disable-line react-hooks/exhaustive-deps
  const sel = (picked || auto).filter((id) => done.some((r) => r.id === id));
  const cols = sel.map((id) => full[id]).filter((r): r is RunFull => !!r?.result);
  const moneyKeys = cols[0] ? Object.keys(cols[0].result!.series).filter((k) => !/pols|policies|deaths/.test(k)) : [];
  const [seriesKey, setSeriesKey] = useState<string>("");
  const sk = moneyKeys.includes(seriesKey) ? seriesKey : (moneyKeys.find((k) => /net/.test(k)) || moneyKeys[0]);

  function toggle(id: string) {
    const cur = picked || auto;
    setPicked(cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id].slice(-4));
  }

  if (!done.length) {
    return (
      <div className="card"><div className="empty">
        <Icon name="compare" size={28} /><h3>Compare runs side by side</h3>
        <p className="muted" style={{ maxWidth: 460 }}>Move a slider and run a what-if, or run the standard sensitivities. Results appear here next to the base run, with the differences worked out.</p>
      </div></div>
    );
  }
  const rowsOf = (r: RunFull) => [...r.result!.kpis.map((k) => ({ ...k })),
    ...r.result!.pv_table.map((p) => ({ label: "PV · " + p.label, value: p.value, unit, note: "", format: "number" as const }))];
  const refRows = cols[0] ? rowsOf(cols[0]) : [];
  const mixed = new Set(cols.map((c) => c.data ?? "")).size > 1;

  return (
    <div className="card">
      <div className="card-head"><h3>Compare runs</h3><span className="faint">pick up to four · the first is the reference</span></div>
      <div className="split" style={{ gridTemplateColumns: "260px minmax(0, 1fr)", gap: 0, alignItems: "stretch" }}>
        <div style={{ borderRight: "1px solid var(--line)", maxHeight: 520, overflowY: "auto" }}>
          {done.map((r) => {
            const on = sel.includes(r.id);
            return (
              <label key={r.id} className="pick">
                <input type="checkbox" checked={on} onChange={() => toggle(r.id)} />
                <span className="stack" style={{ gap: 0, minWidth: 0 }}>
                  <span style={{ fontWeight: on ? 600 : 400, overflow: "hidden", textOverflow: "ellipsis" }}>{r.label}</span>
                  <span className="faint" style={{ fontSize: 11.5 }}>{ago(r.started)}{r.data ? ` · ${r.data}` : ""}</span>
                </span>
                {sel[0] === r.id && <Badge tone="accent">ref</Badge>}
              </label>
            );
          })}
        </div>
        <div className="stack" style={{ gap: 0, minWidth: 0 }}>
          {cols.length === 0 ? <div className="empty"><Spinner /></div> : (
            <>
              {mixed && <div className="callout" style={{ margin: 12 }}><Icon name="alert" />
                <span>These runs use different policy data ({[...new Set(cols.map((c) => c.data || "the model’s own data"))].join(" and ")}), so the differences include the change of data, not only the assumptions.</span></div>}
              <div className="tbl-wrap">
                <table className="tbl cmp">
                  <thead><tr><th>Measure</th>{cols.map((c, i) => <th key={c.id} className="run" style={{ color: PALETTE[i] }}>{c.label}</th>)}</tr></thead>
                  <tbody>
                    {refRows.map((row, ri) => (
                      <tr key={row.label}><td style={{ minWidth: 190 }}>{row.label}</td>
                        {cols.map((c, i) => {
                          const k = rowsOf(c)[ri];
                          const d = k.value - row.value;
                          return <td key={c.id} className="r mono">{kpiValue(k)}
                            {i > 0 && <span className={"delta " + (d > 0 ? "up" : d < 0 ? "down" : "")}>
                              {d === 0 ? "no change" : delta(k, row, unit)}{d !== 0 && row.value !== 0 && k.format !== "percent" ? ` (${d > 0 ? "+" : MINUS}${pct(Math.abs(d / row.value))})` : ""}</span>}
                          </td>;
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {sk && (
                <div className="card-body stack" style={{ borderTop: "1px solid var(--line)" }}>
                  <div className="spread">
                    <h3>{sentence(cols[0].result!.series[sk].label)} by month</h3>
                    <select className="input" value={sk} onChange={(e) => setSeriesKey(e.target.value)} aria-label="Series">
                      {moneyKeys.map((k) => <option key={k} value={k}>{sentence(cols[0].result!.series[k].label)}</option>)}
                    </select>
                  </div>
                  <LineChart unit={unit ? unit + " " : ""} height={240}
                    series={cols.map((c, i) => ({ key: c.id, label: c.label, values: c.result!.series[sk]?.values || [], color: PALETTE[i], dashed: i === 0 }))} />
                  <span className="faint" style={{ fontSize: 12 }}>Dashed: the reference run. <button className="btn small ghost" onClick={() => go(model.id, "run", { run: cols[cols.length - 1].id })}>Open full results <Icon name="arrow" size={13} /></button></span>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
