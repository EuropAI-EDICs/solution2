# Ontwerp — HITL mens-agent-grens: interrupt, dashboard-resume en leerstaat (poort 3, B8)

| | |
|---|---|
| **Datum** | 7 oktober 2026 |
| **Status** | **goedgekeurd door Marc ("akkoord", 2026-10-07)** — inclusief de twee open punten, nu besloten: interrupt-punt = alléén de `run_bp2op_transform`-submit; verdict-zonder-opmerking wordt geweigerd. Eerder bevestigd uit de sessie: **minimale kern** en **dashboard-resume via live_server** |
| **Scope** | poort 3 aantoonbaar end-to-end voor de eerste instantie: de deep-agents-agent interrupt op de toestandswijzigende bp2op-submit-tool, de mens beslist via dashboardknoppen (approve/reject + opmerking), het verdict landt in journal én leerstaat (decision-trail). Resume over procesgrenzen via een persistente SqliteSaver-checkpointer |
| **Buiten scope** | boundary-records per workflow-stap (B8-volledig, fase C-rest) · poort-3/4-critic-checks (juridische bevoegdheidskaart, vervangbaarheidsaudit) · per-regel jurist-goedkeuring in het bp2op-rapport · andere subagents dan eindhoven-bp2op · EN-demo · cloud-checkpointers |
| **Bronnen** | beslispunt 7 AGENTIC_STATE_PLAN v1.2 (besloten: a/HITL) · fase C van dat plan (interrupt_on, bp2op als eerste V4-gated instantie) · [`nldt/07-trust-and-governance.md`](../../nldt/07-trust-and-governance.md) §Human-in-the-loop (triggers: `requiresHitl`, `riskLevel: high`, verdict `needs_human`; `--auto-approve-hitl` als dev-flag) · deepagents 0.7.x (`HumanInTheLoopMiddleware`, `interrupt_on`, resume via `Command`) · bestaan: `deep-agents/pocs.py` (eindhoven-subagent), `nldt/services/mcp_servers/poc_server.py:197` (`run_bp2op_transform`), `poc-bp2op/pipeline/critic.py:30` (V4-hardcode "pending"), `deep-agents/journal.py` (vrije kind-strings), `nldt/services/memory/` (leerstaat, observationtype `hitl_needs_human` bestaat) · MC-6 (VNG-methode): niets wordt door AI gekoppeld; de jurist beslist |
| **Keuzes uit de sessie** | scope: **minimale kern** (niet volledige fase C, niet alleen-orchestrator) · resume-oppervlak: **dashboard-knoppen via live_server** (niet terminal, niet read-only) · aanpak: **SqliteSaver + resume-proces** boven langlopend polsend proces (voorgesteld) · interrupt-punt: **alleen de koppel/transform-submit** conform MC-6 (voorpstel, onbeantwoord) |

## Context en doel

Het beslispunt 7 is besloten: de volgende stap is HITL/mens-agent-grens (lagen 2, 10 en 12 van
het whitepaper-kader; Sitra B8, poort 3). De verkenning bevestigt de witte plek: de geïnstalleerde
deepagents-versie ondersteunt `interrupt_on` maar nergens in het repo wordt het gebruikt;
`deep-agents/agent.py` bouwt de agent zonder interrupts; de V4-mens-wachtpositie bestaat alleen
als hardcode in de bp2op-critic (`"V4_human": "pending"` — pending telt als voldoende); en er is
geen pad waarop een mens ooit daadwerkelijk een agent-beslissing bevestigt of weigert tijdens een
run. Doctrine en infrastructuur zijn er wél: `nldt/07` beschrijft de triggers en de
dev-flag, het journal accepteert willekeurige event-kinds, en de leerstaat heeft al het
observationtype `hitl_needs_human` — maar zonder echte bron.

Dit ontwerp levert de minimale kern die poort 3 **aantoonbaar** maakt: een echte interrupt, een
menselijke beslissing met verantwoording, en een verdict dat in de leerstaat belandt. De
kernoverweging uit de slides blijft leidend: de mens is de laatste schakel — nu als mechanisme,
niet als slogan.

## 1. Architectuur — SqliteSaver + resume-proces

Het dashboard-oppervlak is gekozen; dat dwingt de architectuur. live_server spawnt per run een
subprocess (`live.py`); resume-over-HTTP kan niet in datzelfde proces. Daarom krijgt de graf een
**persistente checkpointer** (`SqliteSaver`):

1. De run stroomt via `graph_trace.run_streamed` zoals nu; bij de geconfigureerde tool-call
   komt een `__interrupt__`-chunk terug.
2. De runner schrijft een journal-event `hitl_request` (tool, samenvatting van de arguments,
   thread_id) en een pending-regel in `steps.jsonl`, en eindigt netjes — de graf-state staat in
   de checkpointer op schijf.
3. Het dashboard toont de pending-kaart (tool, samenvatting, opmerkingveld, knoppen
   Goedkeuren/Afkeuren).
4. Bij een verdict spawnt live_server een **resume-proces** (`resume.py`, nieuw en klein):
   laadt graf + checkpointer op dezelfde thread_id, geeft `Command(resume={"approved": …,
   "comment": …})`, en streamt het vervolg naar hetzelfde `steps.jsonl`.
5. Journal-event `hitl_verdict` (approved/rejected, comment, operator, thread_id); de leerstaat
   pakt het op (§3).

Waarom niet een langlopend polsend run-proces: een server-restart maakt dat run wees en het
doorbreekt het bestaande stop=terminate-model. State op schijf is herstart-proof en past bij de
repo-doctrine van herdraadbare artefacten.

## 2. Componenten

