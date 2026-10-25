import { strings, t, appText } from "./i18n.js?v=citiverse-7";
import { recipeField, riskLabel, readinessLabel } from "./recipes-i18n.js?v=citiverse-7";
import { kindForProcess } from "./process-kinds.js?v=citiverse-7";

const THEME_ORDER = ["utrecht", "breda", "rijnland", "eindhoven", "lake", "gis", "key", "city", "other"];

const state = {
  lang: localStorage.getItem("edic-mp-lang") || "nl",
  theme: "all",
  query: "",
  recipes: [],
  selected: null,
  explainOpen: false,
  recipeCache: new Map(),
};

const $ = (sel, root = document) => root.querySelector(sel);

function setLang(lang) {
  state.lang = lang;
  localStorage.setItem("edic-mp-lang", lang);
  document.documentElement.lang = lang;
  applyStaticI18n();
  renderChips();
  renderGrid();
  if (state.selected) openDetail(state.selected);
  if (state.explainOpen) openExplain();
  $("#btn-nl").setAttribute("aria-pressed", String(lang === "nl"));
  $("#btn-en").setAttribute("aria-pressed", String(lang === "en"));
}

function applyStaticI18n() {
  const L = state.lang;
  const map = [
    ["brand", "brand"],
    ["heroEyebrow", "heroEyebrow"],
    ["heroBrand", "heroBrand"],
    ["tagline", "tagline"],
    ["heroLead", "heroLead"],
    ["ctaCatalog", "ctaCatalog"],
    ["ctaExplain", "ctaExplain"],
    ["catalogEyebrow", "catalogEyebrow"],
    ["catalogTitle", "catalogTitle"],
    ["catalogLead", "catalogLead"],
    ["footer", "footer"],
  ];
  for (const [attr, key] of map) {
    const el = document.querySelector(`[data-i18n="${attr}"]`);
    if (el) el.textContent = t(key, L);
  }
  $("#search").placeholder = t("searchPlaceholder", L);
}

function snippet(recipe) {
  const app = appText(recipe.id, state.lang);
  if (app) return app;
  const d = recipeField(recipe, "description", state.lang) || "";
  return d.length > 180 ? d.slice(0, 177) + "…" : d;
}

function filtered() {
  const q = state.query.trim().toLowerCase();
  return state.recipes.filter((r) => {
    if (state.theme !== "all" && r.theme !== state.theme) return false;
    if (!q) return true;
    const hay = [
      r.id,
      recipeField(r, "title", "nl"),
      recipeField(r, "title", "en"),
      recipeField(r, "description", "nl"),
      recipeField(r, "description", "en"),
      appText(r.id, "nl"),
      appText(r.id, "en"),
    ]
      .join(" ")
      .toLowerCase();
    return hay.includes(q);
  });
}

function renderChips() {
  const host = $("#chips");
  const L = state.lang;
  const themes = ["all", ...THEME_ORDER.filter((th) => state.recipes.some((r) => r.theme === th))];
  host.innerHTML = themes
    .map((th) => {
      const label = th === "all" ? t("allThemes", L) : strings.themes[th]?.[L] || th;
      const pressed = state.theme === th;
      return `<button type="button" class="chip" data-theme="${th}" aria-pressed="${pressed}">${label}</button>`;
    })
    .join("");
  host.querySelectorAll(".chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.theme = btn.dataset.theme;
      renderChips();
      renderGrid();
    });
  });
}

