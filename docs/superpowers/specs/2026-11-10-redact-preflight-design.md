# Ontwerp — Redact-preflight: on-device anonimiseringsgate voor vertrouwelijke documentintake

| | |
|---|---|
| **Datum** | 10 november 2026 |
| **Status** | ter review (richting goedgekeurd in sessie 2026-11-10; spike-bevindingen verwerkt) |
| **Scope** | ontwerp van `redact-preflight`: een lokaal draaiende anonimiseringsstap die vertrouwelijke documenten (notulen, rapporten, bijlagen) sanitiseert vóórdat ze een LLM-seam, de data lake of git bereiken — modelpass (Desert Ant Redact, on-device) + deterministische NL-admin-postpass + menselijke review-diff + metadata-ledger |
| **Niet in scope** | productie-anonimisering van lopende dossiers · OCR/PDF-extractieketen (aanname: tekstinput; pdftotext/markdownextractie blijft bestaande tooling) · spraakmodellen van Desert Ant (Voz/Who/Align — aparte use-case participatienotulen, pas oppakken als die op de roadmap staat) · Schemer (schema-extractie — verworpen, zie alternatieven) · pseudonymisatie-met-restore als standaardmodus |
| **Bronnen** | [desertant.com/llms.txt](https://desertant.com/llms.txt) · [Redact-modelpagina](https://desertant.com/models/redact/) (88,8% recall / 99,6% precisie, 27 talen incl. Nederlands, 23M params) · [JS-SDK-docs](https://desertant.com/docs/redact/) · npm [`@desert-ant-labs/redact@4.3.0`](https://www.npmjs.com/package/@desert-ant-labs/redact) · licentie `LicenseRef-DAL-Source-Available-1.0` ([pointer](https://unpkg.com/@desert-ant-labs/redact/LICENSE.md), [volledige voorwaarden](https://license.desertant.com/1.0)) · [`docs/SOLUTIONS_ARCHITECTURE.md`](../../SOLUTIONS_ARCHITECTURE.md) §3.5 beveiligingslaag (privacy & dataminimalisatie) · [`docs/GENAI_SEAMS.md`](../../GENAI_SEAMS.md) (seam-discipline S1–S11) · pijnpunt-bewijs: [`docs/260806_Rapport_Use_Case_Schiehaven_Noord_geanonimiseerd.md`](../../260806_Rapport_Use_Case_Schiehaven_Noord_geanonimiseerd.md) en `docs/Bijlage … Peilbeheer (Geanonimiseerd).pdf` — beide handmatig gesaneerd · spike 2026-11-10 (bevindingen §5; steekproef geembed in Bijlage A) |

## Besluiten

| Keuze | Uitkomst |
|---|---|
| Volgorde van de passes | **Model eerst op de ruwe tekst, deterministische postpass daarna op de modeloutput.** Omgekeerde volgorde is gespijkt en verworpen: placeholders vóór de modelpass verstoren de NER-context (naam en BSN-placemarker raken gelijmd tot `[GIVEN_NAME_2][BSN_3]r`); model-eerst geeft een schone output waarop de keyword-geankerde NL-patterns (KVK, zaaknummer, perceel) betrouwbaar haken. |
| Entiteitsfamilies | **Model** = natuurpersonen en universele identifiers (namen, adressen, telefoon, e-mail, IBAN, BSN, postcode — spike: 18/18 gevangen). **Postpass** = NL-administratieve identifiers die het model structureel mist (KVK-nummer, zaak-/dossier-/projectnummer, kadastrale sectie+perceel). Geen overlap: checksum-entiteiten (BSN/IBAN/postcode) worden niet dubbel geredigeerd maar door de postpass **gevalideerd** (validator-idioom, zie principes). |
| Checksums als controleschema | 11-proef (BSN), IBAN-modulo-97 en postcodeformaat zijn **kwaliteitspoorten op modelitems**, geen tweede redactielaag: een modelitem dat aan het patroon voldoet maar de proef faalt wordt in de review gemarkeerd als mogelijke misdetectie; een Geslaagde proef bevestigt. Zelfde rol als de number-gate in S4/S8. |
| Keep-list | Model over-redigeerde in de spike de **gebiedsnaam** "Schiehaven Noord" tot `CITY`. Per intake bestaat een keep-list (werkgebied-/gebieds-/instellingsnamen) die modelitems met de labels `CITY`/`STREET_NAME` tegencheckt: match → niet redigeren, wél tonen in de review-diff als "bewust behouden" zodat de mens oordeelt. `ORG`-items worden door het model default níet geredigeerd (bedrijf ≠ natuurpersoon); de diff somt ze als bespreekpunt op — spike-casus: "Aannemersbedrijf J. Smit BV" mag blijven, "J. Smit" is natuurpersoon en dus mensoordeel. |
| Review-diff | **Mens beslist**: unified diff (origineel ↔ gesaneerd) gaat naar een pad **buiten git**, de reviewer keurt per hunk (behouden / herstellen / extra redactie), daarna wordt de diff verwijderd. De diff bevat per definitie originals en wordt nooit gecommit. |
| Ledger | `redaction-ledger.json` per intake met **alleen metadata**: label, origin (`model`/`det`), confidence, spanlengte, placeholder, counts, model- en SDK-versie, sha256 van input en output. **Geen originals en geen hashes van korte originele waarden** (sha256 van een 9-cijferig BSN is triviaal te brute-forcen; alleen de file-hash blijft). |
| Locatie & vorm | `nldt/services/redact_preflight/` naar het patroon van `services/source_monitor/`: Python-entry + `node/`-submap met de SDK-bridge (`redact_bridge.mjs`, aangeroepen als subprocess, JSON via stdin/stdout — geen node_modules in de repo; de bridge installeert de SDK versie-gepinnd in een tool-cache buiten de repo, `~/.cache/nldt/redact-bridge/`). CLI-subcommando `redact-preflight` in `nldt/services/cli.py`. Nieuwe seam **S12 · redact-preflight** in `GENAI_SEAMS.md`. |
| Vendor-afbakening | Desert Ant is **source-available, niet open source** (gratis < 100k maandelijkse apparaten per platform, attributieplicht, verbod op training van concurrerende modellen). Afbakening: de postpass, keep-list, review-loop en ledger zijn volledig vendorvrij; de modelpass is één vervangbare stap (fallback-route: lokaal GLiNER-PII in Python, zwaarder maar open) zodat de gate bij licentiewijziging blijft functioneren. |
| Offline-first | Na eenmalige download cachen de modelgewichten lokaal (Hugging Face-cache); daarna draait de gate volledig offline — gelijk aan de Ollama-seams (S7/S8). Het document verlaat het apparaat nooit vóór de review-goedkeuring. |

### Overwogen alternatieven

| Alternatief | Waarom niet |
|---|---|
| **Alleen regex/patroonherkenning, geen model** | Vrije-tekst namen en adressen zijn met patronen niet te vangen zonder naamdictionaries; in de spike ving het model 18/18 natuurpersoon-items (ook "K. Yilmaz", "A. Jansen", tussenvoegsels). De vendor-benchmark bevestigt dit beeld (Rampart: 61,4% recall — patroongebaseerd). |
| **Cloud-LLM redigeert het document** | Ondermijnt het doel van de gate zelf: vertrouwelijke documenten mogen het apparaat niet verlaten vóór sanering (AVG, verwerkersafspraken pilotgemeenten). Bovendien niet herhaalbaar/repliceerbaar offline. |
| **GLiNER-PII lokaal in Python (open source)** | Sterkste fallback (geen vendor, Python-native), maar 2,3 GB vs 24,5 MB en 90,4% precisie vs 99,6% — meer valse redacties betekent meer reviewwerk, precies wat de gate moet besparen. Als vervangend model achter dezelfde bridge gehouden, niet als eerste keus. |
| **Deterministische pass vóór de modelpass** | Gespijkt en verworpen (zie besluiten): placeholder-tokens in de input verstoren de NER-context en dubbelredactie van BSN/postcode/IBAN levert gelijmde fragmenten op. |
| **Schemer (Desert Ant, schema-extractie) voor formalisatie-taken** | 23M-klasse on-device extractie haalt niet de kwaliteit van de LAYA-template-aanpak (92,3% na bijscholing); closed beta. Geen rol. |
| **Pseudonymisatie met `restore()` als standaardmodus** | De SDK kan placeholders terugvertalen. Voor de intake-use-case is onomkeerbare redactie de veilige default; een mapping-bestand zou de sanering ongedaan maken en moet buiten de repo leven. Alleen als expliciete optie met aparte bewaarperiode, niet in de pilot. |

## 1. Context en doel

Vertrouwelijke overheidsdocumenten — NOVEX-notulen, peilbeheer-bijlagen, use-case-rapporten — worden vandaag **handmatig** geanonimiseerd voordat ze de PoCs, `docs/` of git in mogen (Schiehaven-rapport en peilbeheer-bijlage zijn allebei met de hand gesaneerd). Die stap is traag, foutgevoelig en niet schaalbaar naar de lopende NOVEX- en gebiedsontwikkelingstrajecten. Tegelijk dekt de RI-Geo-moderniseringsplaat een expliciete **beveiligingslaag (privacy & dataminimalisatie)** die in `SOLUTIONS_ARCHITECTURE.md` §3.5 grotendeels op IAM/accessClass rust — een intake-saneringsstap ontbreekt.

De generatieve seams draaien deels lokaal (Ollama), maar de **input-kant** is onbeschermd: elk document dat een LLM-seam, de bronze lake of een commit bereikt, is eerst ongesaneerd in het werkgeheugen van de pipeline. Redact-preflight sluit precies dat gat: een volledig lokaal draaiende, gelede en mens-bekrachtigde sanitiseringsstap vóór alles anders.

Desert Ant Redact is daarvoor het beste beschikbare bouwblok: 23M-parameters NER + patroondetectie, 24,5 MB, Nederlands ondersteund, 99,6% precisie, draait server-side in Node met een prebuilt native core (`@desert-ant-labs/redact/native`), gewichten cacheren lokaal vanaf Hugging Face. De 88,8% recall (≈1 op 9 gemist) is áánleiding voor de architectuur, geen bezwaar: de postpass vangt de systematische domein-gaten en de menselijke review is de beslissende poort.

## 2. Leidende principes

| Principe | Uitwerking |
|---|---|
| Redactie stelt voor, mens beslist | Model én postpass leveren *voorstellen* (placeholders + items). Pas na review-goedkeuring per hunk ontstaat de definitieve gesaneerde output. Zwijgen is nooit goedkeuring: zonder expliciete review blijft status `pending`. |
| Deterministische vloer | De keyword-geankerde NL-patterns (KVK, zaak-/projectnummer, kadasterperceel) zijn puur Python, vendorvrij en unit-testbaar; checksums valideren modelitems. Zelfs zonder model vangt de vloer de identifiers waarmee een document herleidbaar is. |
| Niets verlaat het apparaat | Model inference on-device (na eenmalige weight-download), geen cloud-calls, review-diff buiten git, ledger zonder originals. |
| Alles geleed en herhaalbaar | Elke intake produceert een ledger (wat, door wie — model/pass, welke confidence, welke versie) plus input/output-sha256; herhalen = zelfde input + zelfde SDK-versie → zelfde output (deterministische NER, temperature-vrij). Rejects en keep-list-hits worden bijgeschreven, niet stil gezwegen. |
| Configuratie is data | Keep-list en patroonset zijn geversioneerde JSON-artefacten naast de service, geen code. |

## 3. Architectuur

```
 document (md/txt) ──▶ [1] modelpass ──▶ [2] postpass ──▶ [3] merge+keep-list ──▶ [4] review ──▶ output + ledger
                        node/                 patterns.py           keep_list.json         diff buiten git
                        redact_bridge.mjs     (KVK/zaak/perceel/    (CITY/STREET/ORG-      (mens keurt per
                        (SDK versie-gepinnd,   checksum-validatie)   hits "bewust be-        hunk: OK/herstel/
                        HF-cache, offline)                          houden")                extra redactie)
```

**Componenten** (per een doel, testbaar zonder de rest):

| Component | Doet | Dependency |
|---|---|---|
| `redact_bridge.mjs` | laadt `Redact` (native), leest tekst van stdin, schrijft `{redactedText, items[{label, original, placeholder, confidence}]}` als JSON naar stdout; `dispose()` na elke run | `@desert-ant-labs/redact` (cache-dir, versie-gepinnd) |
| `patterns.py` | NL-admin-identifierpatronen op de modeloutput; checksumvalidatie van modelitems; volledig vendorvrij | stdlib `re` |
| `preflight.py` | orkestratie: bestanden in → passes 1–3 → review-voorstel → na goedkeuring output + ledger wegschrijven | bovenstaande twee + stdlib |
| `cli.py`-subcommando `redact-preflight` | `--in <doc>` `--out <doc_geanonimiseerd>` `--ledger <pad>` `--keep-list <pad>` `--review-dir <pad-buiten-git>` | `preflight.py` |

**Foutpaden.** SDK niet geïnstalleerd/gewichten niet gedownload: modelpass slaat over met **luid** `model: skipped` in de ledger (de vloer blijft werken), nooit stil. Node ontbreekt: zelfde gedrag. Postpass-patroon en modelitem overlappen: modelitem wint (het is al geredigeerd), overlap gaat als `duplicate` naar de ledger. Lege/gelineerde input: gewoon lege items-lijst, geen exceptie.

## 4. Contracts

**`redaction-ledger.schema.json`** (JSON Schema, gevalideerd bij wegschrijven):

```jsonc
{
  "intakeId": "20261110T…-notulen-overleg",
  "createdAt": "…", "sdkVersion": "@desert-ant-labs/redact@4.3.0", "modelSha256": "…",
  "input": {"path": "…", "sha256": "…"}, "output": {"path": "…", "sha256": "…"},
  "status": "pending | approved | rejected", "reviewedBy": null,
  "items": [
    {"label": "KVK", "origin": "det", "placeholder": "[KVK_3]", "spanLength": 8, "confidence": null},
    {"label": "GIVEN_NAME", "origin": "model", "placeholder": "[GIVEN_NAME_1]", "spanLength": 19, "confidence": 1.0},
    {"label": "GOVERNMENT_ID", "origin": "model", "placeholder": "[GOVERNMENT_ID_1]", "spanLength": 9, "confidence": 0.92,
     "checksum": {"proef": "elf_proef", "voldoet": true}},   // alleen gezet als het patroon past
    {"label": "CITY", "origin": "model", "keepListHit": "Schiehaven Noord", "kept": true}
  ],
  "counts": {"model": 18, "det": 3, "kept": 1, "checksumMismatches": 0}
}
```

Bewust **afwezig**: originals, offsets (veranderen bij elke herindeling), hashes van item-waarden. De review-diff (die originals wél bevat) is kortlevend: buiten git, na goedkeuring verwijderd door de tool zelf.

## 5. Spike-bevindingen (2026-11-10, Node 26 / macOS arm64, SDK 4.3.0)

Steekproef: 844-tekens peilbeheer-fragment (Schiehaven-kaliber, uitsluitend nepdata; BSN `123456782` en IBAN `NL91ABNA0417164300` met valide checksums om patroondetectie eerlijk te toetsen):

| Entiteit | Voorbeeld | Modelpass | Postpass |
|---|---|---|---|
| Naam incl. tussenvoegsel | Jeroen van der Meulen; Marianne de Boer | ✅ | — |
| Initialennaam | A. Jansen (gesplitst GIVEN+SURNAME), K. Yilmaz | ✅ | — |
| Telefoon (2 notaties) | 06-12345678, 010-123 45 67 | ✅ | — |
| E-mail (3×) | j.vandermeulen@wsr.nl | ✅ | — |
| IBAN (checksum valide) | NL91ABNA0417164300 | ✅ BANK_ACCOUNT | validatie |
| BSN (11-proef valide) | 123456782 | ✅ GOVERNMENT_ID (0,92) | validatie |
| Straat/postcode/huisnummer | Havenstraat 12, 3111 JD | ✅ | validatie |
| **KVK-nummer** | KVK-nummer 24123456 | ❌ | ✅ `[KVK_3]` |
| **Zaaknummer** | zaaknummer ZA-2026-1187 | ❌ | ✅ `[ZAAKNUMMER_2]` |
| **Kadasterperceel** | kadastraal perceel D 1234 | ⚠️ half ("D" blijft) | ✅ sectieletter `[KADASTER_PERCEEL_1]` |
| **Projectnummer** | projectnummer P-2026-0413 | ❌ | ❌ **bekend gat**: koppelwoord "is" nog niet in de regex — eerste backlog-item, les: zaak-/projectnummers zijn herleidbaar en horen in de vloer |
| Gebiedsnaam | Schiehaven Noord | ⚠️ over-redactie als CITY | keep-list vangt dit |
| Organisatie + persoonsnaam | Aannemersbedrijf J. Smit BV | ❌ (ORG default uit) | bespreekpunt review: bedrijf mag blijven, "J. Smit" is natuurpersoon — keep-list + mens |

Volgorde-experiment (beslissend voor de architectuur): det-pass vóór modelpass levert gelijmde fragmenten op (`is [GIVEN_NAME_2][BSN_3]r (BSN [GOVERNMENT_ID_1]`) en dubbelredactie van postcode/BSN. Model-eerst + postpass-daarna geeft een schone, volledig gesaneerde tekst.

## 6. Licentie, privacy & risico's

| Risico | Beoordeling | Mitigatie |
|---|---|---|
| DAL-licentie is source-available met attributieplicht | acceptabel voor PoC (< 100k apparaten = feitelijk gratis op één werkplek); past binnen de open-source-doctrine van de toolbox als **geïsoleerde, vervangbare stap** | bridge is de enige vendor-aanraking; GLiNER-fallback achter dezelfde interface; licentie-URL in de ledger voor herkomst |
| 88,8% recall model: gemiste natuurpersoon-gegevens | reëel — de gate is een *voorstel*-, geen waarborgslaag | review-diff toont elke hunk; checksumvalidatie vlagt verdachte modelitems; tijd voor review ≪ tijd voor handmatige anonimisering |
| Over-redactie (gebiedsnamen, instellingen) | spike bevestigd | keep-list per intake, defaults uit de use-case-configuratie |
| Review-diff lekt originals | inherent aan review | diff buiten git, tool verwijdert hem na goedkeuring; pad via `--review-dir` (default `/tmp`, nooit in repo of lake) |
| Vendor stopt / licentie verandert | laag | gewichten blijven lokaal gecachet (draaibaar zolang de licentie het toestaat); vloer werkt zonder model door; GLiNER-fallback achter dezelfde bridge-interface |
| PDF/binair input | buiten scope | intake verwacht tekst; bestaande extractie-tooling ervoor |

## 7. Roadmap

| Fase | Inhoud | Klaar-criterium |
|---|---|---|
| F1 | service + bridge + CLI + fixtures (bijlage A wordt eerste testinvoer) + ledger-schema + unittests op de vloer | `redact-preflight --in fixture` produceert output + geldige ledger met status `pending`; vloerpatronen 100% op fixture |
| F2 | keep-list + review-loop (diff genereren, per-hunk goedkeuren, diff opruimen) | handmatige walkthrough op één bestaand niet-geanonimiseerd document (lokaal) |
| F3 | **heranonimiseringstoets**: het handmatig geanonimiseerde Schiehaven-rapport als referentie — overlap/miss/over tussen mensanonimisering en de gate meten (aggregaten only, originals blijven lokaal) | meetrapport met precisie/recall van de gate t.o.v. mensresultaat |
| F4 | intake-koppeling: aanroep vanuit de deep-agents-PoC-prompts en de documentworkflow vóór elke commit van vertrouwelijk materiaal | één echt traject (NOVEX of gebiedsontwikkeling) loopt erdoorheen |

## 8. Samenhang

- **`SOLUTIONS_ARCHITECTURE.md` §3.5** — vult de beveiligingslaag (privacy & dataminimalisatie) op de intake-kant aan; geen wijziging aan de zone-engines.
- **`GENAI_SEAMS.md`** — nieuw seam-voorstel **S12 · redact-preflight** (aanbod-karakter: model stelt redacties voor, mens beslist; zelfde ledger-discipline als S1–S11). Implementatie voegt de rij toe.
- **`nldt/services/`-conventies** — volgt het patroon van `source_monitor/` (dir-service, CLI-subcommando, recipe-opschorting mogelijk); later optioneel recipe `redact-preflight-run`.
- **Doctrine** — *"AI stelt voor · pipeline beschikt · mens beslist"* onverkort van toepassing: dit is de eerste seam die op de **input**-kant zit in plaats van op de voorstel-kant.

## Bijlage A — spike-steekproef (F1-fixture, uitsluitend nepdata)

```text
In overleg van 12 maart 2026 met Jeroen van der Meulen (hoofdwaterbeheerder, Waterschap Rivierenland, tel. 06-12345678, j.vandermeulen@wsr.nl) is besloten dat de perceeleigenaar van kadastraal perceel D 1234 te Schiehaven Noord, Havenstraat 12, 3111 JD Schiedam, een peilafwijking kan aanvragen.

Contactpersoon bij de gemeente is Marianne de Boer (BSN 123456782, m.deboer@gemeente-schiedam.nl). Het projectnummer is P-2026-0413, zaaknummer ZA-2026-1187, en het rekeningnummer (IBAN) van de vereniging is NL91ABNA0417164300. De offerte van Aannemersbedrijf J. Smit BV (KVK-nummer 24123456) bedroeg EUR 12.450, exclusief btw.

Bewoners mevrouw A. Jansen (Oranjestraat 3) en de heer K. Yilmaz hebben aangegeven hinder te ervaren van de huidige waterstand. Voor vragen kunt u bellen naar 010-123 45 67 of mailen naar peilbeheer@schiehavennoord.nl.
```

Verwachte eindtoestand na beide passes (spike-output, geverifieerd 2026-11-10): alle namen, telefoonnummers, e-mails, IBAN, BSN, straat/postcode/huisnummer als `[LABEL_n]`-placeholders; `KVK_3`, `ZAAKNUMMER_2`, `KADASTER_PERCEEL_1` uit de postpass; "Schiehaven Noord" via keep-list behouden (zonder keep-list: `CITY_1`); "P-2026-0413" is het bekende patroongat (backlog).
