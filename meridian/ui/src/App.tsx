import { useEffect, useState } from "react";
import { api, ModelSummary } from "./api";
import { Tour, Welcome } from "./components/Tour";
import { Icon, Logo, useAsync } from "./components/ui";
import { ModelPage } from "./pages/ModelPage";
import { Workspace } from "./pages/Workspace";
import { go, useRoute } from "./router";

export const MODEL_ICON: Record<string, string> = { term: "term", savings: "savings", funeral: "family" };

// The theme is kept in the user's settings file: the app's address (port) changes on every
// start, so browser storage would forget it.
function useTheme(saved: string | null | undefined): [string, () => void] {
  const [theme, setTheme] = useState<string>(() => {
    try { return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"; } catch { return "light"; }
  });
  useEffect(() => { if (saved) setTheme(saved); }, [saved]);
  useEffect(() => { document.documentElement.setAttribute("data-theme", theme); }, [theme]);
  return [theme, () => setTheme((t) => {
    const next = t === "dark" ? "light" : "dark";
    api.saveSettings({ theme: next }).catch(() => undefined);
    return next;
  })];
}

export default function App() {
  const route = useRoute();
  const [settings] = useAsync(() => api.settings(), []);
  const [theme, toggle] = useTheme(settings?.theme);
  const [tour, setTour] = useState<"off" | "welcome" | "on">("off");
  useEffect(() => { if (settings && !settings.tour_done) setTour("welcome"); }, [settings]);
  const [notices, setNotices] = useState<string[]>([]);
  useEffect(() => { api.notices().then(setNotices).catch(() => undefined); }, []);
  const endWelcome = (next: "off" | "on") => { setTour(next); api.saveSettings({ tour_done: true }).catch(() => undefined); };
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
              {(m.modified_tables.length > 0 || m.modified_formulas.length > 0) && <span className="badge warn" title="Assumptions or formulas edited">edited</span>}
            </button>
          ))}
          {err && <div className="faint" style={{ padding: 10 }}>Could not reach the Meridian service.</div>}
        </nav>
        <div className="rail-foot">
          <span className="faint" style={{ fontSize: 12 }}>Prototype · v0.3</span>
          <span className="row" style={{ gap: 2 }}>
          <button className="icon-btn" onClick={() => setTour("on")} title="Take the tour" aria-label="Take the tour" data-tour="help">
            <Icon name="help" />
          </button>
          <button className="icon-btn" onClick={toggle} title={theme === "dark" ? "Light theme" : "Dark theme"} aria-label="Switch theme">
            <Icon name={theme === "dark" ? "sun" : "moon"} />
          </button>
          </span>
        </div>
      </aside>
      <main className="main" id="main">
        {notices.length > 0 && (
          <div className="callout" style={{ margin: "16px 32px 0" }} role="status">
            <Icon name="alert" />
            <div className="stack" style={{ gap: 4, flex: 1 }}>{notices.map((n) => <span key={n}>{n}</span>)}</div>
            <button className="icon-btn" onClick={() => setNotices([])} aria-label="Dismiss"><Icon name="close" size={16} /></button>
          </div>
        )}
        {route.model === null
          ? <Workspace models={models} error={err} />
          : <ModelPage key={route.model} modelId={route.model} section={route.section} params={route.params} onChanged={reload} />}
      </main>
      {tour === "welcome" && <Welcome onTour={() => endWelcome("on")} onSkip={() => endWelcome("off")} />}
      {tour === "on" && <Tour onEnd={() => setTour("off")} />}
    </div>
  );
}
