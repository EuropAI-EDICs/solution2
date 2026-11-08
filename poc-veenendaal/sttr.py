#!/usr/bin/env python3
"""veenendaal-spoorzone — officiële toepasbare regels (STTR) over het gebied.

Derde kennisbank-laag naast de BAG/BGT-gebiedscheck (run.py): welke officiële
vrágen stelt het Omgevingsloket aan dit gebied? Twee sporen, allebei
bewijs-gebonden (doctrine: rekenlaag beslist — dit zijn vragen, géén besluit):

1. **locatie-gebonden** — STTR-bestanden met `uitv:geoVerwijzing` naar
   `nl.imow-gm0345`-GIO's waarvan de geometrie de werkgrens snijdt. Route:
   Presenteren `regelingen/_zoek` op het station-anker → omgevingsplan-AKN →
   downloaden-API (uitwisselpakket) → GIO-GML's → tpod/geo-intersectie.
2. **programma-gebonden** — activiteiten waaraan het programma feitelijk raakt
   (4.500 woningen, spoorlijn in gebied, bestaand pandenbestand). Elke
   koppelregel draagt zijn bewijs mee (indicators.json van de canonieke run +
   gebied.json) en is expliciet als heuristiek gelabeld.

Bronnen: RTR-STTR-set van Veenendaal (185 bestanden, PRE — gedocumenteerd in
docs/POC_STTR_IMTR_KANSEN.md); locatie- en programmabinding zijn indicatief,
geen toestemming; de enum-vertaling blijft juridisch. Geen LLM.

Gebruik:
  nldt/.venv/bin/python sttr.py [--refresh] [--skip-live]
  # live-stappen (Presenteren + downloaden-API) hebben DSO_API_KEY (.env);
  # --skip-live hergebruikt de caches; de STTR-leeslaag is altijd offline.
Uitvoer: sttr-runs/<ts>-loketvragen/{report.md, loketvragen.json, manifest.json}
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent          # poc-veenendaal
REPO = ROOT.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
# client.py importeert z'n buurmodules kaal (dso_overlap-conventie, vgl. rtr.py)
DSO_DIR = REPO / "nldt" / "simulation" / "regelrecht" / "dso_overlap"
if str(DSO_DIR) not in sys.path:
    sys.path.insert(0, str(DSO_DIR))

from nldt.simulation.regelrecht.dso_overlap import client as dso_client  # noqa: E402
from nldt.simulation.regelrecht.sttr import parse_sttr  # noqa: E402

DATA = ROOT / "data"
CACHE = DATA / "cache"
RUNS = ROOT / "sttr-runs"
DSO_OUT = REPO / "nldt" / "simulation" / "regelrecht" / "dso_overlap" / "out"
INSTRUMENT = "veenendaal"
VRAAG_CAP = 12  # per activiteit in de rapportage


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


# ---------------------------------------------------------------- STTR-leeslaag (offline)

def lees_sttr_cache(instrument: str = INSTRUMENT, out_dir: Path = DSO_OUT) -> dict:
    index_pad = out_dir / f"{instrument}.sttr.json"
    rtr_pad = out_dir / f"{instrument}.rtr.json"
    if not index_pad.is_file() or not rtr_pad.is_file():
        raise SystemExit(
            f"STTR-cache mist {index_pad.name} — ververs eerst: "
            f"python -m nldt.simulation.regelrecht.dso_overlap.rtr --instruments {instrument} --bestanden && "
            f"python -m nldt.simulation.regelrecht.sttr --instruments {instrument}"
        )
    return {
        "index": json.loads(index_pad.read_text(encoding="utf-8")),
        "rtr": json.loads(rtr_pad.read_text(encoding="utf-8")),
        "paden": {"index": index_pad, "rtr": rtr_pad},
    }


def geo_verwijzingen(index: dict, out_dir: Path = DSO_OUT,
                     instrument: str = INSTRUMENT) -> list[dict]:
    """locatie-gebonden STTR-vragen: geoVerwijzing-locaties per geldig bestand."""
    uit: list[dict] = []
    for bestand in index.get("bestanden") or []:
        if bestand.get("einddatum") or not (bestand.get("geoVerwijzingen", 0) > 0):
            continue
        dmn_pad = out_dir / f"{instrument}.rtr.{bestand['identifier']}.dmn"
        if not dmn_pad.is_file():
            continue
        parsed = parse_sttr(dmn_pad.read_text(encoding="utf-8", errors="replace"))
        for regel in parsed.get("uitvoeringsregels") or []:
            geo = regel.get("geoVerwijzing")
            if not geo:
                continue
            uit.append({
                "rtrId": bestand["identifier"],
                "activiteit": bestand.get("activiteit"),
                "begindatum": bestand.get("begindatum"),
                "locatieIdentificatie": geo.get("locatieIdentificatie"),
                "vraagTekst": geo.get("vraagTekst") or "",
            })
    return uit


# ---------------------------------------------------------------- live: regeling + pakket

def zoek_omgevingsplan(punt: dict, *, refresh: bool = False) -> tuple[dict, dict]:
    """Presenteren regelingen/_zoek op het ankerpunt; cache-first.

    Return (plan-dict met identificatie+titel, manifest-meta). Filter: gemeente
    gm0345 én identificatie eindigt op '/omgevingsplan'.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    pad = CACHE / "presenteren-regelingen.json"
    meta_pad = CACHE / "presenteren-regelingen.meta.json"
    if pad.exists() and not refresh:
        doc = json.loads(pad.read_text(encoding="utf-8"))
        meta = json.loads(meta_pad.read_text(encoding="utf-8"))
        meta["cached"] = True
    else:
        api_key = dso_client.require_dso_key()
        url = f"{dso_client.presenteren_base()}/regelingen/_zoek?page=1&size=50"
        req = urllib.request.Request(
            url, data=json.dumps({"geometrie": punt, "locatieSelectie": "primair"}).encode(),
            method="POST", headers={
                "X-Api-Key": api_key, "Content-Type": "application/json",
                "Accept": "application/hal+json",
                "Content-Crs": dso_client.CRS_DSO, "Accept-Crs": dso_client.CRS_DSO,
            })
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as e:
            raise SystemExit(
                f"Presenteren regelingen/_zoek faalde: HTTP {e.code} {e.read()[:200]!r}"
            ) from e
        pad.write_bytes(raw)
        doc = json.loads(raw.decode("utf-8"))
        meta = {"url": url, "sha256": sha256_bytes(raw), "fetchedAt": utcnow(),
                "featureCount": len((doc.get("_embedded") or {}).get("regelingen") or [])}
        meta_pad.write_text(json.dumps(meta, indent=2))
        meta["cached"] = False

    kandidaten = [
        r for r in (doc.get("_embedded") or {}).get("regelingen") or []
        if (r.get("aangeleverdDoorEen") or {}).get("code") == "gm0345"
        and str(r.get("identificatie", "")).rstrip("/").endswith("omgevingsplan")
    ]
    if not kandidaten:
        raise SystemExit("geen omgevingsplan gm0345 in het Presenteren-antwoord op het ankerpunt")
    plan = kandidaten[0]
    return {
        "identificatie": plan.get("identificatie"),
        "officieleTitel": plan.get("officieleTitel"),
        "aangeleverdDoorEen": plan.get("aangeleverdDoorEen"),
    }, meta


