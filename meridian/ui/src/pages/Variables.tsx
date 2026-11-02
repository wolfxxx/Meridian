import { useMemo, useState } from "react";
import { ModelDetail, VariableSpec } from "../api";
import { Formula } from "../components/Formula";
import { Badge, Icon, Segmented } from "../components/ui";
import { go } from "../router";

export function kindOf(v: VariableSpec): [string, string] {
  if (v.cls === "C2") return ["company-level", "warn"];
  if (/sum_lives/.test(v.formula)) return ["policy-level", "accent"];
  if (v.pv) return ["present value", "good"];
  if (v.total) return ["reported total", ""];
  return ["", ""];
}

function DepGraph({ v, byName, onPick }: { v: VariableSpec; byName: Record<string, VariableSpec>; onPick: (n: string) => void }) {
  const left = [...v.refs.map(([n, lag]) => ({ n, sub: lag ? `t−${lag}` : "", kind: "var" })),
    ...v.inputs.map((n) => ({ n: `mp.${n}`, sub: "policy data", kind: "inp" })),
    ...v.tables.map((n) => ({ n, sub: "table", kind: "tbl" }))];
  const right = v.used_by.map(([n, lag]) => ({ n, sub: lag ? `t−${lag}` : "", kind: "var" }));
  const rowH = 34, W = 760, colW = 210, H = Math.max(left.length, right.length, 1) * rowH + 20;
  const cx = W / 2, cy = H / 2;
  const y = (i: number, n: number) => H / 2 + (i - (n - 1) / 2) * rowH;
  const node = (label: string, sub: string, x: number, yy: number, cls: string, onClick?: () => void, key?: string) => (
    <g key={key || label} className={`node ${cls}`} transform={`translate(${x - colW / 2}, ${yy - 13})`}
      style={{ cursor: onClick ? "pointer" : "default" }} onClick={onClick}>
      <rect width={colW} height={26} rx={6} />
      <text x={10} y={17} style={{ fill: cls.includes("inp") ? "var(--ref)" : cls.includes("tbl") ? "var(--c5)" : undefined }}>{label}</text>
      {sub && <text x={colW - 8} y={17} textAnchor="end" style={{ fill: "var(--ink-3)", fontSize: 10.5 }}>{sub}</text>}
    </g>
  );
  return (
    <div className="chart depgraph">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`What ${v.name} uses and what uses it`}>
        {left.map((_, i) => <path key={"le" + i} className="edge" d={`M${colW + 20} ${y(i, left.length)} C ${cx - 60} ${y(i, left.length)}, ${cx - 160} ${cy}, ${cx - colW / 2} ${cy}`} />)}
        {right.map((_, i) => <path key={"re" + i} className="edge" d={`M${cx + colW / 2} ${cy} C ${cx + 160} ${cy}, ${cx + 60} ${y(i, right.length)}, ${W - colW - 20} ${y(i, right.length)}`} />)}
        {left.map((d, i) => node(d.n, d.sub, colW / 2 + 20, y(i, left.length), d.kind === "var" ? "" : d.kind,
          d.kind === "var" && byName[d.n] ? () => onPick(d.n) : undefined, "l" + i))}
        {node(v.name, "", cx, cy, "center")}
        {right.map((d, i) => node(d.n, d.sub, W - colW / 2 - 20, y(i, right.length), "", () => onPick(d.n), "r" + i))}
        {left.length === 0 && <text x={colW / 2 + 20} y={cy + 4} textAnchor="middle">time and constants only</text>}
        {right.length === 0 && <text x={W - colW / 2 - 20} y={cy + 4} textAnchor="middle">reported result</text>}
      </svg>
    </div>
  );
}

