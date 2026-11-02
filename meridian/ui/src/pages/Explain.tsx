import { useEffect, useMemo, useState } from "react";
import { api, DataPage, ExplainData, ModelDetail } from "../api";
import { Sparkline } from "../components/charts";
import { Formula } from "../components/Formula";
import { Badge, ErrorNote, Icon, Spinner } from "../components/ui";
import { num } from "../format";
import { go } from "../router";
import { kindOf } from "./Variables";

export function Explain({ model, params }: { model: ModelDetail; params: Record<string, string> }) {
  const policy = Number(params.p ?? 0);
  const vars = model.variables_spec;
  const byName = useMemo(() => Object.fromEntries(vars.map((v) => [v.name, v])), [vars]);
  const defaultVar = { term: "claims", savings: "av_pp_bef_inv", funeral: "claims" }[model.id] || vars[vars.length - 1].name;
  const varName = byName[params.v] ? params.v : defaultVar;
  const [data, setData] = useState<ExplainData | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [t, setT] = useState(Number(params.t ?? 12));
  const [trail, setTrail] = useState<[string, number][]>([]);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<DataPage | null>(null);

  useEffect(() => { setData(null); setErr(null); api.explain(model.id, policy).then(setData).catch((e) => setErr(String(e.message || e))); }, [model.id, policy]);
  useEffect(() => {
    if (!q.trim()) { setHits(null); return; }
    const id = setTimeout(() => api.data(model.id, 0, 8, q).then(setHits), 200);
    return () => clearTimeout(id);
  }, [q, model.id]);

  const set = (v: string, tt?: number, push = true) => {
    if (push && v !== varName) setTrail([...trail.slice(-7), [varName, t]]);
    if (tt !== undefined) setT(Math.max(0, tt));
    go(model.id, "explain", { p: policy, v, t: tt ?? t });
  };
  const steps = data?.steps ?? model.steps;
  const tt = Math.min(t, steps - 1);
  const valueAt = (name: string, at: number) => {
    if (!data) return null;
    if (at < 0) return byName[name]?.init ?? 0;
    const vs = data.values[name];
    return vs ? vs[Math.min(at, vs.length - 1)] : null;
  };
  const v = byName[varName];
  const [kind, tone] = kindOf(v);
  const lifeLabel = model.lives > 1 ? "life" : "policy";

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="card card-body stack" style={{ gap: 12 }}>
        <div className="spread">
          <div className="stack" style={{ gap: 2, minWidth: 0 }}>
            <span className="eyebrow">Explaining {lifeLabel}</span>
            <h2 style={{ overflowWrap: "anywhere" }}>{data ? data.label : "…"}</h2>
          </div>
          <div style={{ position: "relative", width: 330 }}>
            <div className="search"><Icon name="search" size={16} />
              <input placeholder={`Find another ${lifeLabel}…`} value={q} onChange={(e) => setQ(e.target.value)} aria-label={`Find another ${lifeLabel}`} /></div>
            {hits && (
              <div className="card" style={{ position: "absolute", top: 40, left: 0, right: 0, zIndex: 6, boxShadow: "var(--shadow-lg)" }}>
                {hits.rows.length === 0 && <div className="card-body faint">No match</div>}
                {hits.rows.map((r) => (
                  <button key={r._row} className="list-item" onClick={() => { setQ(""); setTrail([]); go(model.id, "explain", { p: r._row, v: varName, t }); }}>
                    <span className="mono" style={{ fontSize: 12.5 }}>{model.data_columns.slice(0, 4).map((c) => r[c.key]).join(" · ")}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
        {data?.family && (
          <div className="row" style={{ gap: 6 }}>
            <span className="faint" style={{ fontSize: 12.5 }}>Lives on this policy:</span>
            {data.family.map((f) => (
              <button key={f.row} className={`btn small ${f.row === policy ? "primary" : ""}`} onClick={() => go(model.id, "explain", { p: f.row, v: varName, t })}>{f.label}</button>
            ))}
          </div>
        )}
        <div className="row" style={{ gap: 14 }}>
          <span className="faint" style={{ fontSize: 12.5 }}>Month</span>
          <input type="range" min={0} max={steps - 1} value={tt} onChange={(e) => setT(Number(e.target.value))} style={{ width: 360, accentColor: "var(--accent)" }} aria-label="Month" />
          <input type="number" className="input mono" style={{ width: 90 }} min={0} max={steps - 1} value={tt} onChange={(e) => setT(Number(e.target.value) || 0)} aria-label="Month number" />
          <span className="faint mono" style={{ fontSize: 12.5 }}>year {Math.floor(tt / 12) + 1}, month {(tt % 12) + 1}</span>
        </div>
      </div>

      {err && <ErrorNote error={err} />}
      <div className="split" style={{ gridTemplateColumns: "260px minmax(0, 1fr)" }}>
        <div className="card listbox">
          {vars.map((x) => (
            <button key={x.name} className="list-item" aria-current={x.name === varName} onClick={() => { setTrail([]); set(x.name, undefined, false); }}>
              <span className="li-name">{x.name}</span>
              <span className="mono faint" style={{ fontSize: 11.5 }}>{data ? num(valueAt(x.name, tt) as number) : ""}</span>
            </button>
          ))}
        </div>
        {!data ? <div className="card card-pad row"><Spinner /><span className="muted">Projecting this {lifeLabel}…</span></div> : (
          <div className="card card-body stack" style={{ gap: 14 }}>
            {trail.length > 0 && (
              <div className="row" style={{ gap: 6, fontSize: 12.5 }}>
                <span className="faint">Came from</span>
                {trail.map(([n, at], i) => (
                  <button key={i} className="chip" onClick={() => { setTrail(trail.slice(0, i)); setT(at); go(model.id, "explain", { p: policy, v: n, t: at }); }}>{n} @{at}</button>
                ))}
              </div>
            )}
            <div className="row" style={{ alignItems: "baseline", gap: 12 }}>
              <span className="mono" style={{ fontSize: 17, fontWeight: 600 }}>{varName} at month {tt}</span>
              <span className="mono" style={{ fontSize: 28, fontWeight: 600, color: "var(--accent)" }}>{num(valueAt(varName, tt) as number)}</span>
              {kind && <Badge tone={tone}>{kind}</Badge>}
            </div>
            {v.doc && <p className="muted">{v.doc}</p>}
            <Formula text={v.formula} isVar={(n) => !!byName[n]} onVar={(n, lag) => set(n, tt - lag)} tables={v.tables} />
            <table className="tbl">
              <thead><tr><th>Uses</th><th>At</th><th className="r">Value</th></tr></thead>
              <tbody>
                {v.refs.map(([n, lag]) => {
                  const at = tt - lag;
                  return (
                    <tr key={n + lag} className="clickable" onClick={() => set(n, at)}>
                      <td><span className="chip">{n}</span></td>
                      <td className="faint mono">{at < 0 ? "before start (initial value)" : `month ${at}`}</td>
                      <td className="r mono">{num(valueAt(n, at) as number)}</td>
                    </tr>
                  );
                })}
                {v.inputs.map((n) => (
                  <tr key={n}><td><span className="chip static" style={{ color: "var(--ref)" }}>mp.{n}</span></td><td className="faint">policy data</td>
                    <td className="r mono">{typeof data.inputs[n] === "string" ? data.inputs[n] : num(data.inputs[n] as number)}</td></tr>
                ))}
                {v.tables.map((n) => (
                  <tr key={n} className="clickable" onClick={() => go(model.id, "assumptions", { t: n })}><td><span className="chip" style={{ color: "var(--c5)" }}>{n}</span></td>
                    <td className="faint" colSpan={2}>assumption table · open</td></tr>
                ))}
                {!v.refs.length && !v.inputs.length && !v.tables.length && <tr><td colSpan={3} className="faint">Depends only on time and constants.</td></tr>}
              </tbody>
            </table>
            <div className="stack" style={{ gap: 4 }}>
              <span className="faint" style={{ fontSize: 12 }}>{varName} over {steps} months · the dot marks month {tt}</span>
              <Sparkline values={data.values[varName] || []} marker={tt} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