def haal_uitwisselpakket(regeling_id: str, *, refresh: bool = False) -> tuple[Path, dict]:
    """OW-uitwisselpakket (GIO-GML's) van het omgevingsplan; cache-first."""
    CACHE.mkdir(parents=True, exist_ok=True)
    pad = CACHE / "omgevingsplan-pakket.zip"
    meta_pad = CACHE / "omgevingsplan-pakket.meta.json"
    if pad.exists() and pad.stat().st_size > 1000 and not refresh:
        meta = json.loads(meta_pad.read_text(encoding="utf-8"))
        meta["cached"] = True
        return pad, meta
    api_key = dso_client.require_dso_key()
    print("  uitwisselpakket aanvragen (asynchroon, kan minuten duren)…")
    raw, sha = dso_client.fetch_uitwisselpakket(regeling_id, api_key=api_key)
    pad.write_bytes(raw)
    meta = {"regelingId": regeling_id, "bytes": len(raw), "sha256": sha, "fetchedAt": utcnow()}
    meta_pad.write_text(json.dumps(meta, indent=2))
    meta["cached"] = False
    return pad, meta


def _ow_locatie_identificaties(pakket_zip: Path) -> set[str]:
    """IMOW-locatie-identificaties uit de OW-objecten (gebieden + gebiedengroepen)."""
    import re
    import zipfile

    uit: set[str] = set()
    with zipfile.ZipFile(pakket_zip) as z:
        for naam in ("OW-bestanden/gebieden.xml", "OW-bestanden/gebiedengroepen.xml"):
            try:
                tekst = z.read(naam).decode("utf-8", errors="replace")
            except KeyError:
                continue
            uit.update(re.findall(r"identificatie>(nl\.imow-[^<]+)<", tekst))
    return uit


