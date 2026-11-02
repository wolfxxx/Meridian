import { useState } from "react";
import { api, ModelDetail } from "../api";
import { MODEL_ICON } from "../App";
import { Badge, ErrorNote, Icon, Spinner, useAsync } from "../components/ui";
import { go } from "../router";
import { Assumptions } from "./Assumptions";
import { Explain } from "./Explain";
import { Overview } from "./Overview";
import { PolicyData } from "./PolicyData";
import { Runs } from "./Runs";
import { Validation } from "./Validation";
import { Variables } from "./Variables";

export const SECTIONS: [string, string, string][] = [
  ["overview", "Overview", "overview"],
  ["variables", "Variables", "formula"],
  ["assumptions", "Assumptions", "table"],
  ["data", "Policy data", "people"],
  ["run", "Run & results", "play"],
  ["explain", "Explain", "explain"],
  ["validation", "Validation", "shield"],
];

export function ModelPage({ modelId, section, params, onChanged }:
  { modelId: string; section: string; params: Record<string, string>; onChanged: () => void }) {
  const [model, err, reload] = useAsync<ModelDetail>(() => api.model(modelId), [modelId]);
  const [starting, setStarting] = useState(false);
  const refresh = () => { reload(); onChanged(); };

  async function quickRun() {
    setStarting(true);
    try {
      const opts: Record<string, number> = {};
      model?.run_options.forEach((o) => (opts[o.key] = o.default));
      const r = await api.startRun(modelId, opts);
      go(modelId, "run", { run: r.id });
    } finally { setStarting(false); }
  }

  if (err) return <div className="page"><ErrorNote error={err} /></div>;
  if (!model) return <div className="page"><div className="row"><Spinner /><span className="muted">Opening model…</span></div></div>;

  return (
    <>
      <header className="model-head"><div className="head-inner">
        <div className="model-head-row">
          <div className="stack" style={{ gap: 6 }}>
            <div className="crumbs"><button onClick={() => go(null)}>Workspace</button><span>/</span><span>{model.name}</span></div>
            <div className="row" style={{ gap: 12 }}>
              <div className="model-glyph" style={{ width: 34, height: 34 }}><Icon name={MODEL_ICON[model.id] || "formula"} size={19} /></div>
              <h1>{model.name}</h1>
              <Badge tone={model.source.startsWith("lifelib") ? "ref" : ""}>{model.source}</Badge>
              {model.modified_tables.length > 0 && <Badge tone="warn">Edited: {model.modified_tables.join(", ")}</Badge>}
            </div>
            <p className="muted">{model.tagline}</p>
          </div>
          <div className="row">
            <button className="btn primary big" onClick={quickRun} disabled={starting}>
              {starting ? <span className="spinner" style={{ borderTopColor: "var(--accent-ink)" }} /> : <Icon name="play" size={16} />}
              Run model
            </button>
          </div>
        </div>
        <div className="tabs" role="tablist" aria-label="Model sections">
          {SECTIONS.map(([id, label, icon]) => (
            <button key={id} className="tab" role="tab" aria-selected={section === id} onClick={() => go(modelId, id)}>
              <Icon name={icon} size={16} />{label}
            </button>
          ))}
        </div>
      </div></header>
      <div className="page">
        {section === "overview" && <Overview model={model} />}
        {section === "variables" && <Variables model={model} selected={params.v} />}
        {section === "assumptions" && <Assumptions model={model} selected={params.t} onChanged={refresh} />}
        {section === "data" && <PolicyData model={model} />}
        {section === "run" && <Runs model={model} runId={params.run} autorun={params.autorun === "1"} />}
        {section === "explain" && <Explain model={model} params={params} />}
        {section === "validation" && <Validation model={model} />}
      </div>
    </>
  );
}
