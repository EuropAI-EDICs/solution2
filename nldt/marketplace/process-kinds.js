/**
 * Compute kind per OGC processId (GENAI_SEAMS / process handlers).
 * algorithm = deterministic code only
 * genai     = may call an LLM (optional or primary propose path)
 * hybrid    = deterministic floor + LLM explorer (AI proposes, pipeline disposes)
 */

/** @typedef {'algorithm' | 'genai' | 'hybrid'} ComputeKind */

/** @type {Record<string, { kind: ComputeKind, seam?: string }>} */
export const PROCESS_KINDS = {
  "fetch-features": { kind: "algorithm" },
  "spatial-intersection": { kind: "algorithm" },
  "compute-area-statistics": { kind: "algorithm" },
  "h3-polygon-to-cells": { kind: "algorithm" },
  "h3-spatial-join-points": { kind: "algorithm" },
  "h3-morans-i": { kind: "algorithm" },
  "h3-knn": { kind: "algorithm" },
  "h3-grid-disk": { kind: "algorithm" },
  "h3-cells-to-geojson": { kind: "algorithm" },
  "validate-artifact": { kind: "algorithm" },
  "opportunity-map-run": { kind: "algorithm" },
  "scenario-sweep": { kind: "algorithm" },
  "crosstrack-overlay": { kind: "algorithm" },
  "world-scene-build": { kind: "algorithm" },
  "breda-scan-run": { kind: "algorithm" },
  "breda-gebiedsafweging": { kind: "algorithm" },
  "rijnland-peil-conflict": { kind: "algorithm" },
  "rijnland-peil-whatif": { kind: "algorithm" },
  "bp2op-transform": { kind: "algorithm" },
  "minigim-gebiedscheck-run": { kind: "algorithm" },
  "hcs-life-event-run": { kind: "algorithm" },
  "hcs-recipe-run": { kind: "algorithm" },
  "timeseries-ingest-run": { kind: "algorithm" },
  "donl-harvest-run": { kind: "algorithm" },
  "lake-publish-dataset": { kind: "algorithm" },
  "source-monitor-probe": { kind: "algorithm", seam: "SM" },
  // GenAI seams — model may propose; never decides alone
  "breda-scan-query": { kind: "genai", seam: "S4" },
  "scenario-author-propose": { kind: "hybrid", seam: "S7" },
};

/** @param {string | undefined} processId */
export function kindForProcess(processId) {
  if (!processId) return { kind: "algorithm" };
  return PROCESS_KINDS[processId] || { kind: "algorithm" };
}