def koppel_geo_aan_werkgrens(
    verwijzingen: list[dict], pakket_zip: Path, bbox_rd: list[float]
) -> tuple[list[dict], dict]:
    """Koppel elke geoVerwijzing-locatie aan de werkgrens — met eerlijke status.

    Drie mogelijke uitkomsten per verwijzing (nooit gokken):
    - ``gekoppeld``: GML met IMOW-bestandsnaam (LVBB-conventie) in het pakket;
      snijdtWerkgrens/overlapHa gemeten (shapely, EPSG:28992).
    - ``aanwezig-als-ow-object``: de locatie bestaat in gebieden/gebiedengroepen.xml,
      maar de geometrie zit niet in dít uitwisselpakket (aparte GIO-aanlevering).
    - ``afwezig-in-pakket``: identificatie ontbreekt geheel (bijv. een
      leveranciers-identificatiefamilie uit de STTR-maker).
    """
    from shapely.geometry import box as shapely_box

    from nldt.simulation.regelrecht.tpod import geo as tpod_geo

    index = tpod_geo.geo_index_uit_pakket(pakket_zip)
    locaties = index.get("locaties") or {}
    ow_ids = _ow_locatie_identificaties(pakket_zip)
    werkgrens = shapely_box(*bbox_rd)
    uit: list[dict] = []
    for v in verwijzingen:
        ident = v.get("locatieIdentificatie")
        item = locaties.get(ident)
        rec = {**v}
        if item is not None:
            rec["status"] = "gekoppeld"
            vorm = item["vorm"]
            rec["snijdtWerkgrens"] = bool(vorm.intersects(werkgrens))
            if rec["snijdtWerkgrens"]:
                rec["overlapHa"] = round(vorm.intersection(werkgrens).area / 10_000, 2)
        elif ident in ow_ids:
            rec["status"] = "aanwezig-als-ow-object"
            rec["toelichting"] = (
                "locatie bestaat in het omgevingsplan (OW-object), maar de geometrie "
                "zit niet in dit uitwisselpakket — GIO-aanlevering loopt apart"
            )
        else:
            rec["status"] = "afwezig-in-pakket"
        uit.append(rec)
    samenvatting = {
        "locatiesInPakket": len(locaties),
        "owObjecten": len(ow_ids),
        "overgeslagenNamen": index.get("overgeslagen"),
    }
    return uit, samenvatting


