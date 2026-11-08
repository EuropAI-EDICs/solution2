# Plan — Tab 7: STTR toepast (vierde laag)

Design: [2026-11-08-sttr-toepast-tab7-design.md](../specs/2026-11-08-sttr-toepast-tab7-design.md)

- [x] 1. `build_dso_kb()` leest `rtr.json`/`sttr.json` per instrument → `sttr`-veld (null / onvolledig / volledig) + samenvattingsprint.
- [x] 2. template: kop7 NL+EN en `kb7-titel` naar vier lagen; `VSTAGES7` + nieuwe stage 4; `kb7InstCard`-derde statuslijn; nieuwe `kb7-sttrcard` + `buildStatic7`/`kb7SttrCard()`; makeSim7-logs met gouden getallen; footer-regel.
- [x] 3. Hub herbouwd (`simulation/build_simulation.py`) en gecontroleerd: markers aanwezig, prints kloppen met de gouden getallen uit de design-spec.
- [x] 4. Kansen-notitie kans 1 bijgewerkt (Update: Tab 7 toont drie statussen) en gecommit.
