import { ReactNode } from "react";

const KEYWORDS = new Set(["where", "min", "max", "floor", "exp", "ln", "sqrt", "abs", "sum_policies", "sum_lives", "life", "t"]);

/** A formula with variable names as clickable links, inputs and tables coloured. */
export function Formula({ text, isVar, onVar, tables = [] }:
  { text: string; isVar: (name: string) => boolean; onVar?: (name: string, lag: number) => void; tables?: string[] }) {
  const re = /mp\.[A-Za-z_]\w*|scen\.[A-Za-z_]\w*|[A-Za-z_]\w*(\[t-\d+\])?|'[^']*'|[^A-Za-z_']+/g;
  const parts: ReactNode[] = [];
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(text)) !== null) {
    const tok = m[0];
    const key = i++;
    if (/^(mp|scen)\./.test(tok)) { parts.push(<span key={key} className="inp" title={tok.startsWith("mp.") ? "Policy data" : "Scenario input"}>{tok}</span>); continue; }
    if (tok.startsWith("'")) { parts.push(<span key={key} className="str">{tok}</span>); continue; }
    const lagm = tok.match(/^([A-Za-z_]\w*)\[t-(\d+)\]$/);
    const base = lagm ? lagm[1] : tok, lag = lagm ? +lagm[2] : 0;
    if (isVar(base)) {
      parts.push(onVar
        ? <button key={key} type="button" className="ref" onClick={() => onVar(base, lag)} title={`Go to ${base}${lag ? ` (${lag} month${lag > 1 ? "s" : ""} earlier)` : ""}`}>{tok}</button>
        : <span key={key} className="ref">{tok}</span>);
    } else if (tables.includes(tok)) parts.push(<span key={key} className="tbl-ref" title="Assumption table">{tok}</span>);
    else if (KEYWORDS.has(tok)) parts.push(<span key={key} className="kw">{tok}</span>);
    else parts.push(tok);
  }
  return <div className="formula">{parts}</div>;
}
