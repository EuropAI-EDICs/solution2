# Method cards — the "Amsterdams model" for bestemmingsplan → omgevingsplan conversion with AI

Primary source: VNGemeenten, *Netwerksessie VTH en omgevingsplan — "van bestemmingsplan naar
omgevingsplan met AI"* (19 juni 2026), speaker Peter Lans (regisseur omgevingswet, gemeente
Amsterdam; tool: **Plangids**, built by Amsterdam's AI Lab / innovation department).
[`vng-netwerksessie-19jun2026-transcript.txt`](vng-netwerksessie-19jun2026-transcript.txt) is the
full ASR transcript (auto-captions, 67 min); timestamps below refer to it. Video:
https://www.youtube.com/watch?v=PRLrYWnLrcg

Projection target of this PoC: **gemeente Eindhoven** (gm0772) — its real, current conversion
challenge: old bestemmingsplannen live on as the *tijdelijk deel* of the
Omgevingsplan gemeente Eindhoven (CVDR696400), TAM-omgevingsplannen convert areas one by one,
and the 1-1-2032 deadline applies (art. 4.9 Invoeringswet Omgevingswet). Exactly the situation
the recorded methods address.

Each card below is **traceable**: `MC-x` ids are cited in the run artifacts (`methodTrace` in the
omzettabel, coverage report, validation report and HTML report) so every pipeline feature can be
traced back to the recorded method that motivated it.

---

## MC-1 · Transitiestrategie met doelregeling (regelbibliotheek)
**[02:31–05:31, 06:33–07:33]** Amsterdam converts against a uniform rule library — the
*hoofdregeling* (formerly *basisregeling*): new, uniformed omgevingsplan rules covering ~80% of
what is needed (spatial rules replacing BP rules + the *bruidschat* with doorwerking of
instructieregels), written up front by jurists as one integrated library. Existing BP rules are
matched to it ("welke regel vervangt wat"). Missing rules are added to the library **first**, as a
separate decision with a dummy location ("een vierkante millimeter in het eieren", 08:09–08:47),
so the rule exists before the plan that needs it is converted.
→ *PoC:* the doelregeling index = Omgevingsplan gemeente Eindhoven (CVDR696400, geldend
29-06-2026); the coverage analyser flags rules that require doelregeling extension first (MC-8).

## MC-2 · Beleidsneutraal omzetten
**[05:59–06:31, 15:44–16:31, 60:44–61:45]** The conversion itself carries no policy change —
first "beleidsarm", sharpened to "beleidsneutraal": convert the *geldende* rules for the area
(BP rules, geldende paraplu rules, local policy where clearly translatable, new-law terminology,
afwijkingsvergunningen, kennelijke fouten) without changing them. Policy discussions
(wegbestemmen, inperken, nadeelcompensatie) are deliberately run as **separate tracks**.
→ *PoC:* the conversion request pins `beleid: "neutraal"`; rows never invent new policy; anything
that would change policy is routed to human review (`needs_human`), never auto-mapped.

## MC-3 · De omzettabel as the core work artifact
**[20:13–21:04, 28:44–30:06]** The conversion is done in an *omzettabel* (conversion table):
left column the verbatim bestemmingsplanregel (which plan, which article, the rule text, where it
applies, its beperkingen); right column the doelregeling rule(s) that replace it, with
toelichting. A mixed bestemming (wonen + detailhandel + maatschappelijke dienstverlening) maps to
**multiple** activities on the location — activiteiten stapelen — so one BP rule may map to
several OP rules.
→ *PoC:* `omzettabel-row` contract + omzettabel.json/md + the HTML table; rows are 1-to-n by
design.

## MC-4 · Automatisch inlezen en opknippen
**[21:07–21:44, 24:25–26:55, 30:34–30:49]** Step 1 of the AI support: read the bestemmingsplannen
in automatically and split them into individual rules (previously colleagues cut-and-pasted
planregels into Excel by hand). Extraction works "best wel goed" for structured plans, but PDF
bestemmingsplannen are genuinely hard — **validation stays always necessary**. The tool takes its
input from the DSO "regels op de kaart" overbruggingsfunctie per location (41:04–41:33).
→ *PoC:* deterministic parsers read the official Eindhoven publications (CVDR HTML, Gemeenteblad
HTML) and split them into artikel/lid-level rules with verbatim quotes; nothing is invented; the
loader records document + versie + URL per rule. (LLM hook is pluggable but off by default.)

## MC-5 · Kennisbank met hergebruik en match-scores
**[21:21–21:44, 23:41–24:12, 33:13–34:58]** Step 2: earlier omzettingen are stored as a kennisbank;
new BP rules get **suggestions** ("andere klanten kochten ook") with an explicit match score
("negen resultaten … 90 tot 70%"), one button "koppel deze regel". Because the omgevingsplan
structure is complex with internal doorverwijzingen, the AI **suggests** — it does not
autonomously couple; it improves as more conversions land.
→ *PoC:* `kennisbank-pair` contract seeded from Eindhoven's own published replacement relations
("komt in de plaats van", gmb-2025-226538: 275 relations) + the gebruiksdoel taxonomy; a
deterministic Dutch-aware similarity matcher (TF-IDF cosine over unigrams+bigrams) produces
scored suggestions in the same bands (≥90 / 70–90 / <70); every suggestion keeps status
`voorgesteld` — coupling is a human act.

## MC-6 · Mens blijft op de knoppen (jurist als sluitstuk)
**[26:07–26:21, 35:25–35:45, 64:38–64:56]** "Het is altijd een mens; de tooling moet
ondersteunen maar kan nooit overnemen." No press-button-and-done; the lawyer is the closing
piece; explicit discussion of hallucination risk (34:44–35:01) and of the hope that case law
("beroep tegen zo'n beleidsneutraal wijzigingsbesluit") will settle the uitzonderingspositie.
→ *PoC:* rows carry review states; V4 (human checkpoint) is a first-class, always-pending
validation level; nothing leaves the pipeline marked `gekoppeld` except seeded pairs that cite
the official publication that established them.

