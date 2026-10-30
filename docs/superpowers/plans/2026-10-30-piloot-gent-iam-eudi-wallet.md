# Piloot Gent IAM — EUDI-wallet (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Geef de H2-authenticatie (het IAM-stuk) van `poc-gent/` een EUDI-wallet-route naast de bestaande ACM/IDM-mock, conform de repo-walletdoctrine [`nldt/16-eid-wallet-identity.md`](../../../nldt/16-eid-wallet-identity.md): wallet-presentatie met **selectieve onthulling** (data-minimalisatie), **LoA-gate per dienst** (`minLoa` als contractveld in het pakketmanifest), machtigingen uit een wallet-attestatie, en ACM/IDM als expliciete **fallback** (vrije uitweg, FR-02-geest). Dekt FR-09/INT-01 (authenticatie pas bij nodig pad, met uitleg) en de DATA-minimalisatielijn; run-artefact en hash-chained events bewijzen welke route liep en welke claims onthuld zijn.

**Architecture:** `adapters/eudi_wallet.py` is een offline, deterministische replay-mock van de relying-party edge (doctrine-optie C: mock-first, pluggable): `presentation_request` (OpenID4VP/DCQL-*vormige* credentials-query + doelbinding + deterministische nonce) → wallet-kant presenteert alléén aangevraagde claims uit attestaties in `fixtures/wallets.json` → RP-kant verifieert tegen lokale vertrouwensankers, fail-closed bij elke afwijking. De claims-vorm volgt `nldt/schemas/wallet-claims.schema.json` (subject_type human; `sub`/`loa`/`roles`; mandaten als Gent-specifieke machtigingsattestatie erbij). `core/pipeline.py` krijgt `auth_methode="eudi"` (standaard) met automatische ACM/IDM-fallback als de persona géén wallet heeft; `core/gates.decide_h2` krijgt een LoA-check vóór de bestaande mandaatcontrole, met `oorzaak: loa | mandaat` zodat de pipeline het juiste blokkadepaad kiest. Run-schema blijft **1.1**: het `auth`-blok krijgt uitsluitend optionele velden (`methode`, `loa`, `onthuldeClaims`) — achterwaarts compatibel; F3-T5 reserveert 1.2 voor submission/documenten/h4.

**Tech Stack:** Python 3.11+ stdlib-only voor `adapters/` en `core/`; `jsonschema` alléén voor run-validatie onder `../nldt/.venv`; pytest.