function renderGrid() {
  const host = $("#grid");
  const items = filtered();
  if (!items.length) {
    host.innerHTML = `<p class="empty">${t("empty", state.lang)}</p>`;
    return;
  }
  host.innerHTML = items
    .map((r, i) => {
      const risk = (r.riskLevel || "").toLowerCase();
      const themeLabel = strings.themes[r.theme]?.[state.lang] || r.theme;
      const title = recipeField(r, "title", state.lang) || r.title || r.id;
      return `
      <button type="button" class="recipe" data-id="${r.id}" style="animation-delay:${Math.min(i, 12) * 0.03}s">
        <div class="recipe-meta">
          <span class="badge">${themeLabel}</span>
          ${risk ? `<span class="badge risk-${risk}">${t("risk", state.lang)} ${riskLabel(risk, state.lang)}</span>` : ""}
        </div>
        <h3>${escapeHtml(title)}</h3>
        <p>${escapeHtml(snippet(r))}</p>
      </button>`;
    })
    .join("");
  host.querySelectorAll(".recipe").forEach((btn) => {
    btn.addEventListener("click", () => {
      const recipe = state.recipes.find((x) => x.id === btn.dataset.id);
      if (recipe) openDetail(recipe);
    });
  });
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function openExplain() {
  state.explainOpen = true;
  closeDetail();
  const L = state.lang;
  const panel = $("#explain-panel");
  const paths = [
    "nldt/recipes/*.json",
    "nldt/recipes/edic-asset-map.json",
    "marketplace/data/catalog.json",
    "marketplace/data/recipes/*.json",
  ];
  panel.innerHTML = `
    <div class="detail-top">
      <div>
        <p class="eyebrow">${escapeHtml(t("heroEyebrow", L))}</p>
        <h2>${escapeHtml(t("explainTitle", L))}</h2>
      </div>
      <button type="button" class="icon-btn" id="explain-close" aria-label="${escapeHtml(t("close", L))}">×</button>
    </div>
    <p class="explain-panel-lead">${escapeHtml(t("explainLead", L))}</p>
    <section>
      <h3>${escapeHtml(t("explainRecipesTitle", L))}</h3>
      <p>${escapeHtml(t("explainRecipesBody", L))}</p>
    </section>
    <section>
      <h3>${escapeHtml(t("explainJsonTitle", L))}</h3>
      <p>${escapeHtml(t("explainJsonBody", L))}</p>
      <p class="explain-paths">${paths.map((p) => `<code>${escapeHtml(p)}</code>`).join("")}</p>
    </section>
  `;
  $("#detail-backdrop").classList.add("open");
  panel.classList.add("open");
  $("#explain-close").addEventListener("click", closeExplain);
}

function closeExplain() {
  state.explainOpen = false;
  $("#explain-panel").classList.remove("open");
  if (!state.selected) $("#detail-backdrop").classList.remove("open");
}

function computeKindBadge(processId, L) {
  const { kind, seam } = kindForProcess(processId);
  const labelKey =
    kind === "genai" ? "computeGenai" : kind === "hybrid" ? "computeHybrid" : "computeAlgorithm";
  const hintKey =
    kind === "genai"
      ? "computeGenaiHint"
      : kind === "hybrid"
        ? "computeHybridHint"
        : "computeAlgorithmHint";
  const seamBit = seam ? ` · ${seam}` : "";
  return `<span class="badge compute-${kind}" title="${escapeHtml(t(hintKey, L))}">${escapeHtml(
    t(labelKey, L)
  )}${escapeHtml(seamBit)}</span>`;
}

function renderPipelineHtml(full, L) {
  const steps = Array.isArray(full?.steps) ? full.steps : [];
  if (!steps.length) return "";
  const items = steps
    .map((step, i) => {
      const title = step.title || step.id || step.processId || `${t("workflowStep", L)} ${i + 1}`;
      const proc = step.processId
        ? `<span>${escapeHtml(t("workflowProcess", L))}: <code>${escapeHtml(step.processId)}</code></span>`
        : "";
      const backend = step.backend
        ? `<span>${escapeHtml(t("workflowBackend", L))}: <code>${escapeHtml(step.backend)}</code></span>`
        : "";
      const kindBadge = computeKindBadge(step.processId, L);
      const arrow =
        i < steps.length - 1 ? `<li class="pipeline-arrow" aria-hidden="true">↓</li>` : "";
      return `
        <li class="pipeline-step">
          <span class="pipeline-num">${i + 1}</span>
          <div class="pipeline-body">
            <div class="pipeline-head">
              <p class="pipeline-title">${escapeHtml(title)}</p>
              ${kindBadge}
            </div>
            ${proc || backend ? `<p class="pipeline-meta">${proc}${backend}</p>` : ""}
          </div>
        </li>${arrow}`;
    })
    .join("");
  return `
    <details class="workflow-block">
      <summary>${escapeHtml(t("workflowPipeline", L))}</summary>
      <ol class="pipeline">${items}</ol>
    </details>`;
}

function renderAgentWorkflowHtml(full, L) {
  const service = full?.service;
  if (!service || typeof service !== "object") return "";
  const parties = Array.isArray(service.parties) ? service.parties : [];
  const blueprint = Array.isArray(service.blueprintSteps) ? service.blueprintSteps : [];
  const genAi = Array.isArray(service.genAiTestPoints) ? service.genAiTestPoints : [];
  const human = service.humanMeasure || {};
  const handovers = Array.isArray(human.handover) ? human.handover : [];
  const exceptions = Array.isArray(human.exceptions) ? human.exceptions : [];
  if (!parties.length && !blueprint.length && !genAi.length && !handovers.length && !exceptions.length) {
    return "";
  }

  const partiesHtml = parties.length
    ? `<p class="workflow-sub">${escapeHtml(t("workflowParties", L))}</p>
       <ul class="party-list">${parties
         .map((p) => {
           const name = typeof p === "string" ? p : p.name || "";
           const role = typeof p === "object" && p.role ? ` — ${p.role}` : "";
           return `<li><strong>${escapeHtml(name)}</strong>${escapeHtml(role)}</li>`;
         })
         .join("")}</ul>`
    : "";

  const blueprintHtml = blueprint.length
    ? `<p class="workflow-sub">${escapeHtml(t("workflowBlueprint", L))}</p>
       <p class="pipeline-meta">${blueprint.map((n) => escapeHtml(String(n))).join(" → ")}</p>`
    : "";

  const genAiHtml = genAi.length
    ? `<p class="workflow-sub">${escapeHtml(t("workflowGenAi", L))}</p>
       <ul class="genai-list">${genAi
         .map((g) => {
           const point = g.point || "";
           const desc = g.description || "";
           return `<li><span class="genai-point">${escapeHtml(point)}</span>${escapeHtml(desc)}</li>`;
         })
         .join("")}</ul>`
    : "";

  const humanHtml =
    handovers.length || exceptions.length
      ? `${
          handovers.length
            ? `<p class="workflow-sub">${escapeHtml(t("workflowHuman", L))}</p>
               <ul class="plain-list">${handovers.map((h) => `<li>${escapeHtml(h)}</li>`).join("")}</ul>`
            : ""
        }${
          exceptions.length
            ? `<p class="workflow-sub">${escapeHtml(t("workflowExceptions", L))}</p>
               <ul class="plain-list">${exceptions.map((h) => `<li>${escapeHtml(h)}</li>`).join("")}</ul>`
            : ""
        }`
      : "";

  return `
    <details class="workflow-block">
      <summary>${escapeHtml(t("workflowAgent", L))}</summary>
      ${partiesHtml}${blueprintHtml}${genAiHtml}${humanHtml}
    </details>`;
}

async function loadRecipeSource(recipe) {
  if (!recipe?.path && !recipe?.id) return null;
  const cached = state.recipeCache.get(recipe.id);
  if (cached) return cached;
  try {
    const res = await fetch(recipeJsonHref(recipe), { credentials: "same-origin" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.recipeCache.set(recipe.id, data);
    return data;
  } catch {
    return null;
  }
}

function openDetail(recipe) {
  closeExplain();
  state.selected = recipe;
  const L = state.lang;
  const panel = $("#detail");
  const title = recipeField(recipe, "title", L) || recipe.title || recipe.id;
  const description = recipeField(recipe, "description", L) || recipe.description || "";
  const acceptance = recipeField(recipe, "acceptance", L) || recipe.acceptance || "";
  const app = appText(recipe.id, L) || description || "—";
  const procs = (recipe.requiredProcesses || []).map((p) => `<li><code>${escapeHtml(p)}</code></li>`).join("") || `<li>—</li>`;
  const risk = String(recipe.riskLevel || "").toLowerCase();
  panel.innerHTML = `
    <div class="detail-top">
      <div>
        <div class="recipe-meta">
          <span class="badge">${escapeHtml(strings.themes[recipe.theme]?.[L] || recipe.theme || "")}</span>
          ${risk ? `<span class="badge risk-${risk}">${t("risk", L)} ${escapeHtml(riskLabel(risk, L))}</span>` : ""}
        </div>
        <h2>${escapeHtml(title)}</h2>
      </div>
      <button type="button" class="icon-btn" id="detail-close" aria-label="${t("close", L)}">×</button>
    </div>
    <section>
      <h3>${t("application", L)}</h3>
      <p>${escapeHtml(app)}</p>
    </section>
    ${description ? `<section><h3>${L === "nl" ? "Beschrijving" : "Description"}</h3><p>${escapeHtml(description)}</p></section>` : ""}
    <section>
      <h3>${t("processes", L)}</h3>
      <ul>${procs}</ul>
      <div id="workflow-host"><p class="workflow-loading">${escapeHtml(t("workflowLoading", L))}</p></div>
    </section>
    <section>
      <dl class="kv">
        <dt>${t("owner", L)}</dt><dd>${escapeHtml(recipe.owner || "—")}</dd>
        <dt>${t("readiness", L)}</dt><dd>${escapeHtml(readinessLabel(recipe.readiness, L) || "—")}</dd>
        <dt>EDIC</dt><dd>${escapeHtml(recipe.edic || "—")}</dd>
        <dt>ID</dt><dd><code>${escapeHtml(recipe.id)}</code></dd>
      </dl>
    </section>
    ${acceptance ? `<section><h3>${t("acceptance", L)}</h3><p>${escapeHtml(acceptance)}</p></section>` : ""}
    ${recipe.path ? `<section><h3>${t("sourceJson", L)}</h3><p><a class="json-link" href="${escapeHtml(recipeJsonHref(recipe))}" target="_blank" rel="noopener">${escapeHtml(recipe.id)}.json</a></p><pre class="json-preview" id="json-preview" hidden></pre><button type="button" class="btn btn-ghost" id="json-preview-btn">${L === "nl" ? "Toon JSON hier" : "Show JSON here"}</button></section>` : ""}
  `;
  $("#detail-backdrop").classList.add("open");
  panel.classList.add("open");
  $("#detail-close").addEventListener("click", closeDetail);
  const previewBtn = $("#json-preview-btn");
  if (previewBtn) {
    previewBtn.addEventListener("click", () => toggleJsonPreview(recipe));
  }
  history.replaceState(null, "", `#${encodeURIComponent(recipe.id)}`);
  fillWorkflow(recipe);
}

async function fillWorkflow(recipe) {
  const host = $("#workflow-host");
  if (!host || state.selected?.id !== recipe.id) return;
  const full = await loadRecipeSource(recipe);
  if (state.selected?.id !== recipe.id) return;
  if (!full) {
    host.innerHTML = "";
    return;
  }
  const L = state.lang;
  host.innerHTML = `${renderPipelineHtml(full, L)}${renderAgentWorkflowHtml(full, L)}`;
}

/** Always /…/marketplace/data/recipes/<file> — ignores missing trailing slash and #hash. */
function marketplaceBaseUrl() {
  // Always build from origin (no userinfo) so Basic Auth in the address bar
  // does not break fetch. Prefer /marketplace/ when that path is present;
  // otherwise use the directory of the current page (Fly serves at /).
  const { origin, pathname } = window.location;
  const marker = "/marketplace";
  const idx = pathname.indexOf(marker);
  if (idx >= 0) {
    return `${origin}${pathname.slice(0, idx)}${marker}/`;
  }
  const dir = pathname.endsWith("/")
    ? pathname
    : pathname.replace(/\/[^/]*$/, "/") || "/";
  return `${origin}${dir}`;
}

function recipeJsonHref(recipe) {
  const name =
    (recipe.path || "").split("/").filter(Boolean).pop() || `${recipe.id}.json`;
  return `${marketplaceBaseUrl()}data/recipes/${name}`;
}

async function toggleJsonPreview(recipe) {
  const pre = $("#json-preview");
  const btn = $("#json-preview-btn");
  if (!pre || !btn) return;
  if (!pre.hidden && pre.dataset.loaded === "1") {
    pre.hidden = true;
    btn.textContent = state.lang === "nl" ? "Toon JSON hier" : "Show JSON here";
    return;
  }
  try {
    const res = await fetch(recipeJsonHref(recipe), { credentials: "same-origin" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const text = await res.text();
    try {
      pre.textContent = JSON.stringify(JSON.parse(text), null, 2);
    } catch {
      pre.textContent = text;
    }
    pre.dataset.loaded = "1";
    pre.hidden = false;
    btn.textContent = state.lang === "nl" ? "Verberg JSON" : "Hide JSON";
  } catch (err) {
    pre.textContent = String(err.message || err);
    pre.hidden = false;
  }
}

function closeDetail() {
  state.selected = null;
  $("#detail").classList.remove("open");
  if (!state.explainOpen) $("#detail-backdrop").classList.remove("open");
  if (!state.explainOpen) {
    history.replaceState(null, "", location.pathname + location.search);
  }
}

function closePanels() {
  closeDetail();
  closeExplain();
  $("#detail-backdrop").classList.remove("open");
  history.replaceState(null, "", location.pathname + location.search);
}

async function loadCatalog() {
  // Use origin-based URL so Basic Auth credentials in the address bar
  // do not break fetch ("URL that includes credentials").
  const res = await fetch(`${marketplaceBaseUrl()}data/catalog.json`, {
    credentials: "same-origin",
  });
  if (!res.ok) throw new Error("catalog.json missing");
  const data = await res.json();
  state.recipes = data.recipes || [];
}

function wire() {
  $("#btn-nl").addEventListener("click", () => setLang("nl"));
  $("#btn-en").addEventListener("click", () => setLang("en"));
  $("#btn-explain").addEventListener("click", () => openExplain());
  $("#search").addEventListener("input", (e) => {
    state.query = e.target.value;
    renderGrid();
  });
  $("#detail-backdrop").addEventListener("click", closePanels);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closePanels();
  });
}

async function main() {
  wire();
  setLang(state.lang);
  await loadCatalog();
  renderChips();
  renderGrid();
  const hash = decodeURIComponent(location.hash.replace(/^#/, ""));
  if (hash) {
    const recipe = state.recipes.find((r) => r.id === hash);
    if (recipe) openDetail(recipe);
  }
}

main().catch((err) => {
  console.error(err);
  $("#grid").innerHTML = `<p class="empty">Failed to load catalogue: ${escapeHtml(err.message)}</p>`;
});
