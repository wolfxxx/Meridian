import { ModelSummary } from "../api";
import { MODEL_ICON } from "../App";
import { Badge, ErrorNote, Icon, Spinner } from "../components/ui";
import { ago, kpiValue, num } from "../format";
import { go } from "../router";

export function Workspace({ models, error }: { models: ModelSummary[] | null; error: string | null }) {
  return (
    <div className="page">
      <div className="hero">
        <span className="eyebrow">Workspace</span>
        <h1>Your models</h1>
        <p className="muted" style={{ maxWidth: 720 }}>
          Each model holds its formulas, assumptions and policy data. Open one to read how it works, change an
          assumption, run it, and trace any number back to its inputs.
        </p>
      </div>
      {error && <ErrorNote error={error} />}
      {!models && !error && <div className="row"><Spinner /> <span className="muted">Loading models…</span></div>}
      <div className="grid cols-3">
        {(models || []).map((m) => (
          <div key={m.id} className="card model-card" role="button" tabIndex={0}
            onClick={() => go(m.id)} onKeyDown={(e) => { if (e.key === "Enter") go(m.id); }}>
            <div className="spread" style={{ alignItems: "flex-start" }}>
              <div className="model-glyph"><Icon name={MODEL_ICON[m.id] || "formula"} size={22} /></div>
              <Badge tone={m.source.startsWith("lifelib") ? "ref" : ""}>{m.source}</Badge>
            </div>
            <div className="stack" style={{ gap: 4 }}>
              <h2>{m.name}</h2>
              <p className="muted">{m.tagline}</p>
            </div>
            <div className="stat-row">
              <div className="stat"><div className="s-v">{num(m.policies, 0)}</div><div className="s-l">policies</div></div>
              {m.lives > 1 && <div className="stat"><div className="s-v">{num(m.rows, 0)}</div><div className="s-l">lives</div></div>}
              <div className="stat"><div className="s-v">{num(m.steps, 0)}</div><div className="s-l">months</div></div>
              <div className="stat"><div className="s-v">{m.variables}</div><div className="s-l">variables</div></div>
            </div>
            <div style={{ borderTop: "1px solid var(--line)", paddingTop: 12, minHeight: 58 }}>
              {m.last_run?.kpis ? (
                <div className="stack" style={{ gap: 2 }}>
                  <span className="faint" style={{ fontSize: 12 }}>Last run · {ago(m.last_run.finished)}</span>
                  <span><span className="muted">{m.last_run.kpis[0].label}: </span>
                    <strong className="mono">{kpiValue(m.last_run.kpis[0])}</strong></span>
                </div>
              ) : <span className="faint" style={{ fontSize: 13 }}>Not run yet in this session.</span>}
            </div>
            <div className="row">
              <button className="btn primary" onClick={(e) => { e.stopPropagation(); go(m.id, "run", { autorun: 1 }); }}>
                <Icon name="play" size={15} /> Run
              </button>
              <button className="btn" onClick={(e) => { e.stopPropagation(); go(m.id); }}>Open <Icon name="arrow" size={15} /></button>
            </div>
          </div>
        ))}
      </div>
      <div className="card card-pad" style={{ display: "grid", gap: 10 }}>
        <h3>How Meridian works</h3>
        <div className="grid cols-3" style={{ gap: 20 }}>
          <div className="stack" style={{ gap: 4 }}>
            <strong>Formulas you can read</strong>
            <span className="muted">Every variable is one formula over time, like a library variable in Prophet. The order of calculation is worked out for you.</span>
          </div>
          <div className="stack" style={{ gap: 4 }}>
            <strong>Fast, exact engine</strong>
            <span className="muted">A compiled engine projects every policy, scenario and month in parallel. Results are identical every time, whatever the machine.</span>
          </div>
          <div className="stack" style={{ gap: 4 }}>
            <strong>Checked against references</strong>
            <span className="muted">The term and savings models reproduce lifelib’s published models policy by policy. See each model’s Validation tab.</span>
          </div>
        </div>
      </div>
    </div>
  );
}
