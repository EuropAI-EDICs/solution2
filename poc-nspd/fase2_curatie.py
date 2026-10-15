"""Fase-2 curatie-driver (plan 2026-10-14-poc-nspd-fase2, taken 3-7).

Config-gedreven: per (track, land) een lijst curatorkeuzes — welke artikel-
vindplaats uit de extractor-kandidaten gepromoveerd wordt, met handgeschreven
claim/legalForce/rule-vorm. Citaten worden machinaal uit de kandidaat-records
overgenomen (garandeert letterlijkheid; quote_guard.py is de na-controle).

Niet-gepromoveerde kandidaten landen automatisch in de rejected-ledger met
reden. Elke groepstaak voegt z'n GROEP-config toe en draait:

    .venv/bin/python fase2_curatie.py <groep>

Herbruikbaar voor T4-T7: zelfde structuur, eigen GROEP-dict.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from pipeline.evidence_extract import extract_candidates, merge_brondocumenten  # noqa: E402

VANDAAG = "2026-10-14"
SESSIE = "curator#poc-nspd-fase2"

_PREFIX = {  # evidence-id-prefix per (land, track); NC-prefix per track
    "nl": {"bos": "EVB", "water": "EVD", "bodem": "EVO", "mobiliteit": "EVM",
           "landschap": "EVL", "landbouw": "EVG", "wonen": "EVH", "werken": "EVJ",
           "recreatie": "EVR", "biomassa": "EVX"},
    "be": {"bos": "BVB", "water": "BVD", "bodem": "BVO", "mobiliteit": "BVM",
           "landschap": "BVL", "landbouw": "BVG", "wonen": "BVH", "werken": "BVJ",
           "recreatie": "BVR", "biomassa": "BVX"},
}
_NC = {"bos": "BOS", "water": "WAT", "bodem": "BOD", "mobiliteit": "MOB",
       "landschap": "LAN", "landbouw": "LNB", "wonen": "WON", "werken": "WER",
       "recreatie": "REC", "biomassa": "BIO"}

# start-trefwoorden per track (curator-basis; uitbreiding via keuzes-trefwoorden)
TREFWOORDEN = {
    "bos": ("bos", "bosbouw", "bosaanplant", "houtige"),
    "water": ("waterkering", "oppervlaktewater", "grondwater", "watervogel",
              "waterstaat", "overstromings"),
    "bodem": ("bodem", "bodemkwaliteit", "bodemsanering", "grond", "ontgronding"),
    "mobiliteit": ("weg", "verkeer", "infrastructuur", "wegen"),
    "landschap": ("landschap", "cultuurlandschap", "kernkwaliteit", "landschappelijk"),
    "landbouw": ("landbouw", "agrarisch", "glastuinbouw", "veehouderij"),
    "wonen": ("wonen", "woningbouw", "woning"),
    "werken": ("bedrijventerrein", "industrie", "bedrijvigheid", "werken"),
    "recreatie": ("recreatie", "dagrecreatie", "verblijfsrecreatie", "toerisme"),
    "biomassa": ("biomassa", "vergisting", "houtige", "bio"),
}

# --------------------------------------------------------------- #
# Groepconfiguraties: alleen de gepromoveerde keuzes; occ = index
# van de vindplaats onder kandidaten met dezelfde locator (0-based).
# --------------------------------------------------------------- #
GROEPEN: dict[str, dict] = {
    "t3": {
        ("bos", "nl"): [
            dict(locator="Artikel 14.2", occ=0, bron="S01",
                 claim="Chapter 14 rules serve nature conservation, maintenance of the forested area in Zeeland and protection of landscape values (stated objective).",
                 legalForce="interpretive", rule_type="zone_attention", semantics="attention",
                 note="Oogmerk-artikel: doelbepaling, geen executabele norm; aandachtmarker."),
            dict(locator="Artikel 14.4", occ=0, bron="S01",
                 claim="The national felling-notification prohibition does not apply to rejuvenation gaps up to 1.5x tree height and jointly max 10% of the forest complex, and only after earlier gaps reached 60% cover.",
                 legalForce="binding", rule_type="zone_conditional", semantics="conditional",
                 note="Uitzondering op meldplicht vellen; numeriek conditioneel, zone-loos."),
            dict(locator="Artikel 14.5", occ=0, bron="S01",
                 claim="Replanting must be silviculturally sound: replanted area at least equal to the felled area, closed canopy within ten years and demonstrable growth within three years.",
                 legalForce="binding", rule_type="procedural_condition", semantics="conditional",
                 note="Herbeplantingseisen: kwaliteitsnormen voor nieuwe beplanting; kernnorm voor forest planting."),
        ],
        ("bos", "be"): [
            dict(locator="Artikel 3", occ=0, bron="rup-zeehaven-gent-fase2",
                 claim="The GRUP zeehavengebied Gent phase-2 designates a Bosgebied (forest area, linkage zone) for the preservation, development and recovery of forest.",
                 legalForce="binding", rule_type="zone_inclusion", semantics="inclusion",
                 note="Bestemmingsartikel bosgebied; vlakken uitsluitend cartografisch (bijlage I), geen geo-pin → zone-loos, V4."),
            dict(locator="Artikel 7", occ=0, bron="gewestplan-voorschriften",
                 claim="The Gewestplan aanvullende voorschriften designate 'uitbreidingsgebied voor bos' (forest expansion area, BVR 13/07/01) with the forest destination as ground colour.",
                 legalForce="binding", rule_type="zone_inclusion", semantics="inclusion",
                 note="Gewestplan-bosuitbreiding; OCR-spatiatie in bron ('uitbreidingsg ebied') letterlijk overgenomen (sic)."),
        ],
        ("water", "nl"): [
            dict(locator="Artikel 2.4", occ=0, bron="S01",
                 claim="A permit for an activity with possible consequences for a KRW surface-water or groundwater body may not lead to non-compliance with the applicable environmental values and programmes.",
                 legalForce="binding", rule_type="zone_conditional", semantics="conditional",
                 note="Beoordelingsregel waterlichaam; delta-breed, zone-loos conditioneel."),
            dict(locator="Artikel 13.4", occ=0, bron="S01",
                 claim="It is prohibited, without an omgevingsvergunning, to remove, hold or transport aquatic plants and animals (or objects evidently serving that purpose) along, on or under a surface water.",
                 legalForce="binding", rule_type="zone_conditional", semantics="conditional",
                 note="Vergunningplicht onderwater flora/fauna: verbod zonder vergunning; zone-loos (oppervlaktewaterlichamen niet als GIO gepind)."),
            dict(locator="Artikel 18.37", occ=1, bron="S01",
                 claim="Activities within a restriction zone of a regional flood defence are only permitted if no obstruction arises for the maintenance, safety or reinforcement of that defence.",
                 legalForce="binding", rule_type="zone_exclusion", semantics="exclusion",
                 note="Instructieregel regionale waterkeringen; kaart 'regionale waterkeringen' niet als geo-pin in dit corpus → zone-loze exclusion met caveat."),
        ],
        ("water", "be"): [
            dict(locator="Artikel 3", occ=0, bron="rup-zeehaven-gent-papierbedrijf",
                 claim="The GRUP designates a zone for surface-water abstraction and treatment installations where all works and actions necessary or useful for that purpose are permitted.",
                 legalForce="binding", rule_type="zone_inclusion", semantics="inclusion",
                 note="Oppervlaktewatercaptatie-zone; vlakken cartografisch, geen geo-pin → zone-loos, V4."),
            dict(locator="Artikel 9", occ=0, bron="gewestplan-voorschriften",
                 claim="In a controlled flooding area (gecontroleerd overstromingsgebied, BVR 01/06/99) all actions and works serving the water system's flood function are possible; other spatial claims are subordinate.",
                 legalForce="binding", rule_type="zone_exclusion", semantics="exclusion",
                 note="Overstromingsgebied = waterveiligheidsfunctie; exclusion-flavored bestemming, cartografisch → zone-loos, V4 (OCR-spatiatie 'overstro mingsgebied' sic)."),
        ],
    },
}

GROEPEN["t4"] = {
    ("bodem", "nl"): [
        dict(locator="Artikel 5.19", occ=2, bron="S01",
             claim="It is prohibited to store, tranship, transport or bring solid or liquid harmful substances onto or into the soil without an omgevingsvergunning.",
             legalForce="binding", rule_type="zone_conditional", semantics="conditional",
             note="Vergunningplicht schadelijke stoffen op/in de bodem; kernbodemnorm, zone-loos."),
        dict(locator="Artikel 5.21", occ=2, bron="S01",
                 claim="In a water-abstraction area or groundwater protection zone it is prohibited without permit to apply soil or dredged sludge that does not meet the 'wonen' quality class.",
                 legalForce="binding", rule_type="zone_conditional", semantics="conditional",
                 note="Bodemkwaliteitsnorm grond/baggerspecie in beschermingszones; zones (waterwingebied) niet als geo-pin in corpus."),
        dict(locator="Artikel 8.3", occ=2, bron="S01",
             claim="No omgevingsvergunning is required for soil-excavation activities that qualify as ground cultivation for normal agriculture, horticulture or forestry practice.",
             legalForce="binding", rule_type="scope_declaration", semantics="conditional",
             note="Vergunningvrije ontgrondingen (uitzonderingscategorieën); scope-bepaling voor bodemactiviteiten."),
    ],
    # BE-bodem: geen specifieke bodemnorm in het haven-corpus (GRUP's, gewestplan,
    # VCRO zijn bestemmings-/procedureel) → expliciete abstention i.p.v. fabuleren
    ("bodem", "be"): [],
    ("mobiliteit", "nl"): [
        dict(locator="Artikel 3.2", occ=2, bron="S01",
             claim="The provincial-road rules aim to preserve the condition and the effective, safe operation of a provincial road, including the interest of widening.",
             legalForce="interpretive", rule_type="zone_attention", semantics="attention",
             note="Oogmerk provinciale wegen: kaderbepaling, aandachtmarker."),
        dict(locator="Artikel 3.3", occ=2, bron="S01",
             claim="Anyone who knows or reasonably suspects that an activity may adversely affect the provincial-road interests must take all reasonably practicable preventive measures.",
             legalForce="binding", rule_type="zone_attention", semantics="attention",
             note="Specifieke zorgplicht provinciale wegen: gedragsnorm, geen executabele geometrie."),
        dict(locator="Artikel 3.9", occ=2, bron="S01",
             claim="Without an omgevingsvergunning it is prohibited to have or make an access road (uitweg) to a provincial road, or to modify an existing one, within the provincial-road management restriction zone.",
             legalForce="binding", rule_type="zone_conditional", semantics="conditional",
             note="Vergunningplicht uitwegen in beperkingengebied beheer provinciale wegen; beperkingengebied-kaart niet als geo-pin in corpus → zone-loos."),
    ],
    ("mobiliteit", "be"): [
        dict(locator="Artikel 17", occ=0, bron="rup-zeehaven-gent-fase2",
             claim="The GRUP designates a road-infrastructure area in which all actions for the construction, management and operation of road infrastructure and accessories are permitted.",
             legalForce="binding", rule_type="zone_inclusion", semantics="inclusion",
             note="Wegeninfrastructuurgebied; vlakken cartografisch (bijlage I) → zone-loos, V4."),
        dict(locator="Artikel 2", occ=0, bron="rup-zeehaven-gent-papierbedrijf",
             claim="The GRUP designates a port-access-road zone in which all works, actions and structures necessary or useful for constructing and operating that road are permitted.",
             legalForce="binding", rule_type="zone_inclusion", semantics="inclusion",
             note="Havenontsluitingsweg-zone; cartografisch → zone-loos, V4."),
    ],
}

GROEPEN["t5"] = {
    ("landschap", "nl"): [
        dict(locator="Artikel 18.41", occ=2, bron="S01",
             claim="An omgevingsplan setting rules for land within a 100-metre assessment zone around an existing nature area must motivate how the nature area is taken into account.",
             legalForce="binding", rule_type="zone_attention", semantics="attention",
             note="Afwegingszone natuurgebieden (bijlage XII/4): motiveringseis; zone (100m rond natuurgebied) zonder geo-pin → zone-loos."),
        dict(locator="Artikel 18.42", occ=2, bron="S01",
             claim="An omgevingsplan affecting landscapes, landscape elements or cultural-historically valuable farms must provide insight into the landscape and cultural-historic values in its motivation.",
             legalForce="binding", rule_type="zone_attention", semantics="attention",
             note="Landschap en erfgoed (bijlage VII): motiveringseis landschapskwaliteit; kernlandschapsnorm, zone-loos."),
    ],
    ("landschap", "be"): [
        dict(locator="Artikel 6", occ=0, bron="rup-zeehaven-gent-fase2",
             claim="The park-area actions permitted under the GRUP are only allowed insofar as spatial coherence, cultural-historical and landscape values of the area are not disproportionate affected.",
             legalForce="binding", rule_type="zone_conditional", semantics="conditional",
             note="Landschappelijke en functionele inpassing parkgebied; inpassingsvoorwaarde, cartografisch → zone-loos, V4."),
        dict(locator="Artikel 3", occ=1, bron="gewestplan-voorschriften",
             claim="The Gewestplan designates zones of cultural-historical value: areas with buildings protected as monument or townscape, where spatial changes must respect that protection.",
             legalForce="binding", rule_type="zone_attention", semantics="attention",
             note="Zone met cultuurhistorische waarde (BVR 13/07/01); aandachtmarker, cartografisch → zone-loos."),
    ],
    ("landbouw", "nl"): [
        dict(locator="Artikel 18.36", occ=2, bron="S01",
             claim="An expansion permit for livestock farming is not refused if the ammonia emission from the barns after expansion does not exceed the emission beforehand, among other conditions.",
             legalForce="binding", rule_type="zone_conditional", semantics="conditional",
             note="Toelaatbare wijziging veehouderij: emissie-uitzondering; kernlandbouwnorm, zone-loos."),
        dict(locator="Artikel 18.39", occ=2, bron="S01",
             claim="An omgevingsplan applying to an Agrarian area of ecological meaning must also set rules protecting the ecological value of that area alongside rules for agricultural activities.",
             legalForce="binding", rule_type="zone_attention", semantics="attention",
             note="Agrarisch gebied van ecologische betekenis (bijlage XII/2): dubbelbestemming; kaart niet gepind → zone-loos."),
    ],
    ("landbouw", "be"): [
        dict(locator="Artikel 7", occ=0, bron="rup-zeehaven-gent-fase2",
             claim="The GRUP designates an agricultural area (koppelingsgebied) for professional farming that buffers the port activities from adjacent functions.",
             legalForce="binding", rule_type="zone_inclusion", semantics="inclusion",
             note="Agrarisch gebied-bestemming; vlakken cartografisch → zone-loos, V4."),
        dict(locator="Artikel 5", occ=0, bron="gewestplan-voorschriften",
             claim="In bouwvrij agrarisch gebied (building-free agricultural area, BVR 13/07/01) an absolute building ban applies, with exceptions only for shelters and specific utility works.",
             legalForce="binding", rule_type="zone_exclusion", semantics="exclusion",
             note="Bouwvrij agrarisch gebied: absoluut bouwverbod; exclusion-karakter, cartografisch → zone-loos, V4."),
    ],
}

_ABSTENTIES = {  # groep → (track, land, reden) voor lege keuzes-lijsten
    "t4": ("bodem", "be",
           "geen specifieke bodemnorm in het BE-havencorpus: GRUP's en gewestplan bevatten "
           "bestemmingsvoorschriften zonder bodembeschermende bepalingen; VCRO is procedureel — "
           "cite-or-abstain: onthouding gedocumenteerd i.p.v. geforceerde koppeling"),
}


def _kandidaten(track: str, land: str, bron_tekst: str, source_url: str, bron_label: str) -> list[dict]:
    return extract_candidates(tekst=bron_tekst, track=track, trefwoorden=TREFWOORDEN[track],
                              jurisdictie=land, source_url=source_url, bron_label=bron_label)


def _tekst_en_url(land: str, bron: str) -> tuple[str, str, str]:
    """(tekst, sourceUrl, bron-label) voor S01 resp. een BE-instrument-id."""
    reg = json.loads((ROOT / "corpus" / "sources.json").read_text(encoding="utf-8"))
    if bron == "S01":
        return (ROOT / "corpus" / "nl" / "CVDR709135" / "tekst.txt").read_text(encoding="utf-8"), \
            reg["S01"]["uri"], "S01"
    for ins in json.loads((ROOT / "corpus" / "be" / "META.json").read_text(encoding="utf-8"))["instrumenten"]:
        if ins["id"] == bron:
            txt = ROOT / "corpus" / "be" / ins["bestand"].replace(".pdf", ".txt")
            return txt.read_text(encoding="utf-8"), ins["bronUrl"], bron
    raise KeyError(bron)


def _instrumentstring(land: str, bron: str) -> tuple[str, str]:
    """(instrument-beschrijving, instrumentType) conform corpus/sources.json."""
    reg = json.loads((ROOT / "corpus" / "sources.json").read_text(encoding="utf-8"))
    if bron == "S01":
        return reg["S01"]["title"] + " (" + reg["S01"]["version"] + ")", "omgevingsverordening-nl"
    types = {"rup": "rup-be", "gewestplan": "gewestplan-be", "vcro": "vcro-be"}
    itype = next(v for k, v in types.items() if bron.startswith(k))
    return reg[_docid_voor(bron)]["title"] + " (" + reg[_docid_voor(bron)]["version"] + ")", itype


def _docid_voor(bron: str) -> str:
    return {"rup-zeehaven-gent-fase2": "S02", "rup-zeehaven-gent-papierbedrijf": "S03",
            "gewestplan-voorschriften": "S04", "vcro": "S05"}[bron]


def verwerk_groep(groep: str) -> None:
    for (track, land), keuzes in GROEPEN[groep].items():
        cache: dict[str, list[dict]] = {}

        def kandidaten_voor(bron: str) -> list[dict]:
            if bron not in cache:
                tekst, url, label = _tekst_en_url(land, bron)
                cache[bron] = _kandidaten(track, land, tekst, url, label)
            return cache[bron]

        ev_prefix = _PREFIX[land][track]
        nc_prefix = _NC[track]
        evidence, kaarten, rules, rejected = [], [], [], []
        gekozen_ids: set[str] = set()
        for i, kz in enumerate(keuzes, start=1):
            kand = [c for c in kandidaten_voor(kz["bron"]) if c["locator"] == kz["locator"]]
            c = kand[kz["occ"]]
            evid = f"{ev_prefix}-{i:02d}"
            ncid = f"NC-{nc_prefix}-{i:02d}"
            frid = f"FR-{nc_prefix}-{i:02d}"
            docid = "S01" if kz["bron"] == "S01" else _docid_voor(kz["bron"])
            regels_reg = json.loads((ROOT / "corpus" / "sources.json").read_text(encoding="utf-8"))[docid]
            instrument, itype = _instrumentstring(land, kz["bron"])
            evidence.append({**c, "id": evid, "verified": True,
                             "note": kz["note"] + " [curator-locatie: fase2-curatie]"})
            kaarten.append({
                "id": ncid, "evidenceId": evid, "claim": kz["claim"],
                "source": {"docId": docid, "article": kz["locator"],
                           "version": regels_reg["version"], "quote": c["quote"],
                           "quoteLanguage": "nl", "uri": regels_reg["uri"],
                           "retrievedAt": regels_reg["retrievedAt"]},
                "instrument": instrument, "instrumentType": itype, "jurisdictie": land,
                "legalForce": kz["legalForce"], "theme": _theme(track),
                "confidence": 0.9, "verified": True,
                "extractedBy": SESSIE + f"-{groep}", "extractedAt": VANDAAG,
                "appliesTo": {"objectType": _objecttype(track), "track": track},
                "notes": kz["note"],
            })
            rules.append({
                "id": frid, "normCardId": ncid,
                "status": "ambiguous" if kz["semantics"] in ("attention",) or "zone_loos" else "formalized",
                "ruleType": kz["rule_type"], "zoneSemantics": kz["semantics"],
                "instrumentType": itype, "jurisdictie": land,
                "appliesTo": {"objectType": _objecttype(track),
                              "contextTags": _contexttags(track, kz)},
                "executableRef": "engine.procedural.human_review@poc-v1",
                "formalizedBy": SESSIE.replace("curator", "norm-formalizer") + f"-{groep}",
                "formalizedAt": VANDAAG,
                "reason": kz["note"] + " Zone-loos gedocumenteerd; routeert naar V4.",
            })
            gekozen_ids.add(f"{kz['bron']}|{kz['locator']}|{kz['occ']}")
        # lege groep = expliciete abstention (cite-or-abstain) indien geregistreerd
        if not keuzes:
            abstentie = _ABSTENTIES.get(groep)
            if abstentie and abstentie[:2] == (track, land):
                rejected.append({"id": f"{_PREFIX[land][track]}-A01", "track": track,
                                 "locator": "-", "bron": "-",
                                 "reden": "abstention (geen kaarten): " + abstentie[2]})
        # niet-gepromoveerde kandidaten → rejected-ledger met generieke redenen
        for bron in cache:
            for j, c in enumerate(kandidaten_voor(bron)):
                sleutel = f"{bron}|{c['locator']}|{j}"
                if sleutel in gekozen_ids:
                    continue
                rejected.append({
                    "id": f"{ev_prefix}-R{len(rejected)+1:02d}", "track": track,
                    "locator": c["locator"], "bron": bron,
                    "reden": "niet juridisch dragend voor deze track (curatie fase 2): "
                             "raakvlak, toelichting-herhaling of ander beleidsterrein",
                })
        for naam, data in (("evidence", evidence), ("normcards", kaarten),
                           ("formal-rules", rules)):
            pad = ROOT / "corpus" / f"{naam}-{land}-{track}.json"
            pad.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"geschreven: {pad.relative_to(ROOT)} ({len(data)})")
        pad = ROOT / "corpus" / f"normcards-rejected-{land}-{track}.json"
        pad.write_text(json.dumps(rejected, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"geschreven: {pad.relative_to(ROOT)} ({len(rejected)} demoties)")


def _objecttype(track: str) -> str:
    return {"bos": "forest_planting", "water": "riparian_development",
            "bodem": "soil_activity", "mobiliteit": "roadside_development",
            "landschap": "landscape_intervention", "landbouw": "agricultural_expansion",
            "wonen": "housing_development", "werken": "business_development",
            "recreatie": "recreation_development", "biomassa": "biomass_installation"}[track]


def _theme(track: str) -> str:
    return {"bos": "forest:aanplant", "water": "water:waterstaat",
            "bodem": "bodem:activiteit", "mobiliteit": "spatial:infra",
            "landschap": "landscape:kwaliteit", "landbouw": "landbouw:uitbreiding",
            "wonen": "wonen:ontwikkeling", "werken": "werken:bedrijventerrein",
            "recreatie": "recreatie:voorziening", "biomassa": "energy:biomassa"}[track]


def _contexttags(track: str, kz: dict) -> list[str]:
    tags = ["zone_loos_gedocumenteerd", "v4_human_review"]
    tags.append(f"curatie_fase2_{track}")
    if kz["semantics"] == "inclusion":
        tags.append("bestemmingsartikel_cartografisch")
    return tags


if __name__ == "__main__":
    verwerk_groep(sys.argv[1] if len(sys.argv) > 1 else "t3")