**Spec:** `nldt/16` (optie C; ARF-alignmentparagraaf: ARF-*vormige* enveloppen in mocks, geen gesimuleerde ARF-requirement-ID's; afwijkingen vastleggen) · Gent-design §5 (stap 5–6: H2, authenticatie alleen bij nodig pad), §6 (integratielaag), §10 (IAM-rij: "goedgekeurd equivalent") · [`2026-10-30-piloot-gent-transactionele-assistent-design.md`](../specs/2026-10-30-piloot-gent-transactionele-assistent-design.md). ARF-notitie: de mock gebruikt OpenID4VP/DCQL-achtige vorm; productie (Belgische EUDI-wallet/itsme-traject, x509_san_dns-client_id, Token Status List, echte LoA-mapping) landt bij de RP-registratie — hier niet gesimuleerd.

## Global Constraints

- Offline en deterministisch: geen muurklok in run-artefact of events; de presentatie-nonce is hash-afgeleid uit (client, doelbinding, query).
- Geen echte persoonsgegevens; de wallet-fixture is synthetisch. De PID-attestatie bevat een `naam`-claim die nóóit aangevraagd wordt — tests bewijzen dat die niet onthuld wordt (selective disclosure).
- Fail-closed adapter: onbekende issuer, onthulling buiten de aanvraag, ontbrekende claim, nonce-mismatch, ongeldig loa → `WalletFout`; géén wallet → `GeenWallet` (signaal voor de ACM/IDM-fallback, geen fout).
- Events blijven waardevrij (SEC-05): `wallet_presentatie` logt loa + claim-namen, nooit sub-waarden; `auth_fallback` logt de reden zonder persoonsgegevens.
- Statuswaarden ongewijzigd; LoA-tekort → `blokkade` + Gentinfo-handover (zelfde patroon als de mandaatblokkade).
- ACM/IDM-pad modelleert géén LoA (mock-beperking; productie-ACM/IDM koppelt zijn eigen waarborg — INT-01). In README gedocumenteerd.
- Schema 1.1 blijft; alleen optionele `auth`-velden erbij (aanvullend, `additionalProperties: false` blijft).
- Commit per taak, conventional commits scope `poc-gent`, Nederlandse samenvatting.

---

### Task 1: Wallet-fixture + EUDI-adapter (presentatie, verificatie, claims)

**Files:**
- Create: `poc-gent/fixtures/wallets.json`
- Create: `poc-gent/adapters/eudi_wallet.py`
- Test: `poc-gent/tests/test_eudi_wallet.py`

**Interfaces:**
- `fixtures/wallets.json`: `{"vertrouwensankers": {"pid": ["itsme-belgie-mock"], "machtiging": ["stad-gent-ebw-mock"]}, "personas": {<personaId>: {"attestaties": [{"type": "pid", "issuer": …, "claims": {"sub", "loa", "naam"}}, {"type": "machtiging", "issuer": …, "claims": {"mandaten": […]}}]}}}` — wallets voor sanne, ahmed, maria, fatima, jeroen, ellen, dirk (loa `substantial`) en wim (loa `low`); nadia ontbreekt expres (fallback-persona). `sub` = pseudoniem uit `identiteiten.json`; ellen krijgt de bewindvoering-machtiging.
- `LOA_ORDER = {"low": 0, "substantial": 1, "high": 2}`; exceptions `WalletFout` (verificatie-/presentatiefouten) en `GeenWallet`.
- `presentation_request(bronnen: list[dict]) -> dict` — ARF-vormige aanvraag: `{"type": "openid4vp.presentation_request", "client_id": "stad-gent-transactieassistent-mock", "doelbinding": bronnen, "credentials_query": [{"credential": "pid", "claims": ["sub", "loa"]}, {"credential": "machtiging", "claims": ["mandaten"]}], "nonce": <sha256-16-hex over client_id+doelbinding+query>}` (deterministisch).
- `presenteer(poc_root, persona_id, request) -> dict` — wallet-kant: onthult per aangevraagd credential alléén de aangevraagde claims; mist de wallet een credential of claim → `WalletFout`; persona zonder wallet → `GeenWallet`.
- `verifieer(poc_root, presentatie, request) -> dict` — RP-kant, fail-closed: nonce-match, elk query-credential aanwezig, onthulde claims ⊆ aangevraagde claims, issuers binnen vertrouwensankers, pid heeft `sub` + geldige `loa`. Retourneert `{"claims": {"subject_type": "human", "sub", "loa", "roles"}, "mandaten": […], "onthuld": ["loa", "mandaten", "sub"]}` (claims-kern conform `nldt/schemas/wallet-claims.schema.json`).
- `authenticate(poc_root, persona_id, bronnen) -> dict` — hele flow; levert de identiteitsweergave voor de pipeline: `{"pseudoniem", "loa", "mandaten", "methode": "eudi-wallet", "onthuldeClaims"}`.

- [ ] **Step 1: falende tests** — `test_eudi_wallet.py`: request is deterministisch en vraagt alleen sub/loa/mandaten met doelbinding; presentatie onthult de nooit aangevraagde `naam` níet; verifieer levert claims + onthuld-lijst; onbekende issuer / onthulling buiten aanvraag / nonce-mismatch / missende loa → `WalletFout`; nadia → `GeenWallet`; claims-kern valideert tegen `nldt/schemas/wallet-claims.schema.json` (exp in de test gevuld); fixture-consistentie: wallet-`sub` == identiteiten-pseudoniem, en elke persona in `personas.json` heeft een wallet óf is nadia.
- [ ] **Step 2: fixture + adapter implementeren**; suite groen. Commit: `feat(poc-gent): EUDI-wallet-mock — ARF-vormige presentaties, selectieve onthulling, vertrouwensankers (IAM)`.

### Task 2: LoA-gate — manifest minLoa (v0.4.0), catalog-validatie, decide_h2-oorzaak

**Files:**
- Modify: `poc-gent/packages/gent-mobiliteit-ondernemer/manifest.json` (services `ontheffing-lez` en `ontheffing-autovrij` krijgen `"minLoa": "substantial"`; version → 0.4.0)
- Modify: `poc-gent/core/catalog.py` (`minLoa`-controle: indien aanwezig ∈ {low, substantial, high})
- Modify: `poc-gent/core/gates.py` (`vereiste_loa(manifest, service_ids)` = hoogste vereiste, default `low`; `decide_h2` checkt wallet-loa vóór mandaat en retourneert `oorzaak: loa | mandaat | geen`)
- Test: `poc-gent/tests/test_gates.py` (+`poc-gent/tests/test_catalog.py`: ongeldig minLoA → PackageError)

- [ ] **Step 1: falende tests** — vereiste_loa = hoogste onder services, `low` zonder declaratie; decide_h2 weigert loa `low` < `substantial` met oorzaak `loa`; accepteert `substantial`; identiteit zónder loa (ACM/IDM-pad) slaat de LoA-check over (bestaande mandaat-tests blijven ongewijzigd geldig); manifest-minLoA-onvalidatie → PackageError.
- [ ] **Step 2: implementeren**; suite groen. Commit: `feat(poc-gent): LoA-gate per dienst — manifest minLoa (v0.4.0) en decide_h2-oorzaak (IAM)`.

### Task 3: Pipeline-integratie — eudi standaard, acmidm-fallback, LoA-blokkade, schema- en golden-uitbreiding

**Files:**
- Modify: `poc-gent/core/pipeline.py` (`auth_methode="eudi"`; wallet-stap `eudi-authenticatie`; `GeenWallet` → event `auth_fallback` + klassiek pad; besluit-oorzaak → `h2-loa-blokkade` naast bestaande `h2-mandaatblokkade`; auth_blok + `methode`/`loa`/`onthuldeClaims`)
- Modify: `poc-gent/schemas/gent-run.schema.json` (auth: optionele `methode` enum ["eudi-wallet", "acm-idm"], `loa` enum, `onthuldeClaims` array; description-aanvulling; schemaVersion blijft 1.1)
- Modify: `poc-gent/fixtures/personas.json` (+wim edge `lage-waarborg`, +nadia edge `geen-eudi-wallet`), `fixtures/identiteiten.json` (+wim, +nadia), `fixtures/magda.json` (+nadia kentekenrecord)
- Modify: `poc-gent/packages/gent-mobiliteit-ondernemer/golden/scenarios.jsonl` (+g9 wim → blokkade, +g10 nadia → gereed)
- Test: `poc-gent/tests/test_pipeline.py` (auth-assert sanne bijgewerkt naar wallet-vorm; +fallback-, LoA-blokkade-, forceringstests), `poc-gent/tests/test_catalog.py` (golden-count 8 → 10)

- [ ] **Step 1: falende tests** — sanne default run: auth_blok methode `eudi-wallet` + loa + onthuldeClaims, stap `eudi-authentic` aanwezig, géén `acm-authenticatie`; wim: status `blokkade`, stap `h2-loa-blokkade`, handover-event; nadia: event `auth_fallback`, methode `acm-idm`; `auth_methode="acmidm"` forceert het klassieke pad; ellen/maria/dirk ongewijzigd; wallet_presentatie-event bevat geen sub-waarde; schema valideert (runs.validate) op alle nieuwe paden.
- [ ] **Step 2: implementeren + fixtures + golden**; eval `10/10`. Commit: `feat(poc-gent): H2-authenticatie via EUDI-wallet — acmidm-fallback, LoA-blokkade, personas wim/nadia, golden g9-g10`.

### Task 4: CLI + README

**Files:**
- Modify: `poc-gent/run.py` (`--auth eudi|acmidm`, default `eudi`; auth-regel in de samenvatting), `poc-gent/README.md` (IAM-sectie: wallet-route, fallback, LoA-gate, mock-beperking ACM/IDM, productiepad)

- Smokes: `python3 run.py --persona sanne` toont `auth: eudi-wallet (loa substantial)`; `--persona wim` → LoA-blokkade + overname; `--persona nadia` → fallback ACM/IDM; `python3 run.py --persona sanne --auth acmidm` → klassiek pad. Commit: `feat(poc-gent): --auth-keuze in CLI; README IAM — EUDI-wallet, fallback en LoA-gate`.

### Task 5: Docsync — F3-planamendement

- Modify: `docs/superpowers/plans/2026-10-30-piloot-gent-f3.md` — T7: personas ilse/hanne → golden **g11–g13** (counttest 10 → 13), suites-aantallen bijgewerkt na IAM-track; T9/zelfcheck: 9 → **11 persona's** in de sim-tab. Commit: `docs: planamendement F3-T7/T9 — golden-nummering en aantallen na IAM-track (EUDI-wallet)`.

## Zelfcheck na afronding (executeur)

1. `cd poc-gent && ../nldt/.venv/bin/python -m pytest tests -q` → alles groen (aantal na Task 3 vastleggen).
2. `python3 eval.py` → `golden: 10/10 geslaagd`, `determinisme: OK`, exit 0.
3. `python3 run.py --persona sanne | head -10` → `auth: eudi-wallet (loa substantial)`; `--persona wim` → LoA-blokkade; `--persona nadia` → fallback; `--auth acmidm` → klassiek.
4. `cd ../simulation && ../nldt/.venv/bin/python build_simulation.py` → gent-regel met 11 persona's; `node verify_static.mjs` → exit 0.
5. Events-ketting geldig op alle nieuwe paden (`verify_chain`).
