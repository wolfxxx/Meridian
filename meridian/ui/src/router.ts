import { useEffect, useState } from "react";

// Hash routes: #/  ·  #/m/<model>/<section>[?key=value...]
export interface Route { model: string | null; section: string; params: Record<string, string> }

export function parse(hash: string): Route {
  const [path, query = ""] = hash.replace(/^#\/?/, "").split("?");
  const parts = path.split("/").filter(Boolean);
  const params: Record<string, string> = {};
  new URLSearchParams(query).forEach((v, k) => (params[k] = v));
  if (parts[0] === "m" && parts[1]) return { model: parts[1], section: parts[2] || "overview", params };
  return { model: null, section: "workspace", params };
}

export function href(model: string | null, section = "overview", params: Record<string, string | number> = {}): string {
  if (!model) return "#/";
  const q = new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString();
  return `#/m/${model}/${section}${q ? "?" + q : ""}`;
}

export function go(model: string | null, section = "overview", params: Record<string, string | number> = {}) {
  window.location.hash = href(model, section, params);
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parse(window.location.hash));
  useEffect(() => {
    const on = () => setRoute(parse(window.location.hash));
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}