def sweep_gios_tegen_werkgrens(
    pakket_zip: Path, bbox_rd: list[float]
) -> list[dict]:
    """Alle GIO's in het pakket (ook vrij benoemde) tegen de werkgrens snijden.

    Dit is de gebiedsfeit-kant: welke officiële beleidslagen (GIO's, elk met
    STOP-FRBRWork) bedekken (een deel van) de werkgrens — onafhankelijk van de
    STTR-vraag-koppeling, die apart en eerlijk wordt gerapporteerd.
    """
    import re
    import zipfile

    from shapely.geometry import box as shapely_box

    from nldt.simulation.regelrecht.tpod import geo as tpod_geo

    werkgrens = shapely_box(*bbox_rd)
    uit: list[dict] = []
    with zipfile.ZipFile(pakket_zip) as z:
        gml_namen = sorted(n for n in z.namelist() if n.endswith(".gml") and "/" in n)
        for naam in gml_namen:
            data = z.read(naam)
            parsed = tpod_geo.parse_gml_vorm(data)
            rec = {"bestand": naam.rsplit("/", 1)[-1]}
            m = re.search(rb"<geo:FRBRWork>([^<]+)</geo:FRBRWork>", data)
            if m:
                rec["frbrWork"] = m.group(1).decode("utf-8", errors="replace")
            if parsed is None:
                rec["parseerbaar"] = False
                uit.append(rec)
                continue
            rec["parseerbaar"] = True
            rec["aantalPolygonen"] = parsed["aantalPolygonen"]
            vorm = parsed["vorm"]
            rec["snijdtWerkgrens"] = bool(vorm.intersects(werkgrens))
            if rec["snijdtWerkgrens"]:
                rec["overlapHa"] = round(vorm.intersection(werkgrens).area / 10_000, 2)
            uit.append(rec)
    return uit


# ---------------------------------------------------------------- programma-koppeling (bewijs-gebonden)

def koppelregels(ind: dict, gebied: dict) -> list[dict]:
    """Expliciete heuristieken programma/gebied → officiële activiteiten.

    Elke regel: (activiteit, soort, bewijs-zin). Geen verzonnen koppelingen:
    een activiteit zonder bewijs komt niet in de lijst (monument bijv. is een
    open kennissgat — zie de rapportage-grenzen).
    """
    doelen = gebied.get("doelen_uit_toekomstbeeld") or {}
    woningen = doelen.get("woningen_nieuw_feiten_tabel") or 0
    spoor = ind.get("spoorlijn_km") or 0
    panden = ind.get("panden_bestand") or 0
    bomen = (ind.get("vegetatieobject_punt") or 0) + (ind.get("vegetatie_vlak_ha") or 0)
    transformatie = "transformatie" in (gebied.get("type") or "")

    regels = []

    def voeg(toe: bool, activiteit: str, soort: str, bewijs: str):
        if toe:
            regels.append({"activiteit": activiteit, "soort": soort, "bewijs": bewijs})

    voeg(spoor > 0, "WegSpoorwegAanleggenWijz", "gebied",
         f"BGT spoorlijn {spoor} km binnen de werkgrens (indicatoren canonieke run)")
    voeg(woningen > 0, "AnderBouwwerkBouwen", "programma",
         f"programma {woningen} nieuwe woningen (Toekomstbeeld p.14 via gebied.json)")
    voeg(woningen > 0, "BouwwerkVeranderen", "programma",
         f"programma {woningen} nieuwe woningen — veranderen/uitbreiden bestaand bouwwerk")
    voeg(woningen > 0, "BijbehorendBouwwerk", "programma",
         f"programma {woningen} nieuwe woningen — bijbehorende bouwwerken")
    voeg(panden > 0 and transformatie, "BouwwerkSlopen", "programma",
         f"{panden} bestaande panden in gebied + type '{gebied.get('type')}' — "
         "vervangingsbouw is expliciet in scope")
    voeg(bomen > 0, "HoutopstandVellen", "programma+locatie",
         f"bomen/vegetatie in gebied (punten {ind.get('vegetatieobject_punt')}, vlak "
         f"{ind.get('vegetatie_vlak_ha')} ha) — locatie-binding via geoVerwijzing (zie locatie-tabel)")
    voeg(spoor > 0 and woningen > 0, "GeluidProdAndereAct", "programma+gebied",
         f"geluidgevoelig gebruik (wonen) naast {spoor} km spoorlijn in gebied — "
         "heuristiek, geen geluidsberekening")
    return regels