export function Variables({ model, selected }: { model: ModelDetail; selected?: string }) {
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<string>("all");
  const vars = model.variables_spec;
  const byName = useMemo(() => Object.fromEntries(vars.map((v) => [v.name, v])), [vars]);
  const cur = byName[selected || ""] || vars[0];
  const pick = (n: string) => go(model.id, "variables", { v: n });
  const shown = vars.filter((v) => {
    if (q && !v.name.toLowerCase().includes(q.toLowerCase()) && !v.doc.toLowerCase().includes(q.toLowerCase())) return false;
    if (filter === "totals") return v.total;
    if (filter === "pv") return v.pv;
    if (filter === "policy") return /sum_lives/.test(v.formula) || v.cls === "C2";
    return true;
  });
  const [kind, tone] = kindOf(cur);

  return (
    <div className="split">
      <div className="card">
        <div className="card-body stack" style={{ gap: 8 }}>
          <div className="search"><Icon name="search" size={16} /><input placeholder="Find a variable" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Find a variable" /></div>
          <Segmented label="Filter variables" value={filter} onChange={setFilter}
            options={[["all", "All"], ["totals", "Totals"], ["pv", "PVs"], ...(model.lives > 1 || vars.some((v) => v.cls === "C2") ? [["policy", "Grouped"] as [string, string]] : [])]} />
          <span className="faint" style={{ fontSize: 12 }}>In calculation order · {shown.length} of {vars.length}</span>
        </div>
        <div className="listbox" style={{ borderTop: "1px solid var(--line)" }}>
          {shown.map((v) => (
            <button key={v.name} className="list-item" aria-current={v.name === cur.name} onClick={() => pick(v.name)}>
              <span className="li-name">{v.name}</span>
              <span className="faint mono" style={{ fontSize: 11 }}>{v.pv ? "PV" : v.total ? "Σ" : ""}</span>
            </button>
          ))}
        </div>
      </div>
      <div className="grid" style={{ gap: 16 }}>
        <div className="card card-body stack" style={{ gap: 14 }}>
          <div className="spread">
            <div className="row"><h2 className="mono">{cur.name}</h2>{kind && <Badge tone={tone}>{kind}</Badge>}</div>
            <button className="btn" onClick={() => go(model.id, "explain", { v: cur.name })}><Icon name="explain" size={16} /> Explain for a policy</button>
          </div>
          {cur.doc && <p className="muted" style={{ fontSize: 15 }}>{cur.doc}</p>}
          <Formula text={cur.formula} isVar={(n) => !!byName[n]} onVar={(n) => pick(n)} tables={cur.tables} />
          <div className="grid cols-2" style={{ gap: 18 }}>
            <div className="stack" style={{ gap: 6 }}>
              <span className="eyebrow">Uses</span>
              <div className="chips">
                {cur.refs.map(([n, lag]) => <button key={n + lag} className="chip" onClick={() => pick(n)}>{n}{lag ? `[t−${lag}]` : ""}</button>)}
                {cur.inputs.map((n) => <span key={n} className="chip static" style={{ color: "var(--ref)" }}>mp.{n}</span>)}
                {cur.tables.map((n) => <button key={n} className="chip" style={{ color: "var(--c5)" }} onClick={() => go(model.id, "assumptions", { t: n })}>{n}</button>)}
                {!cur.refs.length && !cur.inputs.length && !cur.tables.length && <span className="faint">Only time and constants</span>}
              </div>
            </div>
            <div className="stack" style={{ gap: 6 }}>
              <span className="eyebrow">Used by</span>
              <div className="chips">
                {cur.used_by.map(([n, lag]) => <button key={n + lag} className="chip" onClick={() => pick(n)}>{n}{lag ? ` (next month)` : ""}</button>)}
                {!cur.used_by.length && <span className="faint">Nothing — a reported result</span>}
              </div>
            </div>
          </div>
          {cur.init !== 0 && <p className="faint">Before the first month this variable is taken as {cur.init}.</p>}
        </div>
        <div className="card card-body stack">
          <h3>Where it sits</h3>
          <p className="faint" style={{ fontSize: 12.5 }}>Left: what the formula uses. Right: what uses it. Click a name to move to it.</p>
          <DepGraph v={cur} byName={byName} onPick={pick} />
        </div>
      </div>
    </div>
  );
}
