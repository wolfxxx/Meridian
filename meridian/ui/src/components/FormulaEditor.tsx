import { useEffect, useRef, useState } from "react";
import { api, FormulaCheck, ModelDetail, VariableSpec } from "../api";
import { LineChart } from "./charts";
import { Icon, Segmented, Spinner } from "./ui";

const FUNCTION_HELP: Record<string, string> = {
  where: "where(condition, if true, if false)", min: "min(a, b)", max: "max(a, b)", clip: "clip(x, low, high)",
  abs: "abs(x)", floor: "floor(x)", exp: "exp(x)", ln: "ln(x), natural log", sqrt: "sqrt(x)",
  sum_lives: "sum_lives(x): total over the policy's lives", sum_policies: "sum_policies(x): total over all policies",
  t: "t: the projection month, from 0", life: "life: the life's slot in its policy",
};

/** Edit one variable's formula with live checking, an insert palette and a before/after preview. */
export function FormulaEditor({ model, v, onSaved, onCancel }:
  { model: ModelDetail; v: VariableSpec; onSaved: (d: ModelDetail) => void; onCancel: () => void }) {
  const [text, setText] = useState(v.formula);
  const [check, setCheck] = useState<FormulaCheck | null>(null);
  const [checking, setChecking] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"vars" | "inputs" | "tables" | "functions">("vars");
  const [find, setFind] = useState("");
  const box = useRef<HTMLTextAreaElement>(null);
  const seq = useRef(0);

  useEffect(() => {
    const id = ++seq.current;
    setChecking(true);
    const timer = setTimeout(() => {
      api.checkFormula(model.id, v.name, text)
        .then((r) => { if (id === seq.current) setCheck(r); })
        .catch((e) => { if (id === seq.current) setCheck({ ok: false, error: String(e.message || e) }); })
        .finally(() => { if (id === seq.current) setChecking(false); });
    }, 450);
    return () => clearTimeout(timer);
  }, [text, model.id, v.name]);

  useEffect(() => { box.current?.focus(); }, []);
  useEffect(() => {  // grow with the text
    const el = box.current;
    if (el) { el.style.height = "auto"; el.style.height = `${Math.max(84, el.scrollHeight + 2)}px`; }
  }, [text]);

  function insert(s: string, back = 0) {
    const el = box.current;
    if (!el) return setText(text + s);
    const a = el.selectionStart, b = el.selectionEnd;
    const next = text.slice(0, a) + s + text.slice(b);
    setText(next);
    requestAnimationFrame(() => { el.focus(); const p = a + s.length - back; el.setSelectionRange(p, p); });
  }

  async function save() {
    if (!check?.ok || check.unchanged && !v.edited) return;
    setSaving(true); setError(null);
    try { onSaved(await api.saveFormula(model.id, v.name, text)); }
    catch (e: any) { setError(String(e.message || e)); }
    finally { setSaving(false); }
  }

  const names = model.formula_names;
  const q = find.toLowerCase();
  const pool: { label: string; ins: string; back?: number; title?: string; cls?: string }[] =
    tab === "vars" ? model.variables_spec.filter((x) => x.name !== v.name).map((x) => ({ label: x.name, ins: x.name, title: x.doc }))
      : tab === "inputs" ? [...names.inputs.map((n) => ({ label: `mp.${n}`, ins: `mp.${n}`, cls: "inp" })),
          ...names.scenarios.map((n) => ({ label: `scen.${n}`, ins: `scen.${n}`, cls: "inp" }))]
      : tab === "tables" ? names.tables.map((n) => ({ label: n, ins: `${n}[]`, back: 1, cls: "tbl" }))
      : names.functions.map((n) => ["t", "life"].includes(n) ? { label: n, ins: n, title: FUNCTION_HELP[n] }
          : { label: `${n}( )`, ins: `${n}()`, back: 1, title: FUNCTION_HELP[n] });
  const shown = pool.filter((p) => !q || p.label.toLowerCase().includes(q));

  const status = checking && !check ? <span className="row faint"><Spinner /> Checking…</span>
    : !check ? null
    : check.ok
      ? <span className="row" style={{ color: "var(--good)", gap: 6 }}><Icon name="check" size={16} />
          {check.unchanged ? "Same as the current formula" : "The formula is valid"}
          {checking && <Spinner />}</span>
      : <span className="row" style={{ color: "var(--bad)", gap: 6, alignItems: "flex-start" }}><Icon name="alert" size={16} />
          <span>{check.error}</span></span>;

  return (
    <div className="stack" style={{ gap: 12 }}>
      <div className="code-wrap">
        <span className="code-lhs mono">{v.name} =</span>
        <textarea ref={box} className="code" value={text} spellCheck={false} aria-label={`Formula for ${v.name}`}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); save(); }
            if (e.key === "Escape") onCancel();
          }} />
        {check && !check.ok && check.col !== null && check.col !== undefined && <ErrorSpot text={text} col={check.col} />}
      </div>
      <div className="spread">
        {status}
        <div className="row">
          <span className="faint" style={{ fontSize: 12 }}><span className="kbd">Ctrl</span> + <span className="kbd">Enter</span> saves · <span className="kbd">Esc</span> cancels</span>
          <button className="btn" onClick={onCancel}>Cancel</button>
          <button className="btn primary" onClick={save} disabled={!check?.ok || saving || (check.unchanged && !v.edited)}>
            {saving ? <Spinner /> : <Icon name="check" size={15} />} Save formula
          </button>
        </div>
      </div>
      {error && <div className="callout"><Icon name="alert" /><span>{error}</span></div>}

      <div className="card" style={{ boxShadow: "none" }}>
        <div className="card-head" style={{ padding: "8px 12px" }}>
          <Segmented label="Insert" value={tab} onChange={setTab}
            options={[["vars", "Variables"], ["inputs", "Policy data"], ["tables", "Tables"], ["functions", "Functions"]]} />
          <div className="search" style={{ width: 200 }}><Icon name="search" size={14} />
            <input value={find} onChange={(e) => setFind(e.target.value)} placeholder="Filter" aria-label="Filter names" /></div>
        </div>
        <div className="chips" style={{ padding: 12, maxHeight: 132, overflowY: "auto" }}>
          {shown.map((p) => (
            <button key={p.label} className="chip" title={p.title || `Insert ${p.ins}`} onClick={() => insert(p.ins, p.back)}
              style={p.cls === "inp" ? { color: "var(--ref)" } : p.cls === "tbl" ? { color: "var(--c5)" } : undefined}>{p.label}</button>
          ))}
          {!shown.length && <span className="faint">Nothing matches.</span>}
        </div>
      </div>

      {check?.ok && check.preview && <Preview check={check} />}
    </div>
  );
}

