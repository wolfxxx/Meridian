import { useEffect, useRef, useState } from "react";
import { api, ModelDetail, RunBrief, RunFull } from "../api";
import { BarList, LineChart, PALETTE, ScenarioBars } from "../components/charts";
import { Badge, ErrorNote, Icon, KpiTile, Progress, Spinner, useInterval } from "../components/ui";
import { ago, money, num, pct, seconds, sentence } from "../format";
import { go } from "../router";

export function Runs({ model, runId, autorun }: { model: ModelDetail; runId?: string; autorun: boolean }) {
  const [runs, setRuns] = useState<RunBrief[]>([]);
  const [current, setCurrent] = useState<RunFull | null>(null);
  const [baselineId, setBaselineId] = useState<string>("");
  const [baseline, setBaseline] = useState<RunFull | null>(null);
  const [opts, setOpts] = useState<Record<string, number>>(() => Object.fromEntries(model.run_options.map((o) => [o.key, o.default])));
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  const loadRuns = () => api.runs(model.id).then(setRuns).catch((e) => setError(String(e.message || e)));
  useEffect(() => { loadRuns(); }, [model.id]);

  async function start() {
    setError(null);
    try {
      const r = await api.startRun(model.id, opts);
      go(model.id, "run", { run: r.id });
      loadRuns();
    } catch (e: any) { setError(String(e.message || e)); }
  }
  useEffect(() => {
    if (autorun && !started.current) { started.current = true; start(); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autorun]);

  const selected = runId || runs.find((r) => r.status === "done")?.id || runs[0]?.id;
  useEffect(() => { if (selected) api.run(selected).then(setCurrent).catch((e) => setError(String(e.message || e))); else setCurrent(null); }, [selected]);
  const active = current && (current.status === "running" || current.status === "queued");
  useInterval(() => {
    if (selected) api.run(selected).then((r) => { setCurrent(r); if (r.status === "done" || r.status === "failed") loadRuns(); });
  }, active ? 400 : null);

  useEffect(() => { if (baselineId) api.run(baselineId).then(setBaseline); else setBaseline(null); }, [baselineId]);
  const others = runs.filter((r) => r.status === "done" && r.id !== selected);
  const res = current?.result;
  const unit = model.currency;

  return (
    <div className="split" style={{ gridTemplateColumns: "300px minmax(0, 1fr)" }}>
      <div className="grid" style={{ gap: 16 }}>
        <div className="card card-body stack" style={{ gap: 12 }}>
          <h3>New run</h3>
          {model.run_options.map((o) => (
            <label key={o.key} className="stack" style={{ gap: 4 }}>
              <span className="faint" style={{ fontSize: 12 }}>{o.label}</span>
              <select className="input" value={opts[o.key]} onChange={(e) => setOpts({ ...opts, [o.key]: Number(e.target.value) })}>
                {o.choices.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </label>
          ))}
          {model.modified_tables.length > 0
            ? <div className="callout" style={{ fontSize: 12.5 }}><Icon name="edit" size={16} /><div>Uses your edited {model.modified_tables.join(", ")}. <button className="btn small ghost" onClick={() => go(model.id, "assumptions")}>Review</button></div></div>
            : <span className="faint" style={{ fontSize: 12.5 }}>Uses the model’s original assumptions.</span>}
          <button className="btn primary big" onClick={start}><Icon name="play" size={16} /> Run model</button>
        </div>
        <div className="card">
          <div className="card-head"><h3>Run history</h3><Icon name="history" /></div>
          {runs.length === 0 && <div className="card-body faint">No runs yet in this session.</div>}
          {runs.map((r) => (
            <button key={r.id} className="list-item" aria-current={r.id === selected} onClick={() => go(model.id, "run", { run: r.id })}>
              <span className="stack" style={{ gap: 1, textAlign: "left", minWidth: 0 }}>
                <span style={{ fontWeight: 600, fontSize: 13 }}>{r.label}</span>
                <span className="faint" style={{ fontSize: 12 }}>{ago(r.started)}{r.seconds ? ` · ${seconds(r.seconds)}` : ""}</span>
              </span>
              {r.status === "done" ? <Badge tone="good">done</Badge> : r.status === "failed" ? <Badge tone="bad">failed</Badge> : <Spinner />}
            </button>
          ))}
        </div>
      </div>

      <div className="grid" style={{ gap: 16 }}>
        {error && <ErrorNote error={error} />}
        {!current && !error && (
          <div className="card"><div className="empty">
            <Icon name="play" size={28} /><h3>Run the model to see results</h3>
            <p className="muted">Every policy is projected month by month; results appear here.</p>
            <button className="btn primary" onClick={start}><Icon name="play" size={15} /> Run model</button>
          </div></div>
        )}
        {current && active && (
          <div className="card card-pad stack" style={{ gap: 12 }}>
            <div className="spread"><h2>Running…</h2><Spinner /></div>
            <Progress value={current.progress} />
            <span className="muted">{current.message}</span>
          </div>
        )}
        {current?.status === "failed" && <ErrorNote error={current.error || "The run failed."} />}
        {res && current?.status === "done" && (
          <>
            <div className="spread">
              <div className="stack" style={{ gap: 2 }}>
                <h2>{current.label}</h2>
                <span className="faint">{num(res.policies, 0)} policies{current.data ? ` from ${current.data}` : ""} · calculated in {seconds(res.seconds)} · {ago(current.finished)}</span>
              </div>
              <div className="row">
              <a className="btn small" href={`/api/runs/${current.id}/export.csv`} download><Icon name="download" size={14} /> Export CSV</a>
              <button className="btn small" onClick={() => go(model.id, "whatif")}><Icon name="sliders" size={14} /> What-if</button>
              {others.length > 0 && (
                <label className="row faint" style={{ fontSize: 12.5 }}>Compare with
                  <select className="input" value={baselineId} onChange={(e) => setBaselineId(e.target.value)}>
                    <option value="">nothing</option>
                    {others.map((r) => <option key={r.id} value={r.id}>{r.label} ({ago(r.started)})</option>)}
                  </select>
                </label>
              )}
              </div>
            </div>
            <div className="grid cols-4">
              {res.kpis.map((k, i) => <KpiTile key={k.label} k={k} baseline={baseline?.result?.kpis[i]} />)}
            </div>
            {res.sam && <SamPanel sam={res.sam} unit={unit} />}
            <CashFlows res={res} baseline={baseline} unit={unit} />
            {res.scenarios && (
              <div className="card card-body stack">
                <h3>Present value of net cash flow by scenario</h3>
                <p className="faint" style={{ fontSize: 12.5 }}>Each bar is one economic scenario, worst to best. Amber bars are the worst 30%, which set the CTE70.</p>
                <ScenarioBars values={res.scenarios} unit={unit} />
              </div>
            )}
            <div className="card">
              <div className="card-head"><h3>Present values</h3><span className="faint">portfolio, at the valuation date</span></div>
              <div className="grid cols-2" style={{ padding: 16, alignItems: "center" }}>
                <table className="tbl"><tbody>
                  {res.pv_table.map((r) => (
                    <tr key={r.label}><td>{r.label}</td><td className="r mono">{money(r.value, unit)}</td><td className="r mono faint">{pct(r.share)}</td></tr>
                  ))}
                </tbody></table>
                <BarList unit={unit} items={res.pv_table.map((r, i) => ({ label: r.label, value: r.value, color: r.value < 0 ? "var(--c6)" : PALETTE[i % PALETTE.length] }))} />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function CashFlows({ res, baseline, unit }: { res: NonNullable<RunFull["result"]>; baseline: RunFull | null; unit: string }) {
  const keys = Object.keys(res.series);
  const counts = keys.filter((k) => /pols|policies|deaths/.test(k));
  const money_ = keys.filter((k) => !counts.includes(k));
  // Start with premiums and claims: one-off acquisition costs would otherwise dominate the scale.
  const preferred = money_.filter((k) => /premium|claims/.test(k));
  const [on, setOn] = useState<string[]>(preferred.length ? preferred : money_.slice(0, 2));
  const [view, setView] = useState<"money" | "counts">("money");
  const visible = view === "money" ? money_ : counts;
  const shown = (view === "money" ? on : counts).filter((k) => visible.includes(k));
  const series = shown.flatMap((k, i) => {
    const color = PALETTE[visible.indexOf(k) % PALETTE.length];
    const s = [{ key: k, label: sentence(res.series[k].label), values: res.series[k].values, color }];
    const b = baseline?.result?.series[k];
    if (b) s.push({ key: k + "-b", label: `${sentence(res.series[k].label)} (baseline)`, values: b.values, color, dashed: true } as any);
    return s;
    void i;
  });
  return (
    <div className="card card-body stack">
      <div className="spread">
        <h3>{view === "money" ? "Cash flows by month" : "Policies and decrements by month"}</h3>
        {counts.length > 0 && (
          <div className="seg" role="group" aria-label="Chart">
            <button aria-pressed={view === "money"} onClick={() => setView("money")}>Cash flows</button>
            <button aria-pressed={view === "counts"} onClick={() => setView("counts")}>Policies</button>
          </div>
        )}
      </div>
      {view === "money" && (
        <div className="legend">
          {money_.map((k) => (
            <button key={k} aria-pressed={on.includes(k)} onClick={() => setOn(on.includes(k) ? on.filter((x) => x !== k) : [...on, k])}>
              <span className="sw" style={{ background: PALETTE[money_.indexOf(k) % PALETTE.length] }} />{sentence(res.series[k].label)}
            </button>
          ))}
        </div>
      )}
      {series.length ? <LineChart series={series} unit={view === "money" && unit ? unit + " " : ""} height={280} />
        : <p className="faint">Choose a series above.</p>}
      {baseline && <span className="faint" style={{ fontSize: 12 }}>Dashed lines: {baseline.label}.</span>}
    </div>
  );
}

function SamPanel({ sam, unit }: { sam: NonNullable<NonNullable<RunFull["result"]>["sam"]>; unit: string }) {
  const stresses = Object.keys(sam.labels);
  const undiv = sam.scr.mortality + sam.scr.lapse + sam.scr.expense + sam.scr.catastrophe;
  return (
    <div className="grid cols-2">
      <div className="card">
        <div className="card-head"><h3>Best-estimate liability by basis</h3><span className="faint">SAM-style stresses</span></div>
        <table className="tbl"><tbody>
          <tr><td><strong>Base</strong></td><td className="r mono">{money(sam.bel.base, unit)}</td><td /></tr>
          {stresses.map((k) => {
            const d = sam.bel[k] - sam.bel.base;
            return <tr key={k}><td>{sam.labels[k]}</td><td className="r mono">{money(sam.bel[k], unit)}</td>
              <td className="r mono" style={{ color: d > 0 ? "var(--bad)" : "var(--good)" }}>{d > 0 ? "+" : "−"}{money(Math.abs(d), "").trim()}</td></tr>;
          })}
        </tbody></table>
      </div>
      <div className="card card-body stack">
        <div className="spread"><h3>Capital and risk margin</h3><span className="faint">diversification {pct(1 - sam.scr.life / undiv, 0)}</span></div>
        <BarList unit={unit} items={[
          { label: "Mortality", value: sam.scr.mortality }, { label: "Lapse (worst)", value: sam.scr.lapse },
          { label: "Expense", value: sam.scr.expense }, { label: "Catastrophe", value: sam.scr.catastrophe },
          { label: "Sum of modules", value: undiv, color: "var(--line-strong)" },
          { label: "SCR life", value: sam.scr.life, color: "var(--c3)" },
          { label: "Risk margin", value: sam.risk_margin, color: "var(--ref)" }]} />
        <table className="tbl"><tbody>
          <tr><td>Technical provisions (BEL + risk margin)</td><td className="r mono"><strong>{money(sam.tp, unit)}</strong></td></tr>
        </tbody></table>
        <p className="faint" style={{ fontSize: 12 }}>Life SCR aggregates the four modules with the standard-formula correlations. The risk margin is 6% a year of the SCR, projected in proportion to policies in force.</p>
      </div>
    </div>
  );
}
