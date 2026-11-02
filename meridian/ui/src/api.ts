// Typed access to the local Meridian service.

export interface Kpi { label: string; value: number; unit: string; note: string; format: "number" | "percent" }
export interface ModelSummary {
  id: string; name: string; tagline: string; source: string; policies: number; rows: number; steps: number;
  variables: number; lives: number; modified_tables: string[]; last_run: RunBrief | null;
}
export interface VariableSpec {
  name: string; formula: string; doc: string; init: number; refs: [string, number][]; inputs: string[];
  used_by: [string, number][]; cls: "C1" | "C2"; total: boolean; pv: boolean; tables: string[];
}
export interface TableInfo { name: string; description: string; editable: boolean; shape: number[]; modified: boolean }
export interface DataColumn { key: string; label: string; kind?: "id" | "money" }
export interface RunOption { key: string; label: string; kind: "choice"; choices: [number, string][]; default: number }
export interface ModelDetail extends ModelSummary {
  description: string; currency: string; variables_spec: VariableSpec[]; tables: TableInfo[];
  data_columns: DataColumn[]; run_options: RunOption[];
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
  startRun: (id: string, options: Record<string, number>, label?: string) =>
    req<RunBrief>(`/api/models/${id}/runs`, { method: "POST", body: JSON.stringify({ options, label }) }),
  runs: (id: string) => req<RunBrief[]>(`/api/models/${id}/runs`),
  run: (rid: string, full = true) => req<RunFull>(`/api/runs/${rid}?full=${full}`),
  startValidation: (id: string) => req<ValidationState>(`/api/models/${id}/validation`, { method: "POST" }),
  validation: (id: string) => req<ValidationState>(`/api/models/${id}/validation`),
};