def vragen_per_activiteit(index: dict, activiteiten: set,
                           out_dir: Path = DSO_OUT, instrument: str = INSTRUMENT,
                           cap: int = VRAAG_CAP) -> dict:
    """Officiële loket-vragen per activiteit, direct uit de STTR-bestanden."""
    uit: dict = {}
    for bestand in index.get("bestanden") or []:
        act = bestand.get("activiteit")
        if act not in activiteiten or bestand.get("einddatum"):
            continue
        dmn_pad = out_dir / f"{instrument}.rtr.{bestand['identifier']}.dmn"
        if not dmn_pad.is_file():
            continue
        parsed = parse_sttr(dmn_pad.read_text(encoding="utf-8", errors="replace"))
        vragen = []
        for regel in parsed.get("uitvoeringsregels") or []:
            if "vraag" in regel and regel["vraag"].get("vraagTekst"):
                vragen.append(regel["vraag"]["vraagTekst"])
            elif "vasteWaarde" in regel and regel["vasteWaarde"].get("waardeVraag"):
                vragen.append(regel["vasteWaarde"]["waardeVraag"] + " (vaste waarde)")
            elif "geoVerwijzing" in regel and regel["geoVerwijzing"].get("vraagTekst"):
                vragen.append(regel["geoVerwijzing"]["vraagTekst"] + " (geo)")
        rec = uit.setdefault(act, {
            "bestanden": [], "totaalVragen": 0, "projecteerbaar": 0, "decisions": 0,
        })
        rec["bestanden"].append({
            "rtrId": bestand["identifier"],
            "begindatum": bestand.get("begindatum"),
            "dmnVersie": bestand.get("dmnVersie"),
            "vragen": vragen[:cap],
            "meerVragen": max(0, len(vragen) - cap),
        })
        rec["totaalVragen"] += len(vragen)
        rec["projecteerbaar"] += sum(
            1 for d in bestand.get("decisions") or [] if d.get("projecteerbaar"))
        rec["decisions"] += len(bestand.get("decisions") or [])
    return uit


def laatste_indicatoren(runs_dir: Path = ROOT / "runs") -> tuple[dict, Path]:
    run_dirs = sorted(d for d in runs_dir.glob("*-gebiedscheck") if d.is_dir())
    if not run_dirs:
        raise SystemExit("geen canonieke gebiedscheck-run gevonden — draai eerst run.py")
    pad = run_dirs[-1] / "indicators.json"
    return json.loads(pad.read_text(encoding="utf-8")), pad


# ---------------------------------------------------------------- rapport

