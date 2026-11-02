import { useEffect, useState } from "react";
import { api, ModelSummary } from "./api";
import { Icon, Logo, useAsync } from "./components/ui";
import { ModelPage } from "./pages/ModelPage";
import { Workspace } from "./pages/Workspace";
import { go, useRoute } from "./router";

export const MODEL_ICON: Record<string, string> = { term: "term", savings: "savings", funeral: "family" };

function useTheme(): [string, () => void] {
  const [theme, setTheme] = useState<string>(() => {
    try { return localStorage.getItem("meridian-theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"); }
    catch { return "light"; }
  });
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("meridian-theme", theme); } catch { /* private mode */ }
  }, [theme]);
  return [theme, () => setTheme((t) => (t === "dark" ? "light" : "dark"))];
}

export default function App() {
  const route = useRoute();
  const [theme, toggle] = useTheme();
  const [models, err, reload] = useAsync<ModelSummary[]>(() => api.workspace(), []);
  useEffect(() => { reload(); }, [route.model, route.section, reload]);

  return (
    <div className="shell">
      <aside className="rail">
        <div className="brand">
          <Logo />
          <div><div className="brand-name">Meridian</div><div className="brand-sub">Actuarial modelling</div></div>
        </div>
        <nav aria-label="Main">
          <button className="nav-item" aria-current={route.model === null ? "page" : undefined} onClick={() => go(null)}>
            <Icon name="home" /><span className="label">Workspace</span>
          </button>
          <div className="group eyebrow">Models</div>
          {(models || []).map((m) => (
            <button key={m.id} className="nav-item" aria-current={route.model === m.id ? "page" : undefined}
              onClick={() => go(m.id, route.model === m.id ? route.section : "overview")}>
              <Icon name={MODEL_ICON[m.id] || "formula"} />
              <span className="label">{m.name}</span>
              {m.modified_tables.length > 0 && <span className="badge warn" title="Assumptions edited">edited</span>}
            </button>
          ))}
          {err && <div className="faint" style={{ padding: 10 }}>Could not reach the Meridian service.</div>}
        </nav>
        <div className="rail-foot">
          <span className="faint" style={{ fontSize: 12 }}>Prototype · v0.1</span>
          <button className="icon-btn" onClick={toggle} title={theme === "dark" ? "Light theme" : "Dark theme"} aria-label="Switch theme">
            <Icon name={theme === "dark" ? "sun" : "moon"} />
          </button>
        </div>
      </aside>
      <main className="main" id="main">
        {route.model === null
          ? <Workspace models={models} error={err} />
          : <ModelPage key={route.model} modelId={route.model} section={route.section} params={route.params} onChanged={reload} />}
      </main>
    </div>
  );
}