function ErrorSpot({ text, col }: { text: string; col: number }) {
  const flat = text.replace(/\s/g, " ");
  const c = Math.min(col, flat.length);
  const a = Math.max(0, c - 40);
  const pre = (a > 0 ? "…" : "") + flat.slice(a, c);
  const post = flat.slice(c, c + 40) + (c + 40 < flat.length ? "…" : "");
  return <pre className="caret mono" aria-label={`Problem at character ${c + 1}`}>{pre}<mark>{post.charAt(0) || " "}</mark>{post.slice(1)}{"\n"}{" ".repeat(pre.length)}^</pre>;
}

function Preview({ check }: { check: FormulaCheck }) {
  const p = check.preview!;
  if (p.error) return <div className="callout"><Icon name="alert" /><span>{p.error}</span></div>;
  return (
    <div className="stack" style={{ gap: 8 }}>
      <div className="spread">
        <h3>Preview</h3>
        <span className="faint" style={{ fontSize: 12.5 }}>{p.label}</span>
      </div>
      <div className="grid">
        {(p.series || []).map((s) => (
          <div key={s.name} className="card card-body stack" style={{ gap: 6, boxShadow: "none" }}>
            <div className="spread">
              <strong className="mono" style={{ fontSize: 13 }}>{s.name}</strong>
              <span className="faint" style={{ fontSize: 12 }}>
                {s.changed ? `changes in ${s.changed} of ${s.after.length} months` : "no change"}</span>
            </div>
            {s.invalid_from !== null && (
              <div className="callout" style={{ fontSize: 12.5 }}><Icon name="alert" size={16} />
                <span>Not a number from month {s.invalid_from} (for example a division by zero).</span></div>
            )}
            <LineChart height={190} series={[
              { key: "b", label: "Before", values: s.before, color: "var(--c2)", dashed: true },
              { key: "a", label: "After", values: s.after, color: "var(--c1)" }]} />
          </div>
        ))}
      </div>
      <span className="faint" style={{ fontSize: 12 }}>Dashed: the current formula. Solid: your edit. Save, then run the model to see the effect on the whole portfolio.</span>
    </div>
  );
}