def schrijf_rapport(run_dir: Path, data: dict) -> None:
    regels = [
        f"# Het loket over de Spoorzone — {data['runId']}",
        "",
        f"*Run {utcnow()} · engine `poc-veenendaal/sttr.py` · officiële toepasbare regels "
        f"(STTR/DMN) uit de RTR — **vragen, geen besluit** (doctrine: rekenlaag beslist, "
        f"mens beslist).*",
        "",
        f"**Bevoegd gezag:** gemeente Veenendaal (gm0345) · OIN `{data['oin']}` · "
        f"**{data['totaalBestanden']}** geldige STTR-bestanden in de RTR "
        f"({data.get('dmnVersiesTekst') or data['dmnVersies']}; begindata "
        f"{data['begindatumMin']} → {data['begindatumMax']}).",
        f"**Omgevingsplan:** {data['regeling'].get('officieleTitel', '—')} "
        f"(`{data['regeling'].get('identificatie', '—')}`).",
        "",
        "## 1 · Locatie-gebonden vragen (geoVerwijzing ∩ werkgrens)",
        "",
    ]
    loc = data.get("locatieGebonden") or {}
    if loc.get("status") == "gemeten":
        vs = loc["verwijzingen"]
        per_status: dict[str, int] = {}
        for v in vs:
            per_status[v.get("status", "afwezig-in-pakket")] = \
                per_status.get(v.get("status", "afwezig-in-pakket"), 0) + 1
        regels += [
            f"Van de **{len(vs)} locatie-gebonden verwijzingen**: "
            f"**{per_status.get('gekoppeld', 0)} gekoppeld** aan geometrie in het pakket · "
            f"{per_status.get('aanwezig-als-ow-object', 0)} aanwezig als OW-object "
            "(geometrie zit niet in dít uitwisselpakket — de GIO-aanlevering loopt apart) · "
            f"{per_status.get('afwezig-in-pakket', 0)} afwezig "
            "(leveranciers-identificatiefamilie uit de STTR-maker, niet in het omgevingsplan).",
            "",
        ]
        rijen = [v for v in vs if v.get("status") == "gekoppeld" and v.get("snijdtWerkgrens")]
        if rijen:
            regels += [
                "| Activiteit | Vraag in het loket | Locatie (GIO) | Overlap | Geldig sinds |",
                "|---|---|---|---:|---|",
            ]
            for v in rijen:
                regels.append(
                    f"| {v.get('activiteit') or '?'} | {v.get('vraagTekst') or '(geo-vraag zonder tekst)'} | "
                    f"`{v.get('locatieIdentificatie')}` | {v.get('overlapHa', '?')} ha | "
                    f"{v.get('begindatum')} |"
                )
            regels.append("")
        else:
            regels += [
                "Geen van de koppelbare locaties snijdt de (bbox-)werkgrens. De overige "
                "locatie-gebonden vrágen gelden wel in het loket — hun gebied is via dit "
                "pakket alleen niet meetbaar (zie de statusverdeling hierboven).",
                "",
            ]

        alle_gios = loc.get("gios") or []
        snijdend = [g for g in alle_gios if g.get("snijdtWerkgrens")]
        regels += [
            "### Officiële GIO-lagen over de werkgrens (sweep — géén STTR-koppeling)",
            "",
            f"Het uitwisselpakket bevat {len(alle_gios)} GIO's "
            f"({sum(1 for g in alle_gios if not g.get('parseerbaar', True))} niet parseerbaar); "
            f"**{len(snijdend)} snijden de werkgrens**:",
            "",
            "| GIO (bestand) | FRBRWork | Overlap |",
            "|---|---|---:|",
        ]
        for g in sorted(snijdend, key=lambda x: -(x.get("overlapHa") or 0)):
            regels.append(
                f"| {g.get('bestand', '?')[:-4]} | `{g.get('frbrWork', '—')}` | "
                f"{g.get('overlapHa', '?')} ha |"
            )
        regels += [
            "",
            "Dit zijn officiële omgevingsplan-geometrielagen (STOP-FRBRWork) over het gebied. "
            "De doorvertaling naar de specifieke STTR-vragen hierboven is in dit pakket níet "
            "legbaar — naam- of interpretatie-afstemming zou gokken zijn; open punt.",
            "",
        ]
    else:
        regels += [f"Nog niet gemeten — {loc.get('reden', 'draai zonder --skip-live')}."]

    regels += [
        "",
        "## 2 · Programma-gebonden vragen (bewijs per koppeling)",
        "",
        "| Activiteit | Soort | Bewijs |",
        "|---|---|---|",
    ]
    regels += [
        f"| {r['activiteit']} | {r['soort']} | {r['bewijs']} |"
        for r in data["programmaGebonden"]
    ]
    regels += ["", "## 3 · De officiële vragen per activiteit", ""]
    for act, rec in sorted(data["activiteiten"].items()):
        if not rec["bestanden"]:
            continue
        regels += [f"### {act}", ""]
        regels.append(
            f"{rec['totaalVragen']} officiële vragen over {len(rec['bestanden'])} bestand(en) · "
            f"{rec['projecteerbaar']}/{rec['decisions']} decisions uitvoerbaar op de eigen engine "
            "(zie docs/POC_STTR_IMTR_KANSEN.md)."
        )
        regels.append("")
        for b in rec["bestanden"]:
            regels.append(
                f"- **RTR {b['rtrId']}** (geldig sinds {b['begindatum']}, DMN {b['dmnVersie']}):")
            for v in b["vragen"]:
                regels.append(f"  - {v}")
            if b["meerVragen"]:
                regels.append(f"  - … nog {b['meerVragen']} vragen (zie het bestand)")
        regels.append("")

    regels += [
        "## Beperkingen & vervolg",
        "",
        "- Dit zijn de officiële **vragen** (STTR) — geen besluit: de conclusie-enum "
        "(Vergunningplicht/Toestemmingsvrij/…) volgt pas met een concreet voorstel.",
        "- Locatie-binding is gemeten tegen de **provisionele bbox-werkgrens** (run.py, "
        "gebied.json); met de officiële gebiedsgrens kunnen overlappingen verschuiven.",
        "- Programma-koppelingen zijn **gelabelde heuristieken met bewijs**. Monumentstatus "
        "op Rijksniveau blijft een open kennissgat (RCE-register is de bron, niet BAG/BGT); "
        "de GIO-sweep levert wél de gemeentelijke monumentenlaag over het gebied (zie §1).",
        "- PRE, niet prod; de RTR-metadata kent geen namen — bevoegd gezag via de gm-code "
        "(zie de correctie-notitie in POC_STTR_IMTR_KANSEN.md).",
        "",
        "*Artefacten: `loketvragen.json` · `manifest.json` · STTR-cache: "
        "`nldt/simulation/regelrecht/dso_overlap/out/veenendaal.rtr.*`.*",
    ]
    (run_dir / "report.md").write_text("\n".join(regels), encoding="utf-8")


