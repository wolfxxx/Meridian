import { useRef, useState } from "react";
import { api, ImportReport, ModelDetail } from "../api";
import { Badge, ErrorNote, Icon, Modal, Spinner } from "../components/ui";
import { num } from "../format";

type Stage = "pick" | "checking" | "report" | "applying";

/** Import policy data from a CSV: pick a file, see the checks and a preview, then confirm. */
export function ImportDialog({ model, onClose, onDone }: { model: ModelDetail; onClose: () => void; onDone: () => void }) {
  const [stage, setStage] = useState<Stage>("pick");
  const [file, setFile] = useState<{ name: string; text: string } | null>(null);
  const [report, setReport] = useState<ImportReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [over, setOver] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const unitWord = model.lives > 1 ? "lives" : "rows";

  async function choose(f: File | undefined) {
    if (!f) return;
    setError(null);
    if (f.size > 60e6) { setError("The file is larger than 60 MB. Split it, or use fewer columns."); return; }
    setStage("checking");
    try {
      const text = await f.text();
      setFile({ name: f.name, text });
      setReport(await api.importData(model.id, text, f.name));
      setStage("report");
    } catch (e: any) { setError(String(e.message || e)); setStage("pick"); }
  }

  async function apply() {
    if (!file) return;
    setStage("applying");
    try { await api.importData(model.id, file.text, file.name, true); onDone(); }
    catch (e: any) { setError(String(e.message || e)); setStage("report"); }
  }

  const ok = report?.ok;
  const footer = stage === "report" || stage === "applying" ? (
    <>
      {!ok && <span className="faint" style={{ marginRight: "auto", fontSize: 12.5 }}>Fix the file in Excel and choose it again; nothing has changed yet.</span>}
      <button className="btn ghost" onClick={onClose}>Cancel</button>
      <button className="btn" onClick={() => { setReport(null); setStage("pick"); }}>Choose another file</button>
      <button className="btn primary" disabled={!ok || stage === "applying"} onClick={apply}>
        {stage === "applying" ? <Spinner /> : <Icon name="check" size={15} />} Use these {num(report?.rows ?? 0, 0)} {unitWord}
      </button>
    </>
  ) : <button className="btn ghost" onClick={onClose}>Cancel</button>;

  return (
    <Modal title="Import your policy data" onClose={onClose} width={920} footer={footer}>
      {error && <ErrorNote error={error} />}
      {(stage === "pick" || stage === "checking") && (
        <>
          <div className={"drop" + (over ? " over" : "")} role="button" tabIndex={0}
            onClick={() => input.current?.click()} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") input.current?.click(); }}
            onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
            onDrop={(e) => { e.preventDefault(); setOver(false); choose(e.dataTransfer.files[0]); }}>
            {stage === "checking" ? <><Spinner /><strong>Checking every row…</strong></> : <>
              <Icon name="upload" size={30} />
              <strong style={{ fontSize: 15 }}>Drop a CSV file here, or click to choose one</strong>
              <span className="faint">Save from Excel as “CSV (comma delimited)” or “CSV UTF-8”. Semicolons and decimal commas are fine too.</span>
            </>}
            <input ref={input} type="file" accept=".csv,.txt,text/csv" hidden onChange={(e) => choose(e.target.files?.[0])} />
          </div>
          <div className="stack" style={{ gap: 8 }}>
            <div className="spread">
              <h3>What the file needs</h3>
              <a className="btn small" href={`/api/models/${model.id}/data/template.csv`} download><Icon name="download" size={14} /> Download a template</a>
            </div>
            <p className="muted" style={{ fontSize: 13 }}>
              One heading row, then {model.lives > 1 ? "one row per insured life; lives of the same policy share a policy number" : "one row per policy or model point"}.
              Headings are matched by name, ignoring case and spaces, so “Sum Assured”, “sum_assured” and “SA” all work. Extra columns are ignored.
            </p>
            <div className="tbl-wrap card" style={{ boxShadow: "none" }}>
              <table className="tbl">
                <thead><tr><th>Column</th><th>What it is</th><th>Allowed values</th></tr></thead>
                <tbody>
                  {model.input_schema.map((f) => (
                    <tr key={f.key}>
                      <td className="mono">{f.key}</td>
                      <td>{f.description}</td>
                      <td className="faint">{f.choices ? f.choices.join(", ")
                        : [f.kind === "integer" ? "whole number" : f.kind === "text" ? "text" : "number",
                           f.min !== null ? `≥ ${f.min}` : "", f.max !== null ? `≤ ${f.max}` : ""].filter(Boolean).join(", ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
      {(stage === "report" || stage === "applying") && report && <Report report={report} model={model} fileName={file?.name || ""} unitWord={unitWord} />}
    </Modal>
  );
}

function Report({ report, model, fileName, unitWord }: { report: ImportReport; model: ModelDetail; fileName: string; unitWord: string }) {
  const matched = report.matched || [];
  return (
    <>
      <div className="row" style={{ gap: 14 }}>
        <span className={"check-icon" + (report.ok ? "" : " fail")} style={{ width: 34, height: 34 }}>
          <Icon name={report.ok ? "check" : "alert"} size={18} /></span>
        <div className="stack" style={{ gap: 2 }}>
          <strong style={{ fontSize: 15 }}>
            {report.ok ? `All ${num(report.rows ?? 0, 0)} ${unitWord} passed the checks`
              : report.fatal || `${num(report.error_count ?? 0, 0)} problem${report.error_count === 1 ? "" : "s"} found`}
          </strong>
          <span className="faint mono" style={{ fontSize: 12 }}>{fileName} · {num(report.rows ?? 0, 0)} data rows
            {report.delimiter ? ` · separated by “${report.delimiter === "\t" ? "tab" : report.delimiter}”` : ""}</span>
        </div>
      </div>

      {!!report.missing?.length && (
        <div className="callout">
          <Icon name="alert" />
          <div className="stack" style={{ gap: 4 }}>
            <strong>Missing columns</strong>
            {report.missing.map((m) => <span key={m.key}><span className="mono">{m.key}</span> <span className="muted">· {m.description}</span></span>)}
            {!!report.unused?.length && <span className="faint">Columns in your file that were not recognised: {report.unused.join(", ")}. Rename one to match.</span>}
          </div>
        </div>
      )}

      {matched.length > 0 && (
        <div className="stack" style={{ gap: 6 }}>
          <h3>Columns</h3>
          <div className="chips">
            {matched.map((m) => (
              <span key={m.key} className="chip static" title={m.label}>
                {m.column === m.key ? m.key : <>{m.column} <span className="faint">→</span> {m.key}</>}
              </span>
            ))}
            {!report.missing?.length && !!report.unused?.length && <span className="faint" style={{ fontSize: 12 }}>Ignored: {report.unused.join(", ")}</span>}
          </div>
        </div>
      )}

      {!!report.errors?.length && (
        <div className="stack" style={{ gap: 6 }}>
          <div className="spread">
            <h3>Problems</h3>
            <div className="chips">{Object.entries(report.error_summary || {}).map(([k, n]) => <Badge key={k} tone="bad">{k}: {num(n, 0)}</Badge>)}</div>
          </div>
          <div className="tbl-wrap card" style={{ maxHeight: 260, boxShadow: "none" }}>
            <table className="tbl">
              <thead><tr><th className="r">Row</th><th>Column</th><th>Value</th><th>Problem</th></tr></thead>
              <tbody>{report.errors.map((e, i) => (
                <tr key={i}><td className="r mono">{e.row}</td><td>{e.column}</td><td className="mono">{e.value === "" ? <span className="faint">(empty)</span> : e.value}</td><td>{e.message}</td></tr>
              ))}</tbody>
            </table>
          </div>
          {(report.error_count ?? 0) > report.errors.length && <span className="faint" style={{ fontSize: 12 }}>Showing the first {report.errors.length} of {num(report.error_count!, 0)}.</span>}
        </div>
      )}

      {!!report.preview?.length && !report.missing?.length && (
        <div className="stack" style={{ gap: 6 }}>
          <h3>First rows of your file</h3>
          <div className="tbl-wrap card" style={{ boxShadow: "none" }}>
            <table className="tbl">
              <thead><tr>{model.input_schema.map((f) => <th key={f.key} className={f.kind === "text" ? "" : "r"}>{f.key}</th>)}</tr></thead>
              <tbody>{report.preview.map((r, i) => (
                <tr key={i}>{model.input_schema.map((f) => <td key={f.key} className={"mono" + (f.kind === "text" ? "" : " r")}>{r[f.key]}</td>)}</tr>
              ))}</tbody>
            </table>
          </div>
        </div>
      )}
      {report.ok && (
        <div className="callout info"><Icon name="info" />
          <span>Using this data replaces the model’s current policy data for this session. Assumptions and earlier runs are kept, and you can restore the original data at any time.</span>
        </div>
      )}
    </>
  );
}
