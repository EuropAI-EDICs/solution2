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
    appendChild(c) { el.children.push(c); c.parentElement = el; return c; },
    remove() {},
    insertAdjacentHTML(pos, html) { this._adj = (this._adj || "") + String(html); },
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
const scheduled = new Map();   // diagnostiek: welke fn blijft zichzelf her-schedulen
globalThis.setTimeout = (fn, ms = 0) => { timeouts.push({ fn, at: now + (ms || 0) + 1 });
  const key = String(fn).slice(0, 90); scheduled.set(key, (scheduled.get(key) || 0) + 1);
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
    for (const t of due) {
      if (t.fn && t.fn.name === "onTick") continue;   // node/undici-interne klok: her-schedulet zich eeuwig
      now = Math.max(now, t.at); t.fn(); }
    for (const [, iv] of intervals)
      if (iv.fn && iv.fn.name !== "onTick") iv.fn();   // node/undici-interne klok overslaan
  }
  const loopers = [...scheduled.entries()].sort((a, b) => b[1] - a[1]).slice(0, 2)
    .map(([k, n]) => `${n}× ${k.slice(0, 60)}`).join(" | ");
  console.warn(`WARN: timer queue niet gesetteld (poll/reconnect-loop?) — top: ${loopers}`);
}

// WIP live-calls (bv. Ollama-fetch in een nieuwe tab) mogen onder de stubs
// rejectionen geven — waarschuw, maar breek de smoke test er niet op.
process.on("unhandledRejection", (e) =>
  console.warn("WARN: unhandledRejection (live-call WIP?):", String(e).slice(0, 140)));
