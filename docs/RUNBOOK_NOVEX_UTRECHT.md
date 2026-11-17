# Runbook — NOVEX-provincies / Utrecht (arrangement-pilot)

| | |
|---|---|
| **Beleidshaak NOVEX** | [Aanpak provincies](https://www.ruimtelijkeordening.nl/onderwerpen/novex/aanpak-provincies): doorlopende dialoog; compacte, jaarlijks geactualiseerde ruimtelijke arrangementen ([herijking 2026](https://www.ruimtelijkeordening.nl/documenten/2026/07/07/rapport-herijking-werkwijze-novex-provincies)) |
| **Beleidshaak Nota** | Thema’s **economie en energie** + **landbouw en natuur** — integrale afweging waar die botsen |
| **Product** | [NOVEX_ARRANGEMENT_MEMO_UTRECHT.md](NOVEX_ARRANGEMENT_MEMO_UTRECHT.md) |
| **Plan** | [PLAN_NOVEX_NOTA_RUIMTE.md](PLAN_NOVEX_NOTA_RUIMTE.md) §A6–A7 |

---

## Waarom dit bij NOVEX past

De herijking vraagt om **integrale afwegingen** (niet één opgave tegelijk) en om arrangementen die aansluiten op de Nota Ruimte. Dit tracé levert een **gedeeld feitenbeeld** (km² + citaten), geen arrangementstekst.

---

## Canonieke cijfers (dialoogproduct)

Bron: `poc/crosstrack-runs/20260831T094204Z-wzb-xtrack/`

| Paar | Conflict | Leeswijzer |
|---|---:|---|
| **zon × bos** | **22,665 km²** | **94,74%** van zoekgebied nieuwe natuur |
| wind × bos | 22,657 km² | 94,70% van zoekgebied nieuwe natuur |
| wind × zon | 845,445 km² | 98,37% van windzone |

---

## Commando’s (herbouw desgewenst)

```bash
python3 poc/run.py --use-case zon    # of canonical runs onder poc/runs/
python3 poc/run.py --use-case bos
python3 poc/crosstrack/run.py --tracks zon,bos
```

UI: `nldt/simulation/poc-utrecht.html` · `?poc=utrecht`

---

## Dialoogagenda (±30 min)

1. Bevestig cijfers/kaart (5).  
2. Koppel aan Nota-keuzes energie + natuur die dit arrangement moet raken (5).  
3. Weeg zon×bos — wat schrijven we dicht, wat blijft open? (15).  
4. Vervolgafspraak data/netcongestie indien relevant (5).

---

## Succescriteria

- [x] Memo met canonieke cijfers.  
- [x] Integrale conflict (niet single-issue) centraal.  
- [ ] Sessie Rijk–provincie / NOVEX gehouden.  
- [ ] Artefact herbruikbaar in volgende arrangement-ronde.
