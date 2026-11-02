// Typed access to the local Meridian service.

export interface Kpi { label: string; value: number; unit: string; note: string; format: "number" | "percent" }
export interface ModelSummary {
  id: string; name: string; tagline: string; source: string; policies: number; rows: number; steps: number;
  variables: number; lives: number; modified_tables: string[]; last_run: RunBrief | null;
  data_source: DataSource | null; modified_formulas: string[];
}
export interface DataSource { name: string; rows: number; at: number }
export interface Lever { key: string; label: string; kind: "scale" | "shift"; min: number; max: number; step: number; unit: "%" | "pp"; help: string }
export interface SchemaField { key: string; label: string; kind: "number" | "integer" | "text"; description: string; choices: string[] | null; min: number | null; max: number | null }
export interface ImportReport {
  ok: boolean; fatal?: string; rows?: number; delimiter?: string; headers?: string[];
  matched?: { key: string; label: string; column: string }[];
  missing?: { key: string; label: string; description: string }[]; unused?: string[];
  errors?: { row: number; column: string; value: string; message: string }[];
  error_count?: number; error_summary?: Record<string, number>; preview?: Record<string, string>[]; applied?: boolean;
}
export interface Settings { theme: string | null; tour_done: boolean }
export interface VariableSpec {
  name: string; formula: string; doc: string; init: number; refs: [string, number][]; inputs: string[];
  used_by: [string, number][]; cls: "C1" | "C2"; total: boolean; pv: boolean; tables: string[];
  edited: boolean; original: string | null;
}
export interface PreviewSeries { name: string; before: (number | null)[]; after: (number | null)[]; changed: number; invalid_from: number | null }
export interface FormulaCheck {
  ok: boolean; error?: string; col?: number | null; formula?: string; cls?: string; unchanged?: boolean;
  refs?: [string, number][]; inputs?: string[]; tables?: string[];
  preview?: { label?: string; series?: PreviewSeries[]; error?: string };
}
export interface TableInfo { name: string; description: string; editable: boolean; shape: number[]; modified: boolean }
export interface DataColumn { key: string; label: string; kind?: "id" | "money" }
export interface RunOption { key: string; label: string; kind: "choice"; choices: [number, string][]; default: number }
export interface ModelDetail extends ModelSummary {
  description: string; currency: string; variables_spec: VariableSpec[]; tables: TableInfo[];
  data_columns: DataColumn[]; run_options: RunOption[];
  levers: Lever[]; sensitivities: { levers: Record<string, number> }[]; input_schema: SchemaField[];
  formula_names: { inputs: string[]; tables: string[]; scenarios: string[]; functions: string[] };
}
export interface TableDim { kind: "range" | "categories"; start?: number; labels: string[] }
export interface TableData {
  name: string; description: string; shape: number[]; dims: TableDim[]; values: any; fill: number | null;
  editable: boolean; modified: boolean;
}
export interface RunBrief {
  id: string; model: string; label: string; status: "queued" | "running" | "done" | "failed"; progress: number;
  message: string; started: number; finished: number | null; seconds: number | null; error: string | null;
  kpis: Kpi[] | null; modified_tables: string[];
  levers: Record<string, number>; group: string | null; data: string | null;
  modified_formulas?: string[]; restored?: boolean;
}
export interface Series { values: number[]; label: string }
export interface RunResult {
  kpis: Kpi[]; pv_table: { label: string; value: number; share: number }[];
  series: Record<string, Series>; series_unit: string; seconds: number; policies: number;
  scenarios?: number[];
  sam?: { bel: Record<string, number>; scr: Record<string, number>; risk_margin: number; tp: number;
          labels: Record<string, string>; projected_scr: number[] };
}
export interface RunFull extends RunBrief { result: RunResult | null }
export interface DataPage { total: number; offset: number; rows: Record<string, any>[] }
export interface ColumnStats {
  key: string; label: string; kind: "text" | "number"; top?: [string, number][];
  min?: number; max?: number; mean?: number; hist?: number[]; edges?: number[];
}
export interface ExplainData {
  label: string; inputs: Record<string, number | string>; steps: number; values: Record<string, (number | null)[]>;
  family?: { row: number; label: string }[];
}
export interface Check { name: string; detail: string; metric: string; passed: boolean }
export interface ValidationSuite {
  title: string; reference: string; checks: Check[];
  sample: { policy: string | number; meridian: number; reference: number }[]; sample_label: string;
}
export interface ValidationState { status: "not_started" | "running" | "done" | "failed"; result: ValidationSuite[] | null; error: string | null; seconds: number | null }

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...init });
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`;
    try { msg = (await r.json()).detail ?? msg; } catch { /* keep status text */ }
    throw new Error(msg);
  }
  return r.json() as Promise<T>;
}

export const api = {
  workspace: () => req<ModelSummary[]>("/api/workspace"),
  model: (id: string) => req<ModelDetail>(`/api/models/${id}`),
  table: (id: string, name: string) => req<TableData>(`/api/models/${id}/tables/${name}`),
  saveTable: (id: string, name: string, values: any) =>
    req<TableData>(`/api/models/${id}/tables/${name}`, { method: "PUT", body: JSON.stringify({ values }) }),
  resetTables: (id: string) => req<{ ok: boolean }>(`/api/models/${id}/tables/reset`, { method: "POST" }),
  data: (id: string, offset: number, limit: number, search: string) =>
    req<DataPage>(`/api/models/${id}/data?offset=${offset}&limit=${limit}&search=${encodeURIComponent(search)}`),
  dataStats: (id: string) => req<ColumnStats[]>(`/api/models/${id}/data/stats`),
  explain: (id: string, policy: number) => req<ExplainData>(`/api/models/${id}/explain?policy=${policy}`),
  startRun: (id: string, options: Record<string, any>, label?: string, group?: string) =>
    req<RunBrief>(`/api/models/${id}/runs`, { method: "POST", body: JSON.stringify({ options, label, group }) }),
  importData: (id: string, csv: string, name: string, apply = false) =>
    req<ImportReport>(`/api/models/${id}/data/import`, { method: "POST", body: JSON.stringify({ csv, name, apply }) }),
  resetData: (id: string) => req<{ ok: boolean }>(`/api/models/${id}/data/reset`, { method: "POST" }),
  checkFormula: (id: string, name: string, formula: string) =>
    req<FormulaCheck>(`/api/models/${id}/formulas/${name}/check`, { method: "POST", body: JSON.stringify({ formula }) }),
  saveFormula: (id: string, name: string, formula: string) =>
    req<ModelDetail>(`/api/models/${id}/formulas/${name}`, { method: "PUT", body: JSON.stringify({ formula }) }),
  revertFormula: (id: string, name: string) => req<ModelDetail>(`/api/models/${id}/formulas/${name}`, { method: "DELETE" }),
  resetFormulas: (id: string) => req<{ ok: boolean }>(`/api/models/${id}/formulas/reset`, { method: "POST" }),
  deleteRun: (rid: string) => req<{ ok: boolean }>(`/api/runs/${rid}`, { method: "DELETE" }),
  notices: () => req<string[]>("/api/notices"),
  settings: () => req<Settings>("/api/settings"),
  saveSettings: (s: Partial<Settings>) => req<Settings>("/api/settings", { method: "PUT", body: JSON.stringify(s) }),
  runs: (id: string) => req<RunBrief[]>(`/api/models/${id}/runs`),
  run: (rid: string, full = true) => req<RunFull>(`/api/runs/${rid}?full=${full}`),
  startValidation: (id: string) => req<ValidationState>(`/api/models/${id}/validation`, { method: "POST" }),
  validation: (id: string) => req<ValidationState>(`/api/models/${id}/validation`),
};
