# Ontwerp — Redact-preflight & stem-laag: on-device intake- en output-gates voor vertrouwelijke PoC-input

| | |
|---|---|
| **Datum** | 10 november 2026 (stichtingsversie redact-preflight; zelfde dag uitgebreid met stem-laag) |
| **Status** | ter review (richting goedgekeurd in sessie 2026-11-10; spike-bevindingen tekst + stem verwerkt) |
| **Scope** | ontwerp van `redact-preflight` en de aangrenzende **stem-laag**: (a) lokaal draaiende anonimiseringsstap die vertrouwelijke *tekst*documenten sanitiseert vóórdat ze een LLM-seam, de data lake of git bereiken — modelpass (Desert Ant Redact, on-device) + deterministische NL-admin-postpass + menselijke review-diff + metadata-ledger; (b) **stemintake**: on-device STT (Voz) + diarisatie (Who) + domeincorrectie, aangesloten op dezelfde redact-gate, voor opnamen van participatiebijeenkomsten/omgevingsoverleg/interviews (NOVEX, gebiedsontwikkeling, Schiehaven-kaliber); (c) **stemoutput**: on-device TTS (Piper) voor gesproken narratie uitsluitend óp goedgekeurde, gesaneerde output (S11-toegankelijkheid, run-annex, simulation-hub) |
| **Niet in scope** | productie-anonimisering van lopende dossiers · OCR/PDF-extractieketen (aanname: tekstinput) · **live/streaming-STT of een realtime gespreksassistent** (file-based na-verwerking alleen; S3-voicefront is toekomstbeeld, geen pilotonderdeel) · Schemer (schema-extractie — verworpen, zie alternatieven) · pseudonymisatie-met-restore als standaardmodus · TTS-kwaliteitskeuring door eindgebruikers (F7-mijlpaal) · Emo/Toxic/Gist/Eye e.d. (geen aansluiting op de PoCs) |
| **Bronnen** | [desertant.com/llms.txt](https://desertant.com/llms.txt) · [catalog.json](https://desertant.com/catalog.json) (16 modellen, **geen TTS**, gecheckt 2026-11-10) · [Redact-modelpagina](https://desertant.com/models/redact/) (88,8% recall / 99,6% precisie, 27 talen incl. Nederlands, 23M params) · [Voz-modelpagina](https://desertant.com/models/voz/) (25 talen incl. Nederlands, 337 MB, basis NVIDIA Parakeet TDT 0.6B v3 onder CC BY 4.0) · [JS-SDK-docs Redact](https://desertant.com/docs/redact/) / [Voz](https://desertant.com/docs/voz/) (Node: eigen `onnxruntime-node`, WAV-input) · npm [`@desert-ant-labs/redact@4.3.0`](https://www.npmjs.com/package/@desert-ant-labs/redact), `@desert-ant-labs/voz@4.3.0`, `@desert-ant-labs/who@4.3.0` · licentie `LicenseRef-DAL-Source-Available-1.0` ([volledige voorwaarden](https://license.desertant.com/1.0)) · TTS: [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices/tree/main/nl) (nl_NL + nl_BE, open source) · [`docs/SOLUTIONS_ARCHITECTURE.md`](../../SOLUTIONS_ARCHITECTURE.md) §3.5 beveiligingslaag · [`docs/GENAI_SEAMS.md`](../../GENAI_SEAMS.md) (S1–S11) · pijnpunt-bewijs: [`docs/260806_Rapport_Use_Case_Schiehaven_Noord_geanonimiseerd.md`](../../260806_Rapport_Use_Case_Schiehaven_Noord_geanonimiseerd.md) en `docs/Bijlage … Peilbeheer (Geanonimiseerd).pdf` — beide handmatig gesaneerd · spikes 2026-11-10 (tekst §5, stem §6; steekproeven in Bijlage A/B) |

## Besluiten

| Keuze | Uitkomst |
|---|---|
| Volgorde van de passes | **Model eerst op de ruwe tekst, deterministische postpass daarna op de modeloutput.** Omgekeerde volgorde is gespijkt en verworpen: placeholders vóór de modelpass verstoren de NER-context (naam en BSN-placemarker raken gelijmd tot `[GIVEN_NAME_2][BSN_3]r`); model-eerst geeft een schone output waarop de keyword-geankerde NL-patterns (KVK, zaaknummer, perceel) betrouwbaar haken. |
| Entiteitsfamilies | **Model** = natuurpersonen en universele identifiers (namen, adressen, telefoon, e-mail, IBAN, BSN, postcode — spike: 18/18 gevangen). **Postpass** = NL-administratieve identifiers die het model structureel mist (KVK-nummer, zaak-/dossier-/projectnummer, kadastrale sectie+perceel). Geen overlap: checksum-entiteiten worden niet dubbel geredigeerd maar door de postpass **gevalideerd** (validator-idioom, zie principes). |
| Checksums als controleschema | 11-proef (BSN), IBAN-modulo-97 en postcodeformaat zijn **kwaliteitspoorten op modelitems**, geen tweede redactielaag: een modelitem dat aan het patroon voldoet maar de proef faalt wordt in de review gemarkeerd als mogelijke misdetectie; een geslaagde proef bevestigt. Zelfde rol als de number-gate in S4/S8. |
| Keep-list | Model over-redigeerde in de spike de **gebiedsnaam** "Schiehaven Noord" tot `CITY`. Per intake bestaat een keep-list (werkgebied-/gebieds-/instellingsnamen) die modelitems met de labels `CITY`/`STREET_NAME` tegencheckt: match → niet redigeren, wél tonen in de review-diff als "bewust behouden" zodat de mens oordeelt. `ORG`-items worden door het model default níet geredigeerd (bedrijf ≠ natuurpersoon); de diff somt ze als bespreekpunt op — spike-casus: "Aannemersbedrijf J. Smit BV" mag blijven, "J. Smit" is natuurpersoon en dus mensoordeel. |
| Review-diff | **Mens beslist**: unified diff (origineel ↔ gesaneerd) gaat naar een pad **buiten git**, de reviewer keurt per hunk (behouden / herstellen / extra redactie), daarna wordt de diff verwijderd. De diff bevat per definitie originals en wordt nooit gecommit. |
| Ledger | `redaction-ledger.json` per intake met **alleen metadata**: label, origin (`model`/`det`), confidence, spanlengte, placeholder, counts, model- en SDK-versie, sha256 van input en output. **Geen originals en geen hashes van korte originele waarden** (sha256 van een 9-cijferig BSN is triviaal te brute-forcen; alleen de file-hash blijft). |
| **STT-motor** | **Voz** (on-device, Node met eigen `onnxruntime-node`, WAV file-based, transcript + woord-timestamps native — geen aparte Align nodig). Spike: 16,8 s Nederlandse twee-sprekersopname → transcript in 2,4 s, volledig op CPU (realtimefactor ~7×). Jargonfouten ("peilbeheer"→"pijlbeheer", "Schiehaven Noord"→"Schihavenoord") zijn systematisch en deterministisch herstelbaar: een **domeintermenlijst** (geversioneerd JSON, per traject) corrigeert vóór de redactie en dient meteen als keep-list-bron — twee functies, één artefact. De vocabulary-hint-functie van Voz bestaat nog niet in JavaScript; tot die tijd is de termenlijst de vloer. |
| **Stemintake-keten** | Opname → Voz-transcriptie → domeincorrectie → **bestaande redact-preflight-keten** (model + postpass + keep-list + review) → spreker-gelabelde notulen. Geen tweede gate bouwen: de stemintake is een nieuwe *bron* voor dezelfde gate. Woord-timestamps × Who-beurten = wie-zegt-wat, deterministisch versneden. |
| **Diarisatie** | **Who** (`@desert-ant-labs/who/native` — de default-import is browser-WASM; spike bevestigde native import werkt). Spreker-identiteiten blijven lokaal en anoniem (`SPEAKER_0/1/…`); een koppeling spreker↔naam is zélf persoonsgegeven en hoort thuis in de menselijke review (naam pas in de notulen na goedkeuring), nooit vanzelf in de ledger. |
| **TTS-motor** | Desert Ant heeft **geen TTS** in de catalogus (16 modellen, gecheckt 2026-11-10) → **Piper** (open source, ONNX, nl_NL- en nl_BE-stemmen uit rhasspy/piper-voices; Python-native, dus géén Node-bridge nodig). macOS `say` (Xander/Claire, nl_NL) dient als zero-dependency demo-pad op de werkmachine, maar is platformgebonden en geen ontwerpkeuze. TTS draait uitsluitend op **goedgekeurde, gesaneerde output** — gesproken PII is nog steeds PII. |
| **TTS-doelen** | (1) S11 dual-audience: gesproken plain-language-narratie als audio-alternatief naast B1-tekst (digitoegankelijkheid/WCAG); (2) S9 run-annex: audio-bijlage bij het beleidskompas-document; (3) simulation-hub: gesproken replay-narratie van PoC-runs. Alle drie consumeren bestaande, genomineerde tekst-artefacten — TTS genereert nooit nieuwe inhoud. |
| **Audio-beleid** | Opnames blijven lokaal en zijn **sterfelijk**: na transcriptie + goedgekeurde review wordt het audiobestand verwijderd (bewaartermijn configureerbaar, default direct). Opnemen van bewoners/ambtenaren alleen met toestemming (AVG; stem is identificeerbaar). De notulen mét sprekerlabels zijn het duurzame artefact; audio komt nooit in git of de lake. |
| Locatie & vorm | `nldt/services/redact_preflight/` naar het patroon van `services/source_monitor/`: Python-entry + `node/`-submap met de SDK-bridges (`redact_bridge.mjs`, `voice_bridge.mjs` voor Voz+Who — aangeroepen als subprocess, JSON via stdin/stdout; geen node_modules in de repo; SDK's versie-gepinnd in een tool-cache buiten de repo, `~/.cache/nldt/redact-bridge/`) + `tts.py` (Piper, direct Python). Configuratie als data: `keep_list.json`, `domain_terms.json` (STT-correctie + keep-list), patroonset. CLI-subcommando's `redact-preflight` (tekst), `voice-preflight` (audio→gesaneerd transcript+notulen), `tts-narrate` in `nldt/services/cli.py`. Nieuwe seams in `GENAI_SEAMS.md`: **S12 · redact-preflight** (tekst + stemintake delen de gate) en **S13 · on-device tts-narratie** (output-kant). |
| Vendor-afbakening | Desert Ant is **source-available, niet open source** (gratis < 100k maandelijkse apparaten per platform, attributieplicht, verbod op training van concurrerende modellen). Afbakening per laag: de postpass, domeintermen, keep-list, review-loop, notulenbouw en Piper-TTS zijn volledig vendorvrij; de Redact-modelpass is vervangbaar (fallback: lokaal GLiNER-PII, zwaarder maar open); de Voz-modelpass heeft de sterkste fallback van allemaal — het onderliggende Parakeet-model staat onder **CC BY 4.0** en is rechtstreeks in Python te draaien zonder vendor. De gate functioneert in elke configuratie door (vloer eerst). |
| Offline-first | Na eenmalige download cachen alle modelgewichten lokaal (Hugging Face-cache); daarna draait de hele gate volledig offline — gelijk aan de Ollama-seams (S7/S8). Document én audio verlaten het apparaat nooit vóór de review-goedkeuring. |

### Overwogen alternatieven

| Alternatief | Waarom niet |
|---|---|
| **Alleen regex/patroonherkenning, geen model** | Vrije-tekst namen en adressen zijn met patronen niet te vangen zonder naamdictionaries; in de spike ving het model 18/18 natuurpersoon-items (ook "K. Yilmaz", "A. Jansen", tussenvoegsels). De vendor-benchmark bevestigt dit beeld (Rampart: 61,4% recall — patroongebaseerd). |
| **Cloud-LLM redigeert het document** | Ondermijnt het doel van de gate zelf: vertrouwelijke documenten mogen het apparaat niet verlaten vóór sanering (AVG, verwerkersafspraken pilotgemeenten). Bovendien niet herhaalbaar/repliceerbaar offline. |
| **GLiNER-PII lokaal in Python (open source)** | Sterkste fallback (geen vendor, Python-native), maar 2,3 GB vs 24,5 MB en 90,4% precisie vs 99,6% — meer valse redacties betekent meer reviewwerk, precies wat de gate moet besparen. Als vervangend model achter dezelfde bridge gehouden, niet als eerste keus. |
| **Deterministische pass vóór de modelpass** | Gespijkt en verworpen (zie besluiten): placeholder-tokens in de input verstoren de NER-context en dubbelredactie van BSN/postcode/IBAN levert gelijmde fragmenten op. |
| **Whisper (lokaal, bijv. faster-whisper) i.p.v. Voz** | Levensvatbaar en Python-native, maar ~1,6 GB fp16 vs 337 MB, trager op CPU (Voz-spike: ~7× realtime), grovere timestamps en geen SDK-ondersteuning; vendor-uitval is gedekt via de CC-BY-Parakeet-fallback. Voz blijft eerste keus; Whisper benoemd als tweede fallback naast Parakeet-direct. |
| **Cloud-STT (Azure/Google/Whisper-API)** | Zelfde sovereignty-fout als cloud-redactie: de ópname — het meest gevoelige artefact, met stemmen van burgers — verlaat het apparaat ongesaneerd. |
| **Schemer (Desert Ant, schema-extractie) voor formalisatie-taken** | 23M-klasse on-device extractie haalt niet de kwaliteit van de LAYA-template-aanpak (92,3% na bijscholing); closed beta. Geen rol. |
| **Pseudonymisatie met `restore()` als standaardmodus** | De SDK kan placeholders terugvertalen. Voor de intake-use-case is onomkeerbare redactie de veilige default; een mapping-bestand zou de sanering ongedaan maken en moet buiten de repo leven. Alleen als expliciete optie met aparte bewaarperiode, niet in de pilot. |
| **macOS `say` als TTS-motor** | Nul dependencies en goed Nederlands op de werkmachine, maar platformgebonden (darwin-only) — onbruikbaar voor de Linux/RustFS-deploylaag. Demo-pad, geen ontwerpkeuze. |

## 1. Context en doel

Vertrouwelijke overheidsdocumenten — NOVEX-notulen, peilbeheer-bijlagen, use-case-rapporten — worden vandaag **handmatig** geanonimiseerd voordat ze de PoCs, `docs/` of git in mogen (Schiehaven-rapport en peilbeheer-bijlage zijn allebei met de hand gesaneerd). Die stap is traag, foutgevoelig en niet schaalbaar naar de lopende NOVEX- en gebiedsontwikkelingstrajecten. Tegelijk dekt de RI-Geo-moderniseringsplaat een expliciete **beveiligingslaag (privacy & dataminimalisatie)** die in `SOLUTIONS_ARCHITECTURE.md` §3.5 grotendeels op IAM/accessClass rust — een intake-saneringsstap ontbreekt.

De generatieve seams draaien deels lokaal (Ollama), maar de **input-kant** is onbeschermd: elk document dat een LLM-seam, de bronze lake of een commit bereikt, is eerst ongesaneerd in het werkgeheugen van de pipeline. Redact-preflight sluit precies dat gat: een volledig lokaal draaiende, gelede en mens-bekrachtigde sanitiseringsstap vóór alles anders.

De **stem-laag** verbreedt datzelfde gat naar twee kanten. Aan de input-kant: participatiebijeenkomsten, omgevingsoverleggen en bewonersinterviews (precies de NOVEX-/gebiedsontwikkelings- en Schiehaven-use-cases) worden vandaag of niet opgenomen, of uitgewerkt via cloud-diensten — terwijl de opname het meest gevoelige artefact is (stemmen van burgers). On-device STT met diarisatie levert spreker-gelabelde notulen die door dezelfde redact-gate gaan. Aan de output-kant vraagt S11 (dual-audience) een audio-alternatief naast plain-language-tekst voor toegankelijkheid; on-device TTS spreekt alléén goedgekeurde, gesaneerde output.

Desert Ant Redact is voor de tekstgate het beste beschikbare bouwblok: 23M-parameters NER + patroondetectie, 24,5 MB, Nederlands ondersteund, 99,6% precisie, draait server-side in Node met een prebuilt native core, gewichten cacheren lokaal vanaf Hugging Face. De 88,8% recall (≈1 op 9 gemist) is áánleiding voor de architectuur, geen bezwaar: de postpass vangt de systematische domein-gaten en de menselijke review is de beslissende poort. Voor de stem-laag geldt hetzelfde patroon: Voz (STT) en Who (diarisatie) draaien on-device in Node; TTS komt van Piper want Desert Ant biedt dat niet.

## 2. Leidende principes

| Principe | Uitwerking |
|---|---|
| Redactie stelt voor, mens beslist | Model én postpass leveren *voorstellen* (placeholders + items). Pas na review-goedkeuring per hunk ontstaat de definitieve gesaneerde output. Zwijgen is nooit goedkeuring: zonder expliciete review blijft status `pending`. |
| Deterministische vloer | De keyword-geankerde NL-patterns (KVK, zaak-/projectnummer, kadasterperceel) én de domeintermenlijst zijn puur Python/JSON, vendorvrij en unit-testbaar; checksums valideren modelitems; notulenbouw (timestamps × beurten) is pure tekstrekenkunde. Zelfs zonder enig model vangt de vloer de identifiers waarmee een document herleidbaar is. |
| Niets verlaat het apparaat | Model inference on-device (na eenmalige weight-download), geen cloud-calls, review-diff buiten git, ledger zonder originals. Voor audio geldt verscherpt: opnames blijven lokaal, zijn sterfelijk na review, en komen nooit in git of de lake. |
| Alles geleed en herhaalbaar | Elke intake (tekst én audio) produceert een ledger (wat, door wie — model/pass, welke confidence, welke versie) plus input/output-sha256; herhalen = zelfde input + zelfde SDK-versie → zelfde output (deterministische inferentie, temperature-vrij). Rejects, keep-list-hits en STT-correcties worden bijgeschreven, niet stil gezwegen. |
| Configuratie is data | Keep-list, domeintermenlijst en patroonset zijn geversioneerde JSON-artefacten naast de service, geen code. |
| TTS spreekt wat is goedgekeurd | De synthese-input is altijd een al genomineerd, gesaneerd artefact; TTS voegt geen inhoud toe en genereert nooit zelf tekst. |

## 3. Architectuur

```
TEKSTINTAKE
 document (md/txt) ──▶ [1] modelpass ──▶ [2] postpass ──▶ [3] merge+keep-list ──▶ [4] review ──▶ output + ledger
                        node/                 patterns.py           keep_list.json         diff buiten git
                        redact_bridge.mjs     (KVK/zaak/perceel/    (CITY/STREET-hits      (mens keurt per
                        (SDK versie-gepinnd,   checksum-validatie)   "bewust behouden")     hunk: OK/herstel/
                        HF-cache, offline)                                                  extra redactie)

STEMINTAKE (nieuwe bron, zelfde gate)
 opname (wav, lokaal) ─▶ [V1] Voz (STT + woord-timestamps) ─▶ [V2] domeincorrectie ─▶ [V3] redact-preflight ─▶ [V4] review ─▶ notulen + ledger
                          node/voice_bridge.mjs                domain_terms.json      (passen 1–4 hierboven)               (sprekerlabels via
                          + Who (diarisatie, turns)            (dient ook keep-list)                                        Who × timestamps;
                                                                                                                            audio daarna verwijderen)

STEMOUTPUT (uitsluitend op goedgekeurde output)
 goedgekeurd artefact (notulen/narratie/run-annex) ──▶ [T1] Piper TTS (tts.py, Python) ──▶ audio (lokaal artifact)
```

**Componenten** (per een doel, testbaar zonder de rest):

| Component | Doet | Dependency |
|---|---|---|
| `redact_bridge.mjs` | laadt `Redact` (native), leest tekst van stdin, schrijft `{redactedText, items[{label, original, placeholder, confidence}]}` als JSON naar stdout; dispose-defensief (API verschilt per model — spike-les) | `@desert-ant-labs/redact` (tool-cache, versie-gepinnd) |
| `voice_bridge.mjs` | laadt `Voz` én `Who` via `/native` imports met zelf meegegeven `onnxruntime-node`; leest WAV-bytes van stdin, schrijft `{transcript, words[{text,start,end}], turns[{speaker,start,end}], speakerCount}` als JSON; WAV-conversie (afconvert/ffmpeg) is taak van de Python-entry, niet van de bridge | `@desert-ant-labs/voz`, `@desert-ant-labs/who` (tool-cache) |
| `tts.py` | Piper-synthese van goedgekeurde tekst naar lokaal audiobestand; stem-UUID geconfigureerd per traject | `piper-tts` (pip, stemmen van rhasspy/piper-voices) |
| `patterns.py` | NL-admin-identifierpatronen op de modeloutput; checksumvalidatie van modelitems; volledig vendorvrij | stdlib `re` |
| `domain_terms.py` | STT-domeincorrectie (fout-variant → canonieke term, bijv. `pijlbeheer → peilbeheer`) + keep-list-resolutie tegen gecorrigeerde tekst | stdlib + `domain_terms.json` |
| `minutes.py` | spreker-gelabelde notulen: Who-turns × Voz-woorden → per spreker een alinea op de *gesaneerde* tekst | stdlib |
| `preflight.py` | orkestratie tekstintake: bestanden in → passen 1–3 → review-voorstel → na goedkeuring output + ledger | bovenstaande + stdlib |
| `voice_preflight.py` | orkestratie stemintake: wav in → bridge → correctie → preflight.py hergebruiken → notulen + ledger → audio verwijderen | idem |
| `cli.py`-subcommando's `redact-preflight`, `voice-preflight`, `tts-narrate` | `--in`/`--out`/`--ledger`/`--keep-list`/`--domain-terms`/`--review-dir`/(`--voice-uuid` voor TTS) | bovenstaande |

**Foutpaden.** SDK niet geïnstalleerd/gewichten niet gedownload: modelpass slaat over met **luid** `model: skipped` in de ledger (de vloer blijft werken), nooit stil. Node of onnxruntime-node ontbreekt: zelfde gedrag. Postpass-patroon en modelitem overlappen: modelitem wint (het is al geredigeerd), overlap gaat als `duplicate` naar de ledger. Lege/gelineerde input: gewoon lege items-lijst, geen exceptie. Te groot audiobestand: Voz verwerkt file-based in 15s-vensters (geen streaming-limiet); voor zeer lange opnamen kan `voice_preflight.py` bovendien zelf in segmenten splitsen en turns aaneenvoegen (ledger noteert `segmented: true`).

## 4. Contracts

**`redaction-ledger.schema.json`** (JSON Schema, gevalideerd bij wegschrijven; geldt voor tekst- én stemintake):

```jsonc
{
  "intakeId": "20261110T…-notulen-overleg",
  "modality": "text | voice",
  "createdAt": "…", "sdkVersion": "@desert-ant-labs/redact@4.3.0", "modelSha256": "…",
  "input": {"path": "…", "sha256": "…", "deletedAfterReview": true},   // stem: true na verwijdering
  "output": {"path": "…", "sha256": "…"},
  "status": "pending | approved | rejected", "reviewedBy": null,
  "items": [
    {"label": "KVK", "origin": "det", "placeholder": "[KVK_3]", "spanLength": 8, "confidence": null},
    {"label": "GIVEN_NAME", "origin": "model", "placeholder": "[GIVEN_NAME_1]", "spanLength": 19, "confidence": 1.0},
    {"label": "GOVERNMENT_ID", "origin": "model", "placeholder": "[GOVERNMENT_ID_1]", "spanLength": 9, "confidence": 0.92,
     "checksum": {"proef": "elf_proef", "voldoet": true}},   // alleen gezet als het patroon past
    {"label": "CITY", "origin": "model", "keepListHit": "Schiehaven Noord", "kept": true}
  ],
  "voice": {                                    // alleen bij modality=voice
    "stt": {"sdk": "@desert-ant-labs/voz@4.3.0", "durationS": 16.8, "realtimeFactor": 6.96},
    "diarization": {"sdk": "@desert-ant-labs/who@4.3.0", "speakerCount": 2},
    "corrections": [{"from": "pijlbeheer", "to": "peilbeheer", "rule": "domain_terms.json#peilbeheer"}],
    "speakersNamed": false                      // true pas nadat reviewer namen koppelde
  },
  "counts": {"model": 18, "det": 3, "kept": 1, "checksumMismatches": 0}
}
```

Bewust **afwezig**: originals, offsets (veranderen bij elke herindeling), hashes van item-waarden, en de spreker↔naam-koppeling (pas ná review, dan als `speakersNamed: true` zónder de namen zelf). De review-diff (die originals wél bevat) is kortlevend: buiten git, na goedkeuring verwijderd door de tool zelf.

## 5. Spike-bevindingen tekstintake (2026-11-10, Node 26 / macOS arm64, SDK 4.3.0)

Steekproef: 844-tekens peilbeheer-fragment (Schiehaven-kaliber, uitsluitend nepdata; BSN `123456782` en IBAN `NL91ABNA0417164300` met valide checksums om patroondetectie eerlijk te toetsen — volledige tekst in Bijlage A):

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

## 6. Spike-bevindingen stem-laag (2026-11-10, zelfde machine, CPU-only)

Testopname: 16,8 s / 524 kB 16 kHz mono WAV, twee Nederlandse macOS-stemmen (Xander = voorzitter, Claire = bewoonster), reproduceerbaar gegenereerd met `say` + `afconvert` (commando's in Bijlage B):

| Bepaling | Resultaat |
|---|---|
| Voz-transcriptie, volledige opname | **2,4 s**, realtimefactor ~7× — CPU-only via `onnxruntime-node`, geen GPU |
| Transcriptkwaliteit Nederlands | Goed; systeemfouten zijn uitsluitend domeintermen: `peilbeheer→pijlbeheer`, `streefpeil→streefpijl`, `Schiehaven Noord→Schihavenoord`; getalnormalisatie `twaalf→12`. Alle drie deterministisch herstelbaar via de domeintermenlijst (en de vocabulary-hint ontbreekt nog in JS) |
| Woord-timestamps | native, milliseconde-nauwkeurig genoeg voor notulensnede (start expliciet, end geschat — 80 ms-resolutie) |
| Keten STT → redact-gate | ✅ transcript door Redact: `Marianne de Boer`→`[GIVEN_NAME_1]`, `havenstraat`→`[STREET_NAME_1]`, `12`→`[BUILDING_NUMBER_1]`; het verkeerd-geluisterde `Schihavenoord` landde als `CITY` — bevestigt dat domeincorrectie vóór de keep-list-check moet lopen |
| Who-diarisatie | ✅ via `@desert-ant-labs/who/native` (default-import is browser-WASM): `speakerCount: 2`, turns `0.00–8.23 s` en `8.31–16.62 s` — exact de twee segmentgrenzen |
| API-lesjes voor de bridges | `Voz.load({ort})` vereist zelf geïnstalleerde `onnxruntime-node`; WAV-conversie is Node-verantwoordelijk (geen WebCodecs); `dispose()` bestaat niet op elk model — bridge moet defensief afsluiten |

Onbepaald (bewust): TTS-kwaliteit van de Piper nl-stemmen (rdh/hifi_tts_92-hertraind) — geen spike gedaan; dit is het klaar-criterium van F7. Getalswaarschuwing: deze spike gebruikt schone synthesestemmen; echte overgeluiden liggen dichter bij de vendor-cijfers voor meetings (8–11% WER), dus de review-poort blijft onverkort nodig.

## 7. Licentie, privacy & risico's

| Risico | Beoordeling | Mitigatie |
|---|---|---|
| DAL-licentie is source-available met attributieplicht | acceptabel voor PoC (< 100k apparaten = feitelijk gratis op één werkplek); past binnen de open-source-doctrine van de toolbox als **geïsoleerde, vervangbare stappen** | bridges zijn de enige vendor-aanraking; GLiNER-fallback (redact) en Parakeet-direct/Whisper (STT) achter dezelfde interface; Piper en alle vloeronderdelen zijn vendorvrij; licentie-URL in de ledger |
| 88,8% recall model: gemiste natuurpersoon-gegevens | reëel — de gate is een *voorstel*-, geen waarborgslaag | review-diff toont elke hunk; checksumvalidatie vlagt verdachte modelitems; tijd voor review ≪ tijd voor handmatige anonimisering |
| STT luistert een naam verkeerd → glip door de gate | reëel risico, spike toont het mechanisme (`Schihavenoord` als CITY) | domeintermenlijst eerst; review-diff; notulen pas na menselijke goedkeuring; woord-timestamps laten de reviewer het fragment terugvinden (en beluisteren) in de nog aanwezige audio |
| Over-redactie (gebiedsnamen, instellingen) | spike bevestigd | keep-list per intake, defaults uit de use-case-configuratie; domeintermen dienen dubbel als keep-list-bron |
| Review-diff lekt originals | inherent aan review | diff buiten git, tool verwijdert hem na goedkeuring; pad via `--review-dir` (default `/tmp`, nooit in repo of lake) |
| Audio zelf is het gevoeligste artefact (stemmen burgers) | hoog, mits onbeheerd | lokaal-only, sterfelijk na review (default direct verwijderen), nooit git/lake, opname alleen met toestemming; spreker↔naam-koppeling pas na review, buiten de ledger |
| TTS-kwaliteit Nederlands (Piper rdh-basis) ongekeurd | onbekend | F7-mijlpaal: luistertoets met één notulen- en één narratiefragment; `say` als tussenoplossing op de werkmachine |
| Vendor stopt / licentie verandert | laag | gewichten blijven lokaal gecachet (draaibaar zolang de licentie het toestaat); vloer werkt zonder model door; STT heeft CC-BY-Parakeet als vendorvrije onderbouwing; fallbacks achter dezelfde bridge-interfaces |
| PDF/binair input | buiten scope | intake verwacht tekst; bestaande extractie-tooling ervoor |

## 8. Roadmap

| Fase | Inhoud | Klaar-criterium |
|---|---|---|
| F1 | service + bridge + CLI + fixtures (Bijlage A wordt eerste testinvoer) + ledger-schema + unittests op de vloer | `redact-preflight --in fixture` produceert output + geldige ledger met status `pending`; vloerpatronen 100% op fixture |
| F2 | keep-list + review-loop (diff genereren, per-hunk goedkeuren, diff opruimen) | handmatige walkthrough op één bestaand niet-geanonimiseerd document (lokaal) |
| F3 | **heranonimiseringstoets**: het handmatig geanonimiseerde Schiehaven-rapport als referentie — overlap/miss/over tussen mensanonimisering en de gate meten (aggregaten only, originals blijven lokaal) | meetrapport met precisie/recall van de gate t.o.v. mensresultaat |
| F4 | intake-koppeling: aanroep vanuit de deep-agents-PoC-prompts en de documentworkflow vóór elke commit van vertrouwelijk materiaal | één echt traject (NOVEX of gebiedsontwikkeling) loopt erdoorheen |
| F5 | **stemintake**: `voice_bridge.mjs` + `domain_terms.py` + `voice_preflight.py`, keten op Bijlage B-fixture (say-gegenereerd, reproduceerbaar op macOS) | Bijlage B-opname → transcript + correcties + gesaneerde tekst + ledger `pending`; domeincorrecties 3/3 op fixture |
| F6 | **notulen + diarisatie**: `minutes.py` (turns × woorden), spreker↔naam-koppeling in de review, audio-verwijderbeleid | één (nep- of echte) overlegsopname → spreker-gelabelde, gesaneerde notulen `approved` |
| F7 | **TTS**: `tts.py` (Piper, nl-stem), `tts-narrate` CLI, alleen op goedgekeurde artefacten | luistertoets genoteerd in het spec (nl-stem keuze + bevinding); één S11-narratiefragment en één run-annex met audio |

## 9. Samenhang

- **`SOLUTIONS_ARCHITECTURE.md` §3.5** — vult de beveiligingslaag (privacy & dataminimalisatie) op de intake-kant aan; geen wijziging aan de zone-engines.
- **`GENAI_SEAMS.md`** — nieuw seam-voorstel **S12 · redact-preflight** (tekst- én stemintake delen de gate; model stelt redacties voor, mens beslist) en **S13 · on-device tts-narratie** (output-kant: synthese van genomineerde artefacten; voegt niets toe). Implementatie voegt de rijen toe.
- **S3 (conversational intake)** — de stemintake legt het file-based fundament; een realtime gespreksfront-end blijft expliciet toekomstbeeld (niet in scope).
- **S11 (dual-audience)** — TTS levert het audio-alternatief voor de plain-language-narratie; **S9 (run-annex)** — audio-bijlage voor het beleidskompas; **simulation-hub** — gesproken replay-narratie.
- **`nldt/services/`-conventies** — volgt het patroon van `source_monitor/` (dir-service, CLI-subcommando's, recipe-opschorting mogelijk); later optioneel recipes `redact-preflight-run` / `voice-preflight-run`.
- **Doctrine** — *"AI stelt voor · pipeline beschikt · mens beslist"* onverkort van toepassing: S12 is de eerste seam op de **input**-kant, S13 de eerste op de gesproken **output**-kant.

## Bijlage A — tekst-spike-steekproef (F1-fixture, uitsluitend nepdata)

```text
In overleg van 12 maart 2026 met Jeroen van der Meulen (hoofdwaterbeheerder, Waterschap Rivierenland, tel. 06-12345678, j.vandermeulen@wsr.nl) is besloten dat de perceeleigenaar van kadastraal perceel D 1234 te Schiehaven Noord, Havenstraat 12, 3111 JD Schiedam, een peilafwijking kan aanvragen.

Contactpersoon bij de gemeente is Marianne de Boer (BSN 123456782, m.deboer@gemeente-schiedam.nl). Het projectnummer is P-2026-0413, zaaknummer ZA-2026-1187, en het rekeningnummer (IBAN) van de vereniging is NL91ABNA0417164300. De offerte van Aannemersbedrijf J. Smit BV (KVK-nummer 24123456) bedroeg EUR 12.450, exclusief btw.

Bewoners mevrouw A. Jansen (Oranjestraat 3) en de heer K. Yilmaz hebben aangegeven hinder te ervaren van de huidige waterstand. Voor vragen kunt u bellen naar 010-123 45 67 of mailen naar peilbeheer@schiehavennoord.nl.
```

Verwachte eindtoestand na beide passes (spike-output, geverifieerd 2026-11-10): alle namen, telefoonnummers, e-mails, IBAN, BSN, straat/postcode/huisnummer als `[LABEL_n]`-placeholders; `KVK_3`, `ZAAKNUMMER_2`, `KADASTER_PERCEEL_1` uit de postpass; "Schiehaven Noord" via keep-list behouden (zonder keep-list: `CITY_1`); "P-2026-0413" is het bekende patroongat (backlog).

## Bijlage B — stem-spike, reproduceerbaar (F5-fixture)

```bash
say -v Xander -o spk1.aiff "Dit is een testopname van het omgevingsoverleg over peilbeheer in Schiehaven Noord. De waterstand staat dit voorjaar veertien centimeter boven het streefpeil."
say -v "Claire (Enhanced)" -o spk2.aiff "Goedemiddag, mijn naam is Marianne de Boer en ik woon aan de Havenstraat nummer twaalf. Ik ervaar hinder van de hoge waterstand in mijn kelder."
afconvert -f WAVE -d LEI16@16000 -c 1 spk1.aiff spk1.wav && afconvert -f WAVE -d LEI16@16000 -c 1 spk2.aiff spk2.wav
# spk1.wav + spk2.wav frames concateneren (stdlib wave) → meeting.wav (16,8 s, 524 kB)
```

Verwachte resultaten (geverifieerd 2026-11-10): Voz 2,4 s / rtf ~7×; transcript met exact de drie domeinfouten `pijlbeheer`, `streefpijl`, `Schihavenoord` (F5-correctiedoelen) plus `twaalf→12`; Redact op transcript: `GIVEN_NAME` (Marianne de Boer), `STREET_NAME` (havenstraat), `BUILDING_NUMBER` (12), `CITY` (Schihavenoord → keep-list-casus); Who/native: 2 sprekers, turns op de naad 8,23/8,31 s.
