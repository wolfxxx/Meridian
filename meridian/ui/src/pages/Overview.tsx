import { api, ModelDetail, RunBrief, RunFull } from "../api";
import { LineChart } from "../components/charts";
import { Badge, Icon, KpiTile, useAsync } from "../components/ui";
import { ago, num, seconds } from "../format";
import { go } from "../router";

export function Overview({ model }: { model: ModelDetail }) {
  const [runs] = useAsync<RunBrief[]>(() => api.runs(model.id), [model.id]);
  const last = (runs || []).find((r) => r.status === "done");
  const [full] = useAsync<RunFull | null>(() => (last ? api.run(last.id) : Promise.resolve(null)), [last?.id]);
  const vars = model.variables_spec;
  const counts = {
    total: vars.length,
    reported: vars.filter((v) => v.total).length,
    pv: vars.filter((v) => v.pv).length,
    lives: vars.filter((v) => /sum_lives/.test(v.formula)).length,
    company: vars.filter((v) => v.cls === "C2").length,
  };
  const net = full?.result?.series?.net_cf || full?.result?.series?.net_outgo;

  return (
    <div className="grid" style={{ gap: 20 }}>
      <div className="card card-pad stack">
        <span className="eyebrow">About this model</span>
        <p style={{ maxWidth: 860, fontSize: 15 }}>{model.description}</p>
      </div>

      {last && full?.result ? (
        <div className="stack">
          <div className="spread">
            <h2>Latest results</h2>
            <span className="faint">{last.label} · {ago(last.finished)} · {seconds(last.seconds)}
              <button className="btn ghost small" onClick={() => go(model.id, "run", { run: last.id })}>Open results <Icon name="arrow" size={14} /></button>
            </span>
          </div>
          <div className="grid cols-4">{full.result.kpis.map((k) => <KpiTile key={k.label} k={k} />)}</div>
          {net && (
            <div className="card card-body">
              <div className="spread" style={{ marginBottom: 8 }}>
                <h3>{net.label.charAt(0).toUpperCase() + net.label.slice(1)} by month</h3>
              </div>
              <LineChart series={[{ key: "net", label: net.label, values: net.values }]} area height={220} />
            </div>
          )}
        </div>
      ) : (
        <div className="card card-pad spread">
          <div className="stack" style={{ gap: 4 }}>
            <h2>No results yet</h2>
            <p className="muted">Run the model to project every policy and see the results here.</p>
          </div>
          <button className="btn primary big" onClick={() => go(model.id, "run", { autorun: 1 })}><Icon name="play" size={16} /> Run model</button>
        </div>
      )}

      <div className="grid cols-3">
        <div className="card card-body stack">
          <div className="spread"><h3>Model at a glance</h3><Icon name="formula" /></div>
          <table className="tbl"><tbody>
            <tr><td>Variables</td><td className="r mono">{counts.total}</td></tr>
            <tr><td>Reported as portfolio totals</td><td className="r mono">{counts.reported}</td></tr>
            <tr><td>Present values per policy</td><td className="r mono">{counts.pv}</td></tr>
            {model.lives > 1 && <tr><td>Policy-level (sum over lives)</td><td className="r mono">{counts.lives}</td></tr>}
            {counts.company > 0 && <tr><td>Company-level feedback</td><td className="r mono">{counts.company}</td></tr>}
            <tr><td>Projection months</td><td className="r mono">{num(model.steps, 0)}</td></tr>
            {model.lives > 1 && <tr><td>Lives per policy (max)</td><td className="r mono">{model.lives}</td></tr>}
          </tbody></table>
          <button className="btn small" onClick={() => go(model.id, "variables")}>Browse variables <Icon name="arrow" size={14} /></button>
        </div>
        <div className="card card-body stack">
          <div className="spread"><h3>Assumptions</h3><Icon name="table" /></div>
          <div className="stack" style={{ gap: 0 }}>
            {model.tables.map((t) => (
              <button key={t.name} className="list-item" style={{ padding: "8px 0" }} onClick={() => go(model.id, "assumptions", { t: t.name })}>
                <span className="stack" style={{ gap: 0, textAlign: "left" }}>
                  <span className="li-name">{t.name}</span>
                  <span className="faint" style={{ fontSize: 12 }}>{t.description}</span>
                </span>
                {t.modified ? <Badge tone="warn">edited</Badge> : t.editable ? <Badge>editable</Badge> : <Badge><Icon name="lock" size={12} /> fixed</Badge>}
              </button>
            ))}
          </div>
        </div>
        <div className="card card-body stack">
          <div className="spread"><h3>Validation</h3><Icon name="shield" /></div>
          <p className="muted">
            {model.source.startsWith("lifelib")
              ? "This model was rebuilt from lifelib’s published model. Run the reconciliation to compare every policy with lifelib’s own results."
              : "This model is checked against a separate, deliberately simple implementation written from the product description, and against the reference engine."}
          </p>
          <button className="btn small" onClick={() => go(model.id, "validation")}>Open validation <Icon name="arrow" size={14} /></button>
        </div>
      </div>
    </div>
  );
}
