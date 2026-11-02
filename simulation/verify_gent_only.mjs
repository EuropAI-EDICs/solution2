// Static smoke test voor simulation/gent-simulatie.html — het zelfstandige
// Gent-bestand: alleen de Gent-tab actief, drie levensgebeurtenissen via de
// dropdown, kotfoto's als data-URIs. Geen andere PoC-data aanwezig.
// Usage: node simulation/verify_gent_only.mjs
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const html = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "gent-simulatie.html"), "utf8");
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
    appendChild(c) { el.children.push(c); c.parentElement = el; return c; },
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
globalThis.performance = { now: () => Date.now(),
  markResourceTiming() {}, getEntries() { return []; },
  getEntriesByName() { return []; }, getEntriesByType() { return []; } };
globalThis.requestAnimationFrame = (fn) => { fn(performance.now() + 5000); return 0; };

// ---- fake timer queue -------------------------------------------------------
let now = 0; const timeouts = []; const intervals = new Map(); let ivId = 0;
globalThis.setTimeout = (fn, ms = 0) => { timeouts.push({ fn, at: now + (ms || 0) + 1 });
  const h = { unref() {}, ref() {}, [Symbol.toPrimitive]() { return 0; } }; return h; };
globalThis.clearTimeout = () => {};
globalThis.setInterval = (fn, ms = 0) => { const id = ++ivId; intervals.set(id, { fn });
  return { unref() {}, ref() {}, [Symbol.toPrimitive]() { return id; } }; };
globalThis.clearInterval = (id) => { intervals.delete(id); };
function drain(rounds = 400) {
  for (let r = 0; r < rounds; r++) {
    timeouts.sort((a, b) => a.at - b.at);
    const due = timeouts.filter((t) => t.at <= now + 1e9);
    timeouts.length = 0;
    if (!due.length && !intervals.size) return;
    for (const t of due) { if (t.fn && t.fn.name === "onTick") continue; now = Math.max(now, t.at); t.fn(); }
    for (const [, iv] of intervals) if (iv.fn && iv.fn.name !== "onTick") iv.fn();
  }
}
process.on("unhandledRejection", (e) => console.warn("WARN: unhandledRejection:", String(e).slice(0, 140)));
process.on("uncaughtException", (e) => console.warn("WARN: uncaughtException:", String(e).slice(0, 140)));

// ---- run --------------------------------------------------------------------
try {
  if (html.includes('"poc1"')) throw new Error("gent-only bestand bevat nog poc1-data");
  if (!html.includes("data:image/jpeg;base64,")) throw new Error("kotfoto's zijn niet ingebed");
  const [sim5var] = (0, eval)(src + ";[sim5]");
  if (!sim5var || sim5var.steps.length < 4) throw new Error("gent sim5 niet geconstrueerd");
  const ds = globalThis.__ds;
  if (!ds || typeof ds.gentPackage !== "function") throw new Error("__ds hook missing");
  const s5 = ds.sims[3];
  s5.jumpToStage(s5.steps.length - 1); drain();
  ds.gentPersona("wim"); drain();
  ds.gentPackage("gentBurger"); drain();
  const s5b = ds.sims[3]; s5b.jumpToStage(s5b.steps.length - 1); drain();
  const kaartBurger = globalThis.document.getElementById("kaart5");
  if ((kaartBurger.innerHTML.match(/<[a-zA-Z]/g) || []).length < 6)
    throw new Error("burgerkaart leeg in gent-only");
  ds.gentPackage("gentKot"); drain();
  ds.gentRandomKot(); drain();
  const kotcard = globalThis.document.getElementById("kotcard").innerHTML;
  if (kotcard.indexOf("kot.stad.gent") < 0 || kotcard.indexOf("data:image/jpeg;base64,") < 0)
    throw new Error("willekeurig-kot-kaart zonder ingebedde foto");
  ds.gentPackage("gentEvent"); drain();
  const se = ds.sims[3]; se.jumpToStage(se.steps.length - 1); drain();
  ds.gentPersona("gil"); drain();
  const evTags = (globalThis.document.getElementById("kaart5").innerHTML.match(/<[a-zA-Z]/g) || []).length;
  if (evTags !== 5) throw new Error("eventkaart onvolledig in gent-only (gekregen: " + evTags + ")");
  if (globalThis.document.getElementById("kaart5info").innerHTML.indexOf("Gentse Feesten 2026") < 0)
    throw new Error("feesten-voorbeelden ontbreken in gent-only eventkaart");
  ds.gentPackage("gent"); drain();
  if ((globalThis.document.getElementById("kaart5").innerHTML.match(/<[a-zA-Z]/g) || []).length !== 6)
    throw new Error("ondernemerskaart niet terug na pakket-wissels");
  console.log("OK — gent-simulatie.html: alleen Gent actief, vier pakketten via de dropdown, kotfoto's ingebed, timers drained");
} catch (e) {
  console.error("FAIL:", e && e.stack ? e.stack.split("\n").slice(0, 6).join("\n") : e);
  process.exit(1);
}
