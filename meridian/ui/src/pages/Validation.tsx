import { useEffect, useState } from "react";
import { api, ModelDetail, ValidationState } from "../api";
import { Badge, ErrorNote, Icon, Spinner, useInterval } from "../components/ui";
import { num, seconds } from "../format";

export function Validation({ model }: { model: ModelDetail }) {
  const [state, setState] = useState<ValidationState | null>(null);
  useEffect(() => { api.validation(model.id).then(setState); }, [model.id]);
  useInterval(() => { api.validation(model.id).then(setState); }, state?.status === "running" ? 500 : null);
  const start = () => api.startValidation(model.id).then(setState);
  const all = state?.result?.flatMap((s) => s.checks) || [];
  const passed = all.filter((c) => c.passed).length;

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="card card-pad spread">
        <div className="stack" style={{ gap: 4, maxWidth: 760 }}>
          <h2>Validation</h2>
          <p className="muted">
            {model.source.startsWith("lifelib")
              ? "Meridian reproduces lifelib’s published model. This runs both on the same data and compares every policy. lifelib’s results were produced by lifelib itself and ship with Meridian."
              : "There is no published reference for this product, so Meridian is checked against a separate, deliberately plain implementation written from the product description, and against its own reference engine."}
          </p>
        </div>
        {state?.status === "running" ? <div className="row"><Spinner /><span className="muted">Comparing…</span></div>
          : <button className="btn primary big" onClick={start}><Icon name="shield" size={16} /> {state?.status === "done" ? "Run again" : "Run validation"}</button>}
      </div>
      {state?.status === "failed" && <ErrorNote error={state.error || "Validation failed to run."} />}
      {state?.status === "done" && state.result && (
        <>
          <div className="row" style={{ gap: 12 }}>
            <Badge tone={passed === all.length ? "good" : "bad"}>{passed} of {all.length} checks passed</Badge>
            <span className="faint">in {seconds(state.seconds)}</span>
          </div>
          {state.result.map((s) => (
            <div key={s.title} className="card">
              <div className="card-head">
                <div className="stack" style={{ gap: 1 }}><h3>{s.title}</h3><span className="faint" style={{ fontSize: 12.5 }}>Reference: {s.reference}</span></div>
              </div>
              <div className="grid cols-2" style={{ padding: "4px 18px 16px", gap: 28, alignItems: "start" }}>
                <div>
                  {s.checks.map((c) => (
                    <div key={c.name} className="check-row">
                      <span className={`check-icon ${c.passed ? "" : "fail"}`}><Icon name={c.passed ? "check" : "alert"} size={14} /></span>
                      <span className="stack" style={{ gap: 0 }}><span>{c.name}</span><span className="faint" style={{ fontSize: 12 }}>{c.detail}</span></span>
                      <span className="mono" style={{ fontSize: 12.5 }}>{c.metric}</span>
                    </div>
                  ))}
                </div>
                {s.sample.length > 0 && (
                  <div className="stack" style={{ gap: 6, paddingTop: 10 }}>
                    <span className="eyebrow">{s.sample_label}: first rows</span>
                    <table className="tbl">
                      <thead><tr><th /><th className="r">Meridian</th><th className="r" style={{ color: "var(--ref)" }}>Reference</th></tr></thead>
                      <tbody>{s.sample.map((r) => (
                        <tr key={String(r.policy)}><td className="mono faint">{r.policy}</td><td className="r mono">{num(r.meridian, 4)}</td><td className="r mono" style={{ color: "var(--ref)" }}>{num(r.reference, 4)}</td></tr>
                      ))}</tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          ))}
        </>
      )}
      {state?.status === "not_started" && (
        <div className="card"><div className="empty"><Icon name="shield" size={28} /><h3>Not run yet</h3><p className="muted">It takes a few seconds.</p></div></div>
      )}
    </div>
  );
}