## MC-7 · Controleerbaarheid: context, toelichting, geschiedenis
**[34:23–37:26]** Converters must see each rule **in context** — click through to the full
bestemmingsplan on the loket and to the current version of the doelregeling — must be able to add
per-row toelichting ("bestemmingsvlak alleen aan de westzijde"), and every row has a
wijzigingsgeschiedenis (who changed what). View-only roles exist for plantekenaars.
→ *PoC:* every bron/doel regel carries a deep link (CVDR anchor / bekendmaking permalink) and a
verbatim quote; rows have a toelichting field and an audit trail; the report shows both sides
side-by-side.

## MC-8 · Bulk-analyse voor planning (de "Plangids-analyse")
**[54:43–55:43]** Doorontwikkeling explicitly described: read **all** BP rules in bulk, match
them against the doelregeling, and report per **plan** how many matches exist — "hoe goed past de
hoofdregeling; is de hoofdregeling toegerust om een bepaald bestemmingsplan om te zetten, of
moet ik nog nieuwe regels toevoegen?" Deviating plans are filtered to do later, missing rule
types feed doelregeling extensions.
→ *PoC:* `coverage-report` contract + analyser ranks the Eindhoven plan portfolio by
conversie-gereedheid (match-rate bands, needs-new-rule clusters) from the Planviewer inventory.

## MC-9 · Procesontwerp rondom de tool
**[09:04–17:26, 22:31–23:20]** Measured baseline: 6 pilot plans, >1000 h/plan → ~450 FTE for 530
plans by 2032 — impossible; with the tool the pilot ran ~20× faster (23:08–23:17). Process
changes: stop participatie and nota van uitgangspunten for beleidsneutrale omzettingen, one
standard intro per wijzigingsbesluit, delegate the wijzigingsbesluit from council to college,
shrink the stadsdeel role. Pilot selection criteria: no pending policy change (horeca), laagdynamische
gebieden, similar (woongebieden), sometimes only part of a plan area (13:17–13:31).
→ *PoC:* the conversion request encodes pilot-selection criteria (object types, dynamics, partial
areas); the run summary records the measured effort argument (Amsterdam numbers, quoted) as the
business case context.

## MC-10 · Input-kwaliteit en stapeling (de Critical push-back)
**[60:00–63:20]** The sharpest recorded criticism (Deflin): a tool cannot fix bad input — if the
old plans are not in order you re-import the archaeology of double bestemmingen; and conversions
must **stack**: a postzegelplan that weg-bestemde one of ten bedrijfsbestemmingen means the
moederplan conversion must carry nine bedrijven + the apartment complex, not ten + apartments —
overlay the current planologische-juridische kader, take afwijkingsvergunningen along.
→ *PoC:* every bron regel records its document lineage; the loader tags postzegelplan/TAM overlay
relations where published evidence exists; rows that would double-count stacked rules are flagged
`needs_human` with the stacking note; input-quality caveats are first-class in the report.

## MC-11 · Werkingsgebieden zijn (nog) geen AI
**[37:28–38:11, 45:30–46:18]** Werkingsgebieden/geometry are **not** in the Amsterdam tooling:
geometry barely changes when rules swap ("je wisselt alleen de regels"), it is *robotisering*
rather than AI, and it was not the priority. Annotation happens in the plan software (Roxit) when
the result is taken over, not in the matching tool.
→ *PoC:* deliberately no geometry engine here; documented as a method-faithful scope choice with
the quote; the artifact format keeps a `werkingsgebiedRef` placeholder for the robotisering step.

## MC-12 · Kwaliteitsborging van de tool zelf
**[52:53–54:13]** QA of the tool itself: architecture & service management review, algoritmeregister
entry, risicoclassificatie, handboek (who may/where/why), privacy quickscan, pen/hack test — the
complete standard set for using an AI tool in a public process. Model choice: a European model,
not the big US ones (copyright position + Dutch legal text quality) [30:49–31:41].
→ *PoC:* the run summary embeds a self-assessment checklist mapped to these items; the pipeline
itself is deterministic and offline by default (no data leaves the machine), which the checklist
records as the PoC's own control.

---

## Numbers recorded (for the business case panel)

| quantity | value | source |
|---|---|---|
| bestemmingsplannen Amsterdam | 530 | [02:34] |
| deadline | 2032 | [02:48] |
| measured effort, first 6 plans | >1000 uur/plan | [10:08–10:17] |
| implied capacity | ≈450 FTE tot 2032 | [10:22–10:47] |
| pilot speed-up with tool | ≈20× | [23:08–23:17] |
| build effort | ~1.5 jaar, ~€300k, in-house | [43:19–43:55] |
| doelregeling coverage | ~80% | [04:15] |

## Secondary sources (context verification)

- omgevingsweb.nl — *Van bestemmingsplan naar omgevingsplan met AI: hoe Amsterdam de grootste
  planologische operatie van Nederland versnelt*.
- theinnovativelawyer.ai — *Amsterdam zet honderden bestemmingsplannen om met AI en houdt de
  jurist als sluitstuk*.
- openresearch.amsterdam — *AI & omgevingswet: prototype & pilot* / *vraagverkenning*.
- platformaioverheid.nl — Track AI leefomgeving breakout 1C (Amsterdam AI/omgevingswet).
- iplo.nl — *Einde TAM-IMRO per 1 januari 2026* (TAM = tijdelijke alternatieve maatregel,
  art. 4.9a Invoeringswet Omgevingswet).
