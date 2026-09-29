# nLDT simulations

Static visualisations for **every** governed PoC — not only Utrecht.
Open via `file://` or `python3 -m http.server` from this directory.

## Hub

[`index.html`](index.html) — per-PoC sections with story, agent flow, and related demos.

## Per PoC

| PoC | Story | Agent flow | Extra demos |
|-----|-------|------------|-------------|
| **Breda** | [`poc-breda.html`](poc-breda.html) | [`breda-flow-demo.html`](breda-flow-demo.html) | [`breda-report-demo.html`](breda-report-demo.html) (Leaflet scan) · [`breda-whatif-demo.html`](breda-whatif-demo.html) · tour `?poc=breda` |
| **Utrecht** | [`poc-utrecht.html`](poc-utrecht.html) | [`utrecht-flow-demo.html`](utrecht-flow-demo.html) | [`utrecht-whatif-demo.html`](utrecht-whatif-demo.html) (Plane B copilot) · Building/3D/GIS overlay/mock/web3d + `?poc=utrecht` |
| **Rijnland** | [`poc-rijnland.html`](poc-rijnland.html) | [`rijnland-flow-demo.html`](rijnland-flow-demo.html) | [`rijnland-whatif-demo.html`](rijnland-whatif-demo.html) (Leaflet) + `?poc=rijnland` |
| **Eindhoven** | [`poc-eindhoven.html`](poc-eindhoven.html) | [`eindhoven-flow-demo.html`](eindhoven-flow-demo.html) | [`eindhoven-report-demo.html`](eindhoven-report-demo.html) · tour `?poc=eindhoven` |

## Architecture tour

[`poc-mcp-skills.html`](poc-mcp-skills.html) — layers, Play tours (lifecycle, router, all four PoCs), Recipes catalogue.  
Deep-link: `?poc=breda|utrecht|rijnland|eindhoven|lifecycle|router`.

## Utrecht platform demos (also linked from Utrecht section)

| Demo | File |
|------|------|
| Building + zoning plan | `building-agent-demo.html` |
| Agent + 3D BAG | `agent-3d-demo.html` |
| GIS overlay agent flow | `agent-flow-demo.html` |
| Overlay mock | `mock-overlay-demo.html` |
| 3D BAG viewer | `web3d-viewer.html` |

## Opening

```bash
cd nldt/simulation
python3 -m http.server 8090
# → http://127.0.0.1:8090/
# → http://127.0.0.1:8090/rijnland-whatif-demo.html
```

Design: [`docs/superpowers/specs/2026-09-20-nldt-simulations-all-pocs-design.md`](../../docs/superpowers/specs/2026-09-20-nldt-simulations-all-pocs-design.md).
