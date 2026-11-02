import { useEffect, useMemo, useState } from "react";
import { api, ModelDetail, TableData } from "../api";
import { LineChart, PALETTE } from "../components/charts";
import { Badge, ErrorNote, Icon, Spinner, useAsync } from "../components/ui";
import { go } from "../router";

function to2d(t: TableData): number[][] {
  return t.shape.length === 1 ? (t.values as number[]).map((v) => [v]) : (t.values as number[][]);
}

function fmtCell(v: number): string {
  if (!isFinite(v)) return "";
  const a = Math.abs(v);
  if (a === 0) return "0";
  if (a < 1e-3) return v.toExponential(4);
  return String(+v.toPrecision(6));
}

export function Assumptions({ model, selected, onChanged }: { model: ModelDetail; selected?: string; onChanged: () => void }) {
  const name = selected && model.tables.some((t) => t.name === selected) ? selected : model.tables[0].name;
  const [table, err, reload] = useAsync<TableData>(() => api.table(model.id, name), [model.id, name]);
  const [grid, setGrid] = useState<number[][] | null>(null);
  const [orig, setOrig] = useState<number[][] | null>(null);
  const [adjust, setAdjust] = useState("10");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [logY, setLogY] = useState(false);

  useEffect(() => {
    if (table) {
      const g = to2d(table);
      setGrid(g.map((r) => [...r]));
      setOrig(g.map((r) => [...r]));
      setMsg(null);
      setLogY(/mort/.test(table.name));
    }
  }, [table]);

  const dirty = useMemo(() => !!grid && !!orig && grid.some((r, i) => r.some((v, j) => v !== orig[i][j])), [grid, orig]);
  const info = model.tables.find((t) => t.name === name)!;

  async function save() {
    if (!table || !grid) return;
    setSaving(true);
    try {
      const values = table.shape.length === 1 ? grid.map((r) => r[0]) : grid;
      await api.saveTable(model.id, name, values);
      reload(); onChanged();
      setMsg("Saved. The next run uses your values.");
    } catch (e: any) { setMsg(String(e.message || e)); }
    finally { setSaving(false); }
  }
  async function resetAll() {
    await api.resetTables(model.id);
    reload(); onChanged();
    setMsg("All tables restored to the model’s original values.");
  }

  const chart = useMemo(() => {
    if (!table || !grid) return null;
    const d0 = table.dims[0], d1 = table.dims[1];
    if (table.shape.length === 1) {
      return { labels: d0.labels, series: [{ key: "v", label: table.name, values: grid.map((r) => r[0]), color: PALETTE[0] }], xTitle: d0.kind === "range" ? "key" : "" };
    }
    // Plot along the longer dimension, one line per entry of the shorter one.
    if (d1.labels.length <= d0.labels.length) {
      return { labels: d0.labels, xTitle: "", series: d1.labels.slice(0, 8).map((l, j) => ({ key: l, label: `${l}`, values: grid.map((r) => r[j]), color: PALETTE[j % PALETTE.length] })) };
    }
    return { labels: d1.labels, xTitle: "", series: d0.labels.slice(0, 8).map((l, i) => ({ key: l, label: `${l}`, values: grid[i], color: PALETTE[i % PALETTE.length] })) };
  }, [table, grid]);

  return (
    <div className="split">
      <div className="card">
        <div className="card-head"><h3>Tables</h3>
          {model.modified_tables.length > 0 && <button className="btn small" onClick={resetAll}><Icon name="reset" size={14} /> Restore all</button>}
        </div>
        <div>
          {model.tables.map((t) => (
            <button key={t.name} className="list-item" aria-current={t.name === name} onClick={() => go(model.id, "assumptions", { t: t.name })}>
              <span className="stack" style={{ gap: 1, textAlign: "left", minWidth: 0 }}>
                <span className="li-name">{t.name}</span>
                <span className="faint" style={{ fontSize: 11.5 }}>{t.shape.join(" × ")} values</span>
              </span>
              {t.modified ? <Badge tone="warn">edited</Badge> : !t.editable ? <span className="faint"><Icon name="lock" size={14} /></span> : null}
            </button>
          ))}
        </div>
      </div>

      <div className="grid" style={{ gap: 16 }}>
        {err && <ErrorNote error={err} />}
        {!table || !grid ? <div className="row"><Spinner /><span className="muted">Loading table…</span></div> : (
          <>
            <div className="card card-body stack" style={{ gap: 12 }}>
              <div className="spread">
                <div className="row"><h2 className="mono">{table.name}</h2>
                  {table.modified ? <Badge tone="warn">edited</Badge> : <Badge>original</Badge>}
                  {!info.editable && <Badge><Icon name="lock" size={12} /> fixed by the model</Badge>}
                </div>
                {logY !== null && table.shape.length > 0 && (
                  <label className="row faint" style={{ gap: 6, fontSize: 12.5 }}>
                    <input type="checkbox" checked={logY} onChange={(e) => setLogY(e.target.checked)} /> log scale
                  </label>
                )}
              </div>
              <p className="muted">{table.description}</p>
              <div className="faint" style={{ fontSize: 12.5 }}>
                Keys: {table.dims.map((d, i) => <span key={i}>{i > 0 && " × "}{d.kind === "range" ? `${d.labels[0]}–${d.labels[d.labels.length - 1]}` : d.labels.join(", ")}</span>)}
                {table.fill === null ? " · keys beyond the table use the nearest row" : ` · keys outside the table give ${table.fill}`}
              </div>
              {chart && <LineChart series={chart.series} xLabels={chart.labels} xTitle={chart.xTitle} height={250} logY={logY && chart.series.every((s) => s.values.every((v) => v > 0))} />}
              {chart && chart.series.length > 1 && (
                <div className="legend">{chart.series.map((s) => <span key={s.key} className="badge"><span className="sw" style={{ width: 9, height: 9, borderRadius: 9, background: s.color }} />{s.label}</span>)}</div>
              )}
            </div>

            {info.editable && (
              <div className="card card-body spread">
                <div className="row">
                  <span className="muted">Adjust every value by</span>
                  <input className="input mono" style={{ width: 80, textAlign: "right" }} value={adjust} onChange={(e) => setAdjust(e.target.value)} aria-label="Percentage change" />
                  <span className="muted">%</span>
                  <button className="btn" onClick={() => {
                    const f = 1 + (parseFloat(adjust) || 0) / 100;
                    setGrid(grid.map((r) => r.map((v) => Math.min(v * f, /mort|lapse|rate|charge|spot/.test(name) ? 1 : Infinity))));
                  }}>Apply</button>
                </div>
                <div className="row">
                  {dirty && <button className="btn ghost" onClick={() => setGrid(orig!.map((r) => [...r]))}>Discard changes</button>}
                  <button className="btn primary" disabled={!dirty || saving} onClick={save}>{saving ? "Saving…" : "Save for next run"}</button>
                </div>
              </div>
            )}
            {msg && <div className="callout info"><Icon name="info" /><div>{msg} {msg.startsWith("Saved") && <button className="btn small" onClick={() => go(model.id, "run", { autorun: 1 })}><Icon name="play" size={13} /> Run now</button>}</div></div>}
            {table.modified && !dirty && !msg && (
              <div className="callout"><Icon name="alert" /><div>This table has been edited. Runs use the edited values until you restore it.
                <button className="btn small" style={{ marginLeft: 8 }} onClick={resetAll}>Restore original</button></div></div>
            )}

            <div className="card">
              <div className="tbl-wrap" style={{ maxHeight: 460 }}>
                <table className="tbl">
                  <thead><tr>
                    <th>{table.dims[0].kind === "range" ? "Key" : "Category"}</th>
                    {table.shape.length === 1 ? <th className="r">Value</th> : table.dims[1].labels.map((l) => <th key={l} className="r">{l}</th>)}
                  </tr></thead>
                  <tbody>
                    {grid.map((r, i) => (
                      <tr key={i}>
                        <td className="mono faint">{table.dims[0].labels[i]}</td>
                        {r.map((v, j) => (
                          <td key={j} className={`r ${orig && v !== orig[i][j] ? "edited" : ""}`} style={{ minWidth: 92 }}>
                            {info.editable ? (
                              <input className="cell-input" defaultValue={fmtCell(v)} key={`${i}-${j}-${v}`}
                                aria-label={`${table.dims[0].labels[i]}, column ${j + 1}`}
                                onBlur={(e) => {
                                  const nv = parseFloat(e.target.value);
                                  if (isFinite(nv) && nv !== v) setGrid(grid.map((row, ii) => row.map((x, jj) => (ii === i && jj === j ? nv : x))));
                                  else e.target.value = fmtCell(v);
                                }}
                                onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }} />
                            ) : <span className="mono">{fmtCell(v)}</span>}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