# ---------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    refresh = "--refresh" in argv
    skip_live = "--skip-live" in argv

    gebied = json.loads((DATA / "gebied.json").read_text(encoding="utf-8"))
    ind, ind_pad = laatste_indicatoren()
    bbox_rd = gebied["werkgrens"]["bbox_rd"]
    anker_rd = gebied["ankers"][0]["rd"]

    sttr = lees_sttr_cache()
    index, rtr = sttr["index"], sttr["rtr"]
    verwijzingen = geo_verwijzingen(index)
    print(f"STTR-cache: {index['totals']['bestanden']} bestanden · "
          f"{len(verwijzingen)} geoVerwijzing-vragen")

    locatieGebonden: dict = {"status": "niet-gemeten",
                             "reden": "draai zonder --skip-live (Presenteren + downloaden-API)"}
    bronnen = [
        {"bron": "sttr-index", "pad": str(sttr["paden"]["index"]),
         "sha256": sha256_file(sttr["paden"]["index"])},
        {"bron": "rtr-cache", "pad": str(sttr["paden"]["rtr"]),
         "sha256": sha256_file(sttr["paden"]["rtr"])},
        {"bron": "gebiedscheck-indicatoren", "pad": str(ind_pad),
         "sha256": sha256_file(ind_pad)},
        {"bron": "gebied.json", "pad": str(DATA / "gebied.json"),
         "sha256": sha256_file(DATA / "gebied.json")},
    ]
    regeling = None
    if not skip_live:
        print("→ Presenteren regelingen/_zoek op het ankerpunt…")
        regeling, reg_meta = zoek_omgevingsplan(
            {"type": "Point", "coordinates": anker_rd}, refresh=refresh)
        bronnen.append({"bron": "presenteren-regelingen",
                        "pad": str(CACHE / "presenteren-regelingen.json"),
                        "sha256": reg_meta.get("sha256")})
        print(f"  omgevingsplan: {regeling['identificatie']}")
        pakket, pak_meta = haal_uitwisselpakket(regeling["identificatie"], refresh=refresh)
        bronnen.append({"bron": "ow-uitwisselpakket", "pad": str(pakket),
                        "sha256": pak_meta.get("sha256"), "bytes": pak_meta.get("bytes")})
        print(f"  pakket: {(pak_meta.get('bytes') or 0) / 1e6:.1f} MB")
        print("→ geoVerwijzingen koppelen aan de werkgrens…")
        gekoppeld, samenvatting = koppel_geo_aan_werkgrens(verwijzingen, pakket, bbox_rd)
        print("→ alle GIO's in het pakket tegen de werkgrens sweepen…")
        gios = sweep_gios_tegen_werkgrens(pakket, bbox_rd)
        locatieGebonden = {"status": "gemeten", "verwijzingen": gekoppeld,
                           "samenvatting": samenvatting, "gios": gios}
        in_gebied = [v for v in gekoppeld
                     if v.get("status") == "gekoppeld" and v.get("snijdtWerkgrens")]
        snijdend = [g for g in gios if g.get("snijdtWerkgrens")]
        print(f"  verwijzingen: {len(in_gebied)} gekoppeld+in gebied van {len(gekoppeld)}")
        print(f"  GIO-sweep: {len(snijdend)}/{len(gios)} GIO's snijden de werkgrens")
        regeling = {**regeling, "pakketSha256": pak_meta.get("sha256")}

    programma = koppelregels(ind, gebied)
    activiteiten = {r["activiteit"] for r in programma} | {
        v["activiteit"] for v in (locatieGebonden.get("verwijzingen") or [])
        if v.get("status") == "gekoppeld" and v.get("snijdtWerkgrens")
    }
    vragen = vragen_per_activiteit(index, activiteiten)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-loketvragen"
    run_dir = RUNS / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    begindata = sorted(
        {b.get("begindatum") for b in index.get("bestanden") or [] if b.get("begindatum")},
        key=lambda d: datetime.strptime(d, "%d-%m-%Y"),
    )
    dmn_versies = index["totals"].get("dmnVersies") or {}
    dmn_tekst = " + ".join(f"{n}× DMN {v}" for v, n in sorted(dmn_versies.items()))
    data = {
        "runId": run_id,
        "gegenereerdOp": utcnow(),
        "gebied": gebied.get("gebied"),
        "oin": rtr.get("oin"),
        "totaalBestanden": index["totals"]["bestanden"],
        "dmnVersies": dmn_versies,
        "dmnVersiesTekst": dmn_tekst,
        "begindatumMin": begindata[0] if begindata else None,
        "begindatumMax": begindata[-1] if begindata else None,
        "regeling": regeling or {"status": "niet opgehaald (--skip-live)"},
        "locatieGebonden": locatieGebonden,
        "programmaGebonden": programma,
        "activiteiten": vragen,
    }
    (run_dir / "loketvragen.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    schrijf_rapport(run_dir, data)
    (run_dir / "manifest.json").write_text(
        json.dumps({"runId": run_id, "gegenereerdOp": utcnow(), "bronnen": bronnen},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n✓ run {run_id}")
    if locatieGebonden.get("status") == "gemeten":
        van = {}
        for v in locatieGebonden.get("verwijzingen") or []:
            van[v.get("status", "?")] = van.get(v.get("status", "?"), 0) + 1
        print(f"  locatie-gebonden: {van} · "
              f"GIO's snijden werkgrens: "
              f"{len([g for g in locatieGebonden.get('gios') or [] if g.get('snijdtWerkgrens')])}"
              f"/{len(locatieGebonden.get('gios') or [])}")
    else:
        print(f"  locatie-gebonden: {locatieGebonden.get('status')}")
    print(f"  programma-koppelingen: {len(programma)} · rapport: {run_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
