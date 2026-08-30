// Static smoke test for simulation/simulation.html — extracts the inline script,
// runs it against a permissive DOM stub, then drives both Sims through every step
// (including all fired timers) to catch reference/typos/data-shape errors.
// Usage: node simulation/verify_static.mjs
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const html = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "simulation.html"), "utf8");
const m = html.match(/<script>([\s\S]*?)<\/script>/);
if (!m) { console.error("no <script> found"); process.exit(1); }
const src = m[1];

// ---- permissive DOM stubs --------------------------------------------------
const ids = new Map();
function stubEl(tag) {
  const el = {
    tag, style: {}, dataset: {}, children: [], _inner: "", _text: "",
    classList: { add() {}, remove() {}, toggle() {}, contains: () => false },
    setAttribute() {}, getAttribute: () => null, removeAttribute() {},
    appendChild(c) { el.children.push(c); return c; },
    remove() {},
    querySelector: () => stubEl("q"),
    querySelectorAll: () => [],
    addEventListener() {},
    addEventListenerNS() {},
  };
  Object.defineProperty(el, "innerHTML", { get: () => el._inner, set: (v) => { el._inner = v; el.children = []; } });
  Object.defineProperty(el, "textContent", { get: () => el._text, set: (v) => { el._text = String(v); } });
  Object.defineProperty(el, "scrollTop", { get: () => 0, set: () => {} });
  return el;
}
globalThis.document = {
  getElementById: (id) => { if (!ids.has(id)) ids.set(id, stubEl(id)); return ids.get(id); },
  createElement: (t) => stubEl(t),
  createElementNS: (ns, t) => stubEl(t),
  querySelectorAll: () => [],
  addEventListener() {},
};
globalThis.performance = { now: () => Date.now() };
globalThis.requestAnimationFrame = (fn) => { fn(performance.now() + 5000); return 0; };

// ---- fake timer queue -------------------------------------------------------
let now = 0; const timeouts = []; const intervals = new Map(); let ivId = 0;
globalThis.setTimeout = (fn, ms = 0) => { timeouts.push({ fn, at: now + (ms || 0) + 1 }); return timeouts.length; };
globalThis.clearTimeout = () => {};
globalThis.setInterval = (fn, ms = 0) => { const id = ++ivId; intervals.set(id, { fn }); return id; };
globalThis.clearInterval = (id) => { intervals.delete(id); };
function drain(rounds = 400) {
  for (let r = 0; r < rounds; r++) {
    timeouts.sort((a, b) => a.at - b.at);
    const due = timeouts.filter((t) => t.at <= now + 1e9);
    timeouts.length = 0;
    if (!due.length && !intervals.size) return;
    for (const t of due) { now = Math.max(now, t.at); t.fn(); }
    for (const [, iv] of intervals) iv.fn();
  }
  throw new Error("timer queue did not settle");
}

// ---- run --------------------------------------------------------------------
try {
  // indirect eval runs in global scope like a real <script>; its completion
  // value carries the top-level `let` bindings that never reach globalThis
  const [, s2] = (0, eval)(src + ";[sim1, sim2]");
  if (typeof s2 !== "object") throw new Error("sims not constructed");
  const ds = globalThis.__ds;
  if (!ds || typeof ds.switchTrack !== "function") throw new Error("__ds hook missing");
  // drive every PoC-1 track plus PoC-2 through all steps
  for (const track of ["wind", "zon", "bos"]) {
    ds.switchTrack(track);
    const s1 = ds.sims[0];
    if (s1.steps.length < 5) throw new Error(`track ${track}: too few steps`);
    s1.jumpToStage(8); drain();
  }
  const n1 = ds.sims[0].steps.length, n2 = s2.steps.length;
  s2.jumpToStage(7); drain(600);
  ds.sims[0].reset(); s2.reset(); drain();
  console.log(`OK — script evaluated; poc1 tracks driven through every step (${n1} steps on active track), sim2 ${n2} steps, timers drained`);
} catch (e) {
  console.error("FAIL:", e && e.stack ? e.stack.split("\n").slice(0, 6).join("\n") : e);
  process.exit(1);
}