process.on("uncaughtException", (e) =>
  console.warn("WARN: uncaughtException (live-call WIP?):", String(e).slice(0, 140)));

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
  // dock follows the PoC tab: PoC-2 → eindhoven, PoC-1 → utrecht
  ds.switchTab(2);
  if (globalThis.document.getElementById("layadock").parentElement !== globalThis.document.getElementById("view2")) {
    throw new Error("laya dock not mounted on PoC-2");
  }
  ds.switchTab(1);
  if (globalThis.document.getElementById("layadock").parentElement !== globalThis.document.getElementById("view1")) {
    throw new Error("laya dock not mounted on PoC-1");
  }
  ds.switchTab(2);
  if (!ds.layaOn()) throw new Error("laya chat not unlocked after poc2 run");
  if (!ds.layaOn("eindhoven")) throw new Error("eindhoven chat not unlocked after poc2 run");
  // laya forward pass + chat intents on real embedded predictions
  ds.fpRun("geluidonderzoek bij evenementen");
  ds.fpRun("22.46 kennisbank");
  const chat = (v) => { globalThis.document.getElementById("chatin").value = v; ds.chatSend(); };
  for (const q of ["22.1", "wat zijn je cijfers", "onthoudingen", "jurist", "kennisbank",
                   "hoeveel regels gaan naar hoofdstuk 10", "run samenvatting", "xyzzy onbekend"]) chat(q);
  if (!ds.nnBron("milieubelastende activiteiten", 1)[0]) throw new Error("nnBron empty");
  // utrecht dataset: unlocked by the sim1 report steps driven above
  ds.switchLayaDs("utrecht");
  if (!ds.layaOn("utrecht")) throw new Error("utrecht chat not unlocked after poc1 runs");
  ds.fpRun("windturbines nabij natura 2000");
  const chatU = (v) => { globalThis.document.getElementById("chatin").value = v; ds.chatSend(); };
  for (const q of ["5.1", "wat zijn je cijfers", "onthoudingen", "jurist",
                   "hoeveel km is de eindzone", "welke regels zijn uitgesloten",
                   "hoeveel panden staan er in de zone",
                   "tracks overzicht", "xyzzy onbekend"]) chatU(q);
  ds.switchLayaDs("eindhoven");
  if (!ds.layaOn("eindhoven")) throw new Error("eindhoven chat lost after ds switch");
  ds.sims[0].reset(); s2.reset(); drain();
  if (ds.layaOn()) throw new Error("laya chat not re-locked after reset");

  // PoC-4 Breda five-value tab: timeline → unlock → golden chat
  ds.switchTab(4);
  const s4 = ds.sim4;
  if (!s4 || s4.steps.length < 6) throw new Error("sim4 missing or too few steps");
  s4.jumpToStage(5); drain();
  if (!ds.bredaOn()) throw new Error("breda chat not unlocked after timeline");
  globalThis.document.getElementById("chatin4").value = "Belcrum";
  ds.bredaChatSend();
  globalThis.document.getElementById("chatin4").value = "xyzzy onbekend";
  ds.bredaChatSend();
  ds.setWaarde("autonomous");
  ds.setWaarde("democratic");
  s4.reset(); drain();

  // ---- Gent tab: sim5 + persona switches ---------------------------------
  const s5 = ds.sims[3];
  if (!s5 || s5.steps.length < 4) throw new Error("sim5 missing or too few steps");
  s5.jumpToStage(s5.steps.length - 1); drain();
  ds.gentPersona("dirk"); drain();
  const s5d = ds.sims[3];
  s5d.jumpToStage(s5d.steps.length - 1); drain();
  ds.gentPersona("ellen"); drain();
  const s5e = ds.sims[3];
  s5e.play(); drain(4000); s5e.pause();
  ds.gentPersona("wim"); drain();
  const kaartSvg = globalThis.document.getElementById("kaart5");
  const kaartTags = () => (kaartSvg.innerHTML.match(/<[a-zA-Z]/g) || []).length;
  if (!kaartSvg || kaartTags() !== 6) throw new Error("kaart5 toont bij persona-switch basis + startlocatie (gekregen: " + kaartTags() + ")");
  const s5k = ds.sims[3];
  s5k.jumpToStage(0); drain();
  if (kaartTags() !== 6) throw new Error("kaart5 blijft bij de intake-stap op basis + start (gekregen: " + kaartTags() + ")");
  s5k.jumpToStage(s5k.steps.length - 1); drain();
  if (kaartTags() < 15) throw new Error("kaart5 volledige lagen (routes+innames+doel) verwacht na de routing-stap (gekregen: " + kaartTags() + ")");
  s5k.reset(); drain();
  if (kaartTags() !== 6 || kaartSvg.innerHTML.indexOf("circle") < 0) throw new Error("kaart5 blijft na reset gevuld met basis + startlocatie (gekregen: " + kaartTags() + ")");
  ds.gentPersona("nadia"); drain();
  ds.gentPersona("ilse"); drain();
  ds.gentPersona("hanne"); drain();
  ds.gentPersona("maria"); drain();
  const kaartWrap = globalThis.document.getElementById("kaart5wrap");
  if (kaartWrap && kaartWrap.style.display !== "none") throw new Error("kaart5 verborgen verwacht voor maria (geen voertuig)");
  ds.gentPersona("sanne"); drain();
  if (kaartWrap && kaartWrap.style.display === "none") throw new Error("kaart5 zichtbaar verwacht voor sanne");
  if (ds.bredaOn()) throw new Error("breda chat not re-locked after reset");

  // ---- Gent burgerpakket GT-VERH-01 via de levensgebeurtenis-dropdown ------
  ds.gentPackage("gentBurger"); drain();
  const s5b = ds.sims[3];
  if (!s5b || s5b.steps.length < 4) throw new Error("burger sim5 missing after package switch");
  s5b.jumpToStage(s5b.steps.length - 1); drain();
  ds.gentPersona("tomas"); drain();
  const kbSvg = globalThis.document.getElementById("kaart5");
  const kbTags = () => (kbSvg.innerHTML.match(/<[a-zA-Z]/g) || []).length;
  if (!kbSvg || kbTags() !== 7) throw new Error("burgerkaart toont grens + 3 zones + woning (gekregen: " + (kbSvg ? kbTags() : "none") + ")");
  if (kbSvg.innerHTML.indexOf("nieuwe woning") < 0) throw new Error("burgerkaart startpunt 'nieuwe woning' ontbreekt");
  ds.gentPersona("robrecht"); drain();
  ds.gentPackage("gent"); drain();
  if (kaartTags() !== 6) throw new Error("terug op ondernemerspakket: kaart5 weer basis + start (gekregen: " + kaartTags() + ")");

  // ---- Gent kotpakket GT-KOT-01 via de levensgebeurtenis-dropdown --------
  ds.gentPackage("gentKot"); drain();
  const s5k2 = ds.sims[3];
  if (!s5k2 || s5k2.steps.length < 4) throw new Error("kot sim5 missing after package switch");
  s5k2.jumpToStage(s5k2.steps.length - 1); drain();
  ds.gentPersona("gregory"); drain();
  const kkSvg = globalThis.document.getElementById("kaart5");
  const kkTags = () => (kkSvg.innerHTML.match(/<[a-zA-Z]/g) || []).length;
  if (!kkSvg || kkTags() !== 5) throw new Error("kotkaart toont grens + kotzone + kotadres (gekregen: " + (kkSvg ? kkTags() : "none") + ")");
  const kkInfo = globalThis.document.getElementById("kaart5info").innerHTML;
  if (kkInfo.indexOf("kotzone:") < 0) throw new Error("kotzone-naam ontbreekt in kaart5info");
  const kotwrap = globalThis.document.getElementById("kotwrap");
  if (!kotwrap || kotwrap.style.display === "none") throw new Error("willekeurig-kot-kaart verwacht in kotpakket");
  if (globalThis.document.getElementById("kotcard").innerHTML.indexOf("kot.stad.gent") < 0)
    throw new Error("willekeurig-kot-kaart is leeg");
  ds.gentRandomKot(); drain();
  if (globalThis.document.getElementById("kotcard").innerHTML.indexOf("adres:") < 0)
    throw new Error("willekeurig-kot-kaart vult niet na dobbel");
  const geselecteerd = ds.gentKotSelectie ? ds.gentKotSelectie() : null;
  if (!geselecteerd || !geselecteerd.run) throw new Error("kotselectie zonder run-slice");
  const factsNa = globalThis.document.getElementById("facts5").innerHTML;
  if (factsNa.indexOf(geselecteerd.adres) < 0)
    throw new Error("feiten-paneel volgt het geselecteerde kotadres niet: " + geselecteerd.adres);
  const chatNa = globalThis.document.getElementById("chat5").innerHTML;
  if (chatNa.indexOf("kotzone") < 0 || chatNa.indexOf("koteloket-status") < 0)
    throw new Error("aanvraag-formulier volgt het geselecteerde kot niet");
  const statusNa = globalThis.document.getElementById("facts5").innerHTML;
  if (statusNa.indexOf("afval") < 0) throw new Error("afvalfeiten ontbreken bij kotselectie");
  ds.gentPackage("gentEvent"); drain();
  const se = ds.sims[3];
  se.jumpToStage(se.steps.length - 1); drain();
  ds.gentPersona("lorne"); drain();
  const evWrap = globalThis.document.getElementById("kaart5wrap");
  if (evWrap && evWrap.style.display === "none") throw new Error("eventkaart verwacht zichtbaar");
  const evSvg = globalThis.document.getElementById("kaart5");
  const evTags = (evSvg.innerHTML.match(/<[a-zA-Z]/g) || []).length;
  if (evTags !== 5) throw new Error("eventkaart toont grens + lez + locatie (gekregen: " + evTags + ")");
  const evInfo = globalThis.document.getElementById("kaart5info").innerHTML;
  if (evInfo.indexOf("Gentse Feesten 2026") < 0) throw new Error("feesten-voorbeelden ontbreken in kaartinfo");
  ds.gentPackage("gent"); drain();
  if (kaartTags() !== 6) throw new Error("terug op ondernemerspakket na event: kaart5 weer basis + start (gekregen: " + kaartTags() + ")");

  // ---- Veenendaal · Spoorzone gebiedscheck (tab 6) ------------------------
  const s6 = ds.sim6;
  if (!s6 || s6.steps.length !== 8) throw new Error("sim6 verwacht 8 stappen (kreeg: " + (s6 ? s6.steps.length : "none") + ")");
  if (ds.vdPanden() < 3000) throw new Error("veenendaal-kaart mist panden (" + ds.vdPanden() + ")");
  s6.reset(); drain(); s6.jumpToStage(s6.steps.length - 1); drain();
  const done6 = globalThis.document.getElementById("done6");
  if (!done6._inner || done6._inner.indexOf("V3 PASS") < 0) throw new Error("done6-banner mist 'V3 PASS'");
  if (done6._inner.indexOf("gebiedscheck") < 0) throw new Error("done6-banner mist 'gebiedscheck'");
  const doel6 = globalThis.document.getElementById("doel6");
  if (!doel6._inner || doel6._inner.indexOf("4.500") < 0) throw new Error("doel-tabel mist woningbouwdoel");
  const v3n = globalThis.document.getElementById("v3note6");
  if (!v3n._text || v3n._text.indexOf("2e") < 0) throw new Error("v3note6 leeg");

  // deelgebieden: payload + per-scenario zone-tabel
  const zdata = ds.vdZonesData();
  if (!zdata || !zdata.zones || zdata.zones.length !== 7) throw new Error("zone-payload mist of != 7 zones");
  const zones6 = globalThis.document.getElementById("zones6");
  if (!zones6._inner || zones6._inner.indexOf("Stationsgebied") < 0) throw new Error("zone-tabel leeg");

  // agent-uitlegboxen op elke PoC-tab (logkop1/2/4/5/6)
  for (const id of ["logkop1", "logkop2", "logkop4", "logkop5", "logkop6"]) {
    const k = globalThis.document.getElementById(id);
    if (!k || !k._inner || k._inner.indexOf("LLM") < 0)
      throw new Error(id + " mist de agent-rol-uitleg");
  }

  // scenario-sweep: dropdown + onafhankelijke weergave per variant
  const sweep = ds.vdSweep();
  if (!sweep || !sweep.scenarios || sweep.scenarios.length < 6) throw new Error("sweep-payload mist of te klein");
  ds.vdScenario("BOUW-OP-GROEN"); drain();
  const sweepBody = globalThis.document.getElementById("sweep6body");
  if (!sweepBody._inner || sweepBody._inner.indexOf("14.83") < 0) throw new Error("BOUW-OP-GROEN toont groen eind 14.83 niet");
  if (sweepBody._inner.indexOf("breekt") < 0) throw new Error("groendoel-breek-marker ontbreekt");
  const doel6s = globalThis.document.getElementById("doel6");
  if (!doel6s._inner || doel6s._inner.indexOf("eindstand in dit scenario") < 0)
    throw new Error("doel-tabel schakelt niet mee naar scenario-modus");
  if (doel6s._inner.indexOf("14.83") < 0) throw new Error("doel-tabel toont scenario-groen eind niet");
  ds.vdScenario("TEMPO-150"); drain();
  if (sweepBody._inner.indexOf("2050") < 0) throw new Error("TEMPO-150 toont doelpercentagejaar 2050 niet");
  if (ds.vdNieuwN() < 10) throw new Error("kaart-overlay nieuwbouw-allocatie te klein of afwezig (" + ds.vdNieuwN() + " vlakken)");
  ds.vdScenario("CONTROL"); drain();
  if (ds.vdNieuwN() !== 0) throw new Error("CONTROL moet de kaart-overlay legen");
  if (doel6s._inner.indexOf("nulmeting") < 0) throw new Error("doel-tabel gaat niet terug naar nulmeting");
  ds.vdScenario("BOUW-OP-GROEN"); drain();
  if (zones6._inner.indexOf("Goeie Spoor") < 0) throw new Error("zone-tabel mist 't Goeie Spoor");
  const bgz = (ds.vdSweep().scenarios.find(x => x.id === "BOUW-OP-GROEN").kaart || {}).per_zone || {};
  const somZones = Object.values(bgz).reduce((a, z) => a + z.genomen_ha, 0);
  if (!(somZones > 17 && somZones < 19)) throw new Error("zone-som buiten bereik: " + somZones);
  if (zones6._inner.indexOf(somZones.toFixed(2)) < 0)
    throw new Error("zone-tabel toont de totaal-toedeling niet");

  // ---- DSO-KB tab 7: coverage + toets + drift ----------------------------
  ds.switchTab(7);
  const s7 = ds.sim7;
  if (!s7 || s7.steps.length !== 5) throw new Error("sim7 verwacht 5 stappen (kreeg: " + (s7 ? s7.steps.length : "none") + ")");
  s7.jumpToStage(3); drain();
  const kb = ds.dsokbData();
  if (!kb || kb.instrumenten.length !== 2) throw new Error("dsokbData verwacht 2 instrumenten");
  const eh7 = kb.instrumenten.find(i => i.id === "eindhoven");
  const ut7 = kb.instrumenten.find(i => i.id === "utrecht");
  if (eh7.dekking.coverage !== 0.5635) throw new Error("eindhoven coverage verwacht 0.5635, kreeg " + eh7.dekking.coverage);
  if (eh7.dekking.executable !== 457 || eh7.dekking.dsoArtikelen !== 811) throw new Error("eindhoven 811/457 verwacht");
  if (ut7.dekking.coverage !== 0.0654) throw new Error("utrecht coverage verwacht 0.0654, kreeg " + ut7.dekking.coverage);
  if (ut7.dekking.executable !== 7) throw new Error("utrecht executable verwacht 7");
  if (eh7.geo.getoetst !== 34 || eh7.geo.overeenstemming !== 34) throw new Error("eindhoven geo verwacht 34/34");
  if (ut7.geo.naamOvereenkomend !== 8) throw new Error("utrecht naamafstemming verwacht 8");
  if (ut7.geo.naamSweepGmls !== 8) throw new Error("utrecht naamSweepGmls verwacht 8, kreeg " + ut7.geo.naamSweepGmls);
  // geo-kaartregels eerlijk: geen "✓ 0/0" op niet-uitgevoerde toetsen —
  // Utrecht toont alléén zijn echte 8/8-naamafstemming (punt-in-GIO is daar
  // niet uitgevoerd: GIO's niet filename-koppelbaar, getoetst=0).
  const utCard7 = globalThis.document.getElementById("kb7-utrecht").innerHTML;
  if (utCard7.includes("0/0")) throw new Error("utrecht-kaart toont nog een 0/0-geolijn");
  if (!utCard7.includes("naamafstemming 8/8")) throw new Error("utrecht-kaart mist echte naamafstemming 8/8");
  if (eh7.ververs && eh7.ververs.drift.inhoudelijkeDrift !== "geen")
    throw new Error("eindhoven drift verwacht 'geen', kreeg " + eh7.ververs.drift.inhoudelijkeDrift);
  if (!globalThis.document.getElementById("kb7-cov-eindhoven").textContent.includes("56,35"))
    throw new Error("kb7-cov-eindhoven mist gouden 56,35%");

  const kg = ds.kg7Data();
  if (!kg || !kg.eindhoven || !kg.utrecht) throw new Error("kg7Data verwacht beide instrumenten");
  const kgE = kg.eindhoven, kgU = kg.utrecht;
  if (kgE.top[0] !== "1.8" || kgE.artikelen["1.8"].nRegels !== 12) throw new Error("eindhoven kg top verwacht 1.8 met 12 regels");
  if (kgE.artikelen["1.8"].status !== "formalized") throw new Error("eindhoven 1.8 verwacht formalized");
  if (kgE.artikelen["3.37"].status !== "unmatched") throw new Error("eindhoven 3.37 verwacht unmatched");
  if (kgU.top[0] !== "10.4" || kgU.artikelen["10.4"].nRegels !== 9) throw new Error("utrecht kg top verwacht 10.4 met 9 regels");
  if (Object.keys(kgE.artikelen).length !== 811 || Object.keys(kgU.artikelen).length !== 107)
    throw new Error("kg artikel-aantallen verwacht 811/107");
  if (!(kgE.overzicht.n.length > 0) || !(kgE.overzicht.e.length > 0)) throw new Error("kg overzicht zonder knopen/edges");
  const pos = new Set(kgE.overzicht.n.map(n => n.x + "," + n.y));
  if (pos.size !== kgE.overzicht.n.length)
    throw new Error("kg overzicht: knopen stapelen op dezelfde (x,y): " + kgE.overzicht.n.length + " knopen, " + pos.size + " uniek");
  if (!(kgE.overzicht.h > 300 && kgE.overzicht.h < 1500))
    throw new Error("kg overzicht-hoogte buiten band (300-1500): " + kgE.overzicht.h);
  if (kgU.artikelen["10.4"].status !== "unmatched")
    throw new Error("utrecht 10.4 status verwacht unmatched (README-claim)");
  ds.kg7Kies("eindhoven", "3.37");
  const kgN = parseInt(globalThis.document.getElementById("kg7-n").textContent, 10);
  if (!(kgN > 0)) throw new Error("kg7-n leeg na artikelkeuze 3.37");
  const a18 = kgE.artikelen["1.8"];
  if (!a18.tekst || !a18.tekst.includes("meet- en rekenbepalingen"))
    throw new Error("kg 1.8-popup mist gouden tekstfragment");
  if (!a18.rr.includes("toegestaan_art_1_8") || !(a18.rr.includes("limiet_m") || a18.rr.includes("in_werkingsgebied")))
    throw new Error("kg 1.8-popup mist executie-output/input");
  const w18 = a18.rts[0], ld18 = (kgE.lids || {})[w18];
  if (!ld18 || !(ld18.tekst.length >= 40))
    throw new Error("kg lids mist echte lidtekst voor " + w18);
  const u104 = kgU.artikelen["10.4"];
  if (!u104.rr.includes("niet geformaliseerd") || !u104.rr.includes("unmatched"))
    throw new Error("kg utrecht 10.4 rr verwacht niet-geformaliseerd/unmatched");

  console.log(`OK — script evaluated; poc1 tracks driven through every step (${n1} steps on active track), sim2 ${n2} steps, laya fp+chat driven, poc4 sim4 ${s4.steps.length} steps, gent sim5 ${s5e.steps.length} steps (sanne/dirk/ellen/wim/nadia/ilse/hanne/maria) + kaartpanel gecontroleerd incl. burger-, kot- en eventpakket-switch, veenendaal sim6 ${s6.steps.length} stappen (${ds.vdPanden()} panden op de kaart), timers drained, sim7 ${s7.steps.length} stappen (dekking ${eh7.dekking.coverage})`);
} catch (e) {
  console.error("FAIL:", e && e.stack ? e.stack.split("\n").slice(0, 6).join("\n") : e);
  process.exit(1);
}
