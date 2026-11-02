import { useEffect, useState } from "react";
import { api, ColumnStats, DataPage, ModelDetail } from "../api";
import { Histogram } from "../components/charts";
import { Icon, Spinner, useAsync } from "../components/ui";
import { ago, compact, num } from "../format";
import { go } from "../router";
import { ImportDialog } from "./ImportDialog";

const PAGE = 100;

export function PolicyData({ model, onChanged }: { model: ModelDetail; onChanged: () => void }) {
  const version = model.data_source?.at ?? 0;
  const [stats] = useAsync<ColumnStats[]>(() => api.dataStats(model.id), [model.id, version]);
  const [importing, setImporting] = useState(false);
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<DataPage | null>(null);
  useEffect(() => { const id = setTimeout(() => { setQuery(q); setOffset(0); }, 250); return () => clearTimeout(id); }, [q]);
  useEffect(() => { let on = true; api.data(model.id, offset, PAGE, query).then((p) => on && setPage(p)); return () => { on = false; }; }, [model.id, offset, query, version]);
  async function restore() { await api.resetData(model.id); setOffset(0); onChanged(); }
  const money = model.currency ? model.currency + " " : "";
  const lifeWord = model.lives > 1 ? "lives" : "policies";

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="spread">
        <div className="stack" style={{ gap: 2 }}>
          <h2>Policy data</h2>
          <p className="muted">{model.lives > 1
            ? `One row per insured life, as an administration system holds it. Meridian groups the lives of each policy (up to ${model.lives}) when it runs.`
            : "One row per model point, read straight from the data file."}</p>
        </div>
        <div className="row" data-tour="import">
          <a className="btn" href={`/api/models/${model.id}/data/template.csv`} download><Icon name="file" size={15} /> Template</a>
          <a className="btn" href={`/api/models/${model.id}/data/export.csv`} download><Icon name="download" size={15} /> Export CSV</a>
          <button className="btn primary" onClick={() => setImporting(true)}><Icon name="upload" size={15} /> Import your data</button>
        </div>
      </div>
      {model.data_source && (
        <div className="callout info">
          <Icon name="file" />
          <div className="spread" style={{ flex: 1 }}>
            <span>Using <strong>your data</strong> from <span className="mono">{model.data_source.name}</span> · {num(model.data_source.rows, 0)} rows · loaded {ago(model.data_source.at)}.
              Runs use it until you restore the original data or close Meridian.</span>
            <button className="btn small" onClick={restore}><Icon name="reset" size={14} /> Restore original data</button>
          </div>
        </div>
      )}
      {importing && <ImportDialog model={model} onClose={() => setImporting(false)} onDone={() => { setImporting(false); setOffset(0); onChanged(); }} />}
      <div className="grid cols-4">
        {(stats || []).filter((s) => s.key !== model.data_columns[0].key).slice(0, 8).map((s) => (
          <div key={s.key} className="card card-body stack" style={{ gap: 6 }}>
            <span className="faint" style={{ fontSize: 12 }}>{s.label}</span>
            {s.kind === "number" ? (
              <>
                <span className="mono" style={{ fontWeight: 600 }}>{compact(s.min!)} – {compact(s.max!)}</span>
                <Histogram hist={s.hist!} height={44} />
                <span className="faint mono" style={{ fontSize: 11.5 }}>mean {num(s.mean!)}</span>
              </>
            ) : (
              <div className="stack" style={{ gap: 3 }}>
                {s.top!.slice(0, 5).map(([v, c]) => {
                  const total = s.top!.reduce((a, b) => a + b[1], 0);
                  return (
                    <div key={v} className="stack" style={{ gap: 2 }}>
                      <div className="spread" style={{ fontSize: 12.5 }}><span className="mono">{v}</span><span className="faint mono">{num(c, 0)}</span></div>
                      <div className="progress" style={{ height: 4 }}><div style={{ width: `${(100 * c) / total}%` }} /></div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="card">
        <div className="card-head">
          <div className="search" style={{ width: 340 }}><Icon name="search" size={16} />
            <input placeholder="Search policy number, product, role…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search policy data" /></div>
          <span className="faint">{page ? `${num(page.total, 0)} ${lifeWord}` : ""}</span>
        </div>
        {!page ? <div className="card-body row"><Spinner /> Loading…</div> : (
          <>
            <div className="tbl-wrap" style={{ maxHeight: 520 }}>
              <table className="tbl">
                <thead><tr>
                  {model.data_columns.map((c) => <th key={c.key} className={c.kind !== "id" && typeof page.rows[0]?.[c.key] !== "string" ? "r" : ""}>{c.label}</th>)}
                  <th />
                </tr></thead>
                <tbody>
                  {page.rows.map((r) => (
                    <tr key={r._row} className="clickable" onClick={() => go(model.id, "explain", { p: r._row })}>
                      {model.data_columns.map((c) => {
                        const v = r[c.key];
                        const isText = typeof v === "string";
                        return <td key={c.key} className={!isText && c.kind !== "id" ? "r mono" : "mono"}>
                          {isText ? v : c.kind === "money" ? money + num(v, v % 1 ? 2 : 0) : c.kind === "id" ? v : num(v)}
                        </td>;
                      })}
                      <td className="r"><span className="faint" style={{ fontSize: 12 }}>Explain <Icon name="arrow" size={13} /></span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="card-body spread" style={{ borderTop: "1px solid var(--line)" }}>
              <span className="faint">Rows {num(Math.min(offset + 1, page.total), 0)}–{num(Math.min(offset + PAGE, page.total), 0)} of {num(page.total, 0)}</span>
              <div className="row">
                <button className="btn small" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>Previous</button>
                <button className="btn small" disabled={offset + PAGE >= page.total} onClick={() => setOffset(offset + PAGE)}>Next</button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
