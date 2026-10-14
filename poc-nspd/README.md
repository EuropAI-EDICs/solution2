# poc-nspd — North Sea Port District (grensoverschrijdend scenario-POC + Leia-viewer)

Spec: `docs/superpowers/specs/2026-10-14-poc-nspd-design.md` · Plan: `docs/superpowers/plans/2026-10-14-poc-nspd.md`
Status: **in aanbouw (fase 1)**. Pipeline: kopie/adapt van `poc/`; jurisdicties nl+be; viewer: Leia-submodule (`viewer/`, MIT, zie viewer/README.md).

## viewer/ — Leia (git-submodule, ongepatched)

Upstream: https://github.com/leia-project/viewer (MIT) · Gepind op commit: 73510022e708bc1042a4fd0e88cec27e4857434d
Start: `npm install && npm run dev -- --port 5173` (of Docker volgens upstream-README).
Config: Leia leest `?url=http://localhost:8000/nspd.config.json` — viewer-data/ wordt door
`make_viewer_config.py` geschreven en geserveerd met
`python3 -m http.server 8000 -d ../viewer-data` (vanuit viewer/).
Deze POC wijzigt géén Leia-broncode; alleen JSON-config + laagbestanden.
(pin-info hier in poc-nspd/README.md omdat viewer/ een onaangetaste submodule is —
zie viewer/README.md daar voor de upstream-documentatie)