| Onderdeel | Verantwoordelijkheid |
|---|---|
| `deep-agents/agent.py` | `build_agent` krijgt een checkpointer-parameter en geeft `interrupt_on={"run_bp2op_transform": …}` mee aan `create_deep_agent`. Zonder MCP-tools is de tool afwezig en is de config een no-op (veilig) |
| `deep-agents/graph_trace.py` | `__interrupt__`-chunk afvangen: `hitl_request` in het journal + pending-regel in `steps.jsonl`; daarna de stream netjes beëindigen (exit-code die "pending" onderscheidt van ok/fout) |
| `deep-agents/resume.py` (nieuw) | resume-proces: checkpointer + thread_id laden, `Command(resume=…)` geven, verder streamen naar hetzelfde `steps.jsonl`; exit-code onderscheidt voltooid/fout |
| Checkpointer | `SqliteSaver` onder `deep-agents/runs/live/checkpoints.sqlite` (valt onder het gitignored data-regime van `runs/`) |
| `deep-agents/live_server.py` | `GET /api/hitl/pending` (leest pending-regels uit de checkpointer/journal, herstelt na herstart); `POST /api/hitl/verdict` (valideert: pending bestaat, opmerking niet-leeg; spawnt resume-proces); minimale UI: pending-kaart met knoppen en opmerkingveld |
| `deep-agents/journal.py` | geen schemawijziging — nieuwe kinds `hitl_request` / `hitl_verdict` via de bestaande generieke `append(kind, agent, summary, **extra)` |
| Leerstaat (`nldt/services/memory/`) | het observationtype `hitl_needs_human` krijgt het deep-agents-journal als echte bron (extractor-uitbreiding): elk interrupt wordt een trail (status `open`), het besluit zet `handled` met `didItHelp` = de opmerking |
| `--auto-approve-hitl` | blijft bestaan als dev/offline-flag (doctrine `nldt/07`): auto-approve noteert in het journal dat de goedkeuring machinaal was — nooit zichtbaar als menselijke beslissing |

**Interrupt-punt (voorpstel):** alléén `run_bp2op_transform` — de toestandswijzigende actie
(conform MC-6: de jurist beslist over koppelen). Leesbare calls (catalog-search, recipe-read,
describe_process) lopen zonder onderbreking. Het per-regel goedkeuren van koppelkandidaten in
het bp2op-rapport is bewust buiten scope; de agent-niveau-goedkeuring is de eerste, aantoonbare
mens-agent-grens.

## 3. Verdict-data en afkeur-semantiek

Verdict-payload: `{approved: bool, comment: string (verplicht, niet-leeg), operator: string,
thread_id, tool, ts}`. De verplichte opmerking is de leerstaat-koppeling: "wie beslist" zonder
toelichting is geen trail-waardig signaal.

**Afkeuren:** de tool wordt niet uitgevoerd; de agent vervolgt met het afgewezen-verdict in
context en het dossier blijft V4-pending mét geregistreerde afwijzing. Er is geen pad waarop
een afwijzing onzichtbaar is: journal, steps.jsonl en trail dragen het alle drie.

**Goedkeuren:** de transform draait; V4 blijft pending-by-design in het artifact (critic.py
ongewijzigd) — de dashboard-goedkeuring is de agent-niveau-grens, niet de V4-jurist-toets.

## 4. Foutgedrag

- **Server-restart met pending interrupt:** pending-kaart keert terug uit de schijf
  (checkpointer + journal); geen verlies, geen auto-resume.
- **Geen time-out die goedkeurt:** een open pending blijft open tot een mens beslist — de mens
  is de laatste schakel, ook in de foutpaden.
- **Tweede verdict op dezelfde pending:** geweigerd (409); de pending is na het eerste verdict
  verbruikt.
- **Resume-proces faalt (crash, model onbereikbaar):** pending blijft staan in het dashboard met
  foutmelding; de operator kan opnieuw beslissen (nieuwe resume-poging).

## 5. Testen

Offline unittests (standaardsuite, LLM-vrij en snel): interrupt treedt op bij
`run_bp2op_transform` en niet bij leesbare tools · resume met approve voert de tool uit en
resume met reject slaat hem over · journal draagt `hitl_request`/`hitl_verdict` met de juiste
payload · pending-queue herstelt na gesimuleerde herstart · dubbel verdict wordt geweigerd ·
`--auto-approve-hitl` markeert machinale goedkeuring in het journal. Plus één `llm`-marker-test
voor de volledige agent-loop met lokaal LLM (volgt het bestaande S1/S7-patroon; zonder lokaal
endpoint geskipt). De eisen aan testoutput zijn streng: geen warnings, geen ruis.

## 6. Verificatie-eis aan het implementatieplan

Eén ding is in dit ontwerp bewust niet gepind: de exacte toolnaam waaronder de MCP-tool in de
subagent terechtkomt (`run_bp2op_transform` volgens `poc_server.py:197`) en hoe
`interrupt_on` op subagent-niveau doorwerkt in deepagents 0.7.x (tool-matching over subagent-grenzen).
Het implementatieplan opent met een verificatietaak die beide in de geïnstalleerde
deepagents-versie bevestigt vóór er gebouwd wordt; wijkt de realiteit af, dan gaat de afwijking
terug naar deze spec.

## Open punten (voor Marc)

1. **Interrupt-punt bevestigen** — alleen de `run_bp2op_transform`-submit (voorstel) dan wel
   álle bp2op-tool-calls of een configureerbare lijst per subagent.
2. **Verplichte opmerking bevestigen** — verdict zonder opmerking weigeren (voorstel) dan wel
   een lege opmerking toestaan (verzwakt de leerstaat).
