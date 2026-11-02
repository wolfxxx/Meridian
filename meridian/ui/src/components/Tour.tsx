import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Icon, Logo, Modal } from "./ui";

interface Step { route: string; target: string; title: string; body: string }

const STEPS: Step[] = [
  { route: "#/", target: '[data-tour="models"]', title: "Your models",
    body: "Three complete models, ready to run. Term assurance and a stochastic savings product rebuilt from the open-source lifelib library, and a South African family funeral product valued on a SAM basis." },
  { route: "#/", target: '[data-tour="run-funeral"]', title: "Run in one click",
    body: "Every policy is projected month by month on all your processor cores. The funeral model runs its base and six SAM stress bases in seconds." },
  { route: "#/m/funeral/overview", target: '[data-tour="tabs"]', title: "Everything about a model, in one place",
    body: "Formulas, assumptions, policy data, results, what-ifs, explanations and validation. Nothing to install, wire up or copy between files." },
  { route: "#/m/funeral/variables", target: '[data-tour="page"]', title: "Formulas you can read",
    body: "Each variable is one readable formula, like a Prophet library variable. Click a name to follow it; the graph shows what feeds what." },
  { route: "#/m/funeral/assumptions", target: '[data-tour="page"]', title: "Assumptions as tables",
    body: "Every table as a chart and an editable grid. Change a value or scale a whole table; edited tables are flagged and used by the next run." },
  { route: "#/m/funeral/whatif", target: '[data-tour="levers"]', title: "Ask what-if questions",
    body: "Move a slider and run it. Or run the standard sensitivities to see which assumption moves the result most, side by side with the base." },
  { route: "#/m/funeral/data", target: '[data-tour="import"]', title: "Bring your own data",
    body: "Import a CSV from your administration system or Excel. Meridian matches the columns, checks every row and shows a preview before anything changes." },
  { route: "#/m/funeral/explain", target: '[data-tour="page"]', title: "Explain any number",
    body: "Pick a policy and a month and trace a result back through its formulas to the inputs, the way you would audit a spreadsheet." },
  { route: "#/m/funeral/validation", target: '[data-tour="page"]', title: "Evidence, not claims",
    body: "Each model is checked against an independent implementation: lifelib for term and savings, a separate loop-by-loop calculation for funeral. Run the checks yourself." },
  { route: "#/", target: '[data-tour="help"]', title: "That’s the tour",
    body: "Open it again any time from this button. A good first step: run the funeral model, then open its What-if tab." },
];

/** Welcome dialog shown on the very first start. */
export function Welcome({ onTour, onSkip }: { onTour: () => void; onSkip: () => void }) {
  return (
    <Modal title="Welcome to Meridian" onClose={onSkip} width={560}
      footer={<>
        <button className="btn ghost" onClick={onSkip}>Explore on my own</button>
        <button className="btn primary" onClick={onTour}>Take the tour <span className="faint" style={{ color: "inherit", opacity: 0.8 }}>· 1 minute</span></button>
      </>}>
      <div className="welcome">
        <Logo size={40} />
        <p style={{ fontSize: 15 }}>Meridian is an actuarial modelling workspace: readable formulas, a fast exact engine, and results you can trace and check.</p>
        <ul>
          <li>Three working models, including a South African funeral product on a SAM basis</li>
          <li>What-if sliders, standard sensitivities and side-by-side comparison</li>
          <li>Import your own policy data from a CSV file</li>
          <li>Every model reconciled to an independent implementation</li>
        </ul>
      </div>
    </Modal>
  );
}

/** A spotlight tour: highlights one part of the app per step and explains it. */
export function Tour({ onEnd }: { onEnd: () => void }) {
  const [i, setI] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const pop = useRef<HTMLDivElement>(null);
  const [popH, setPopH] = useState(200);
  const step = STEPS[i];
  const last = i === STEPS.length - 1;

  useEffect(() => {
    if (window.location.hash !== step.route) window.location.hash = step.route;
    let alive = true, tries = 0;
    const measure = () => {
      const el = document.querySelector(step.target);
      if (alive && el) setRect(el.getBoundingClientRect());
    };
    const find = () => {
      if (!alive) return;
      const el = document.querySelector(step.target);
      if (el) {
        el.scrollIntoView({ block: "nearest" });
        requestAnimationFrame(measure);
      } else if (tries++ < 50) setTimeout(find, 100);
      else setRect(null);
    };
    setRect(null);
    const t = setTimeout(find, 60);
    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    return () => { alive = false; clearTimeout(t); window.removeEventListener("resize", measure); window.removeEventListener("scroll", measure, true); };
  }, [i, step.route, step.target]);

  useLayoutEffect(() => { if (pop.current) setPopH(pop.current.offsetHeight); }, [i, rect]);

  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onEnd();
      else if (e.key === "ArrowRight" || e.key === "Enter") { e.preventDefault(); last ? onEnd() : setI(i + 1); }
      else if (e.key === "ArrowLeft" && i > 0) setI(i - 1);
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [i, last, onEnd]);

  const W = 360, pad = 6, gap = 14, vw = window.innerWidth, vh = window.innerHeight;
  let top = vh / 2 - popH / 2, left = vw / 2 - W / 2;
  if (rect) {
    const big = rect.height > vh * 0.55;
    if (big) { top = vh - popH - 24; left = vw - W - 24; }
    else if (rect.bottom + gap + popH < vh - 12) { top = rect.bottom + gap; left = rect.left; }
    else if (rect.top - gap - popH > 12) { top = rect.top - gap - popH; left = rect.left; }
    else { top = Math.max(12, rect.top); left = rect.right + gap; }
    left = Math.min(Math.max(16, left), vw - W - 16);
    top = Math.min(Math.max(12, top), vh - popH - 12);
  }
  const hole = rect
    ? { top: Math.max(rect.top - pad, 4), left: Math.max(rect.left - pad, 4),
        width: Math.min(rect.width + 2 * pad, vw - 8), height: Math.min(rect.height + 2 * pad, vh - Math.max(rect.top - pad, 4) - 4) }
    : { top: vh / 2, left: vw / 2, width: 0, height: 0 };

  return (
    <>
      <div className="tour-hole" style={hole} />
      <div className="card tour-pop" ref={pop} role="dialog" aria-modal="true" aria-label={step.title} style={{ top, left, width: W }}>
        <div className="spread">
          <span className="eyebrow">Tour · {i + 1} of {STEPS.length}</span>
          <button className="icon-btn" onClick={onEnd} aria-label="End tour"><Icon name="close" size={16} /></button>
        </div>
        <h2>{step.title}</h2>
        <p className="muted">{step.body}</p>
        <div className="spread" style={{ marginTop: 4 }}>
          <div className="tour-dots" aria-hidden="true">{STEPS.map((_, k) => <i key={k} className={k === i ? "on" : ""} />)}</div>
          <div className="row">
            {i > 0 && <button className="btn ghost small" onClick={() => setI(i - 1)}>Back</button>}
            <button className="btn primary small" onClick={() => (last ? onEnd() : setI(i + 1))} autoFocus>
              {last ? "Finish" : "Next"} {!last && <Icon name="arrow" size={14} />}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
