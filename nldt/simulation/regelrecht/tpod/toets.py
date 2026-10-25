"""Punt-toets: formalized RegelRecht-artikelen executeren op TPOD-geo-feiten.

Sluit de cirkel van de bestuurlijke notitie (laag 1 annotatie → laag 2 toets):
per formalized artikel in de DSO-hit wordt elke `execution.input` opgelost als

- **feit** — uit de tpod-index: `in_werkingsgebied` (artikel zit in de punt-hit)
  of een zone-input die uniek matcht op een gebiedsaanwijzing-naam uit de hit;
- **afwezigheid** — geen enkele hit-gebiedsaanwijzing matcht: `false`
  (punt-in-gebied: wat de DSO op het punt níét annoteert geldt daar niet);
  expliciet gelabeld, want gebaseerd op afwezigheid;
- **scenario** — voorstelafhankelijke booleans (strijd met het tijdelijk deel,
  verbodsaard van de activiteit, IWT-voorschriften): alle polariteitscombinaties
  worden doorgerekend en in het rapport als scenario gemarkeerd, nooit als feit
  verkocht;
- **onbekend** — niet op te lossen (bijv. numerieke activiteitparameters) →
  artikel blijft onthouding (MC-6).

Alle uitkomsten komen uit de deterministische reference-engine; een EngineError
wordt als `engineFout`-artikel gerapporteerd, nooit gefixt of weggeschreven.
Zie docs/POC_TPOD_IMOW_KANSEN.md, kans 1.
"""
from __future__ import annotations

import itertools
import re
from typing import Any

from nldt.simulation.regelrecht import reference_engine
from nldt.simulation.regelrecht.tpod.index import artikel_sleutel

CONTRACT = "punt-toets/v1"
SWEEP_CONTRACT = "voorstel-sweep/v1"

#: stoptokens bij het matchen van inputveldnamen op gebiedsaanwijzing-namen
_STOPWOORDEN = {
    "op", "uit", "de", "het", "van", "en", "in", "ter", "een", "voor", "bij",
    "nog", "niet", "te",
}

_INPUT_PREFIXEN = ("in_gebied_", "in_")

#: voorstelafhankelijke booleans: geen feiten maar scenario-variabelen; de
#: toets rekent alle polariteitscombinaties door en labelt ze als scenario.
SCENARIO_VELDEN = {
    "strijd_met_tijdelijk_deel",
    "activiteit_valt_onder_verbod",
    "voorschriften_verbonden_voor_iwt",
}


def _tokens(tekst: str | None) -> set[str]:
    return {
        t
        for t in re.split(r"[^a-z0-9]+", (tekst or "").lower())
        if t and t not in _STOPWOORDEN
    }


def _input_tokens(input_naam: str) -> set[str]:
    kern = input_naam
    for prefix in _INPUT_PREFIXEN:
        if kern.startswith(prefix):
            kern = kern[len(prefix):]
            break
    return _tokens(kern.replace("_", " "))


def match_gebiedsaanwijzing(
    input_naam: str, gebiedsaanwijzingen: list[dict[str, Any]]
) -> str | None | str:
    """Unieke gebiedsaanwijzing-naam die het inputveld aanduidt.

    Geeft de naam, ``None`` (geen kandidaat) of ``"AMBIGU"`` (meerdere
    gelijkbeste kandidaten — dan nooit gokken). Een exacte token-gelijkheid
    wint van een partiële: "Stedelijk gebied" verslaat "Energie uit biomassa
    stedelijk gebied" voor het veld ``in_stedelijk_gebied``. Partiële matches
    moeten ≥ 0,6 zijn en uniek beste, zodat één generiek gedeeld token
    ("gebied") nooit volstaat.
    """
    it = _input_tokens(input_naam)
    if not it:
        return None
    exact: list[str] = []
    best: list[tuple[float, str]] = []
    for ga in gebiedsaanwijzingen:
        gt = _tokens(ga.get("naam"))
        if not gt:
            continue
        if gt == it:
            exact.append(ga.get("naam") or "")
            continue
        score = len(it & gt) / len(it)
        if score >= 0.6:
            best.append((score, ga.get("naam") or ""))
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return "AMBIGU"
    if not best:
        return None
    best.sort(key=lambda p: (-p[0], p[1]))
    if len(best) > 1 and best[0][0] == best[1][0]:
        return "AMBIGU"
    return best[0][1]


def resolve_input(
    input_naam: str,
    *,
    gebiedsaanwijzingen: list[dict[str, Any]],
    voorstel_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Eén inputveld classificeren voor een artikel dat in de punt-hit zit.

    Geeft ``{"bron": …, "waarde": …}`` met bron `presenteren-hit`
    (in_werkingsgebied), `voorstel` (expliciet gegeven in een voorstel-fixture,
    altijd gelabeld), `gebiedsaanwijzing` (unieke naam-match → true),
    `afwezig_in_hit` (geen match bij een ``in_``-zoneveld → false, gelabeld),
    `scenario` (voorstelafhankelijke booleans, zie SCENARIO_VELDEN) of
    `onbekend` (ambiguïteit of een overig veld zonder voorstelwaarde — nooit
    gokken). De afwezigheid-false geldt alleen voor zonevelden: punt-in-gebied
    is een feit ("wat de DSO hier niet annoteert geldt hier niet"), maar de
    afwezigheid van een activiteitparameter uit de hit zegt niets over zijn
    waarde.
    """
    if input_naam == "in_werkingsgebied":
        return {"bron": "presenteren-hit", "waarde": True}
    if voorstel_params is not None and input_naam in voorstel_params:
        return {"bron": "voorstel", "waarde": voorstel_params[input_naam]}
    if input_naam in SCENARIO_VELDEN:
        return {"bron": "scenario", "waarde": None}
    if not input_naam.startswith("in_"):
        return {"bron": "onbekend", "waarde": None, "reden": "geen_zoneveld"}
    match = match_gebiedsaanwijzing(input_naam, gebiedsaanwijzingen)
    if match == "AMBIGU":
        return {"bron": "onbekend", "waarde": None, "reden": "ambigu_gebiedsaanwijzing"}
    if match is not None:
        return {"bron": "gebiedsaanwijzing", "waarde": True, "match": match}
    return {"bron": "afwezig_in_hit", "waarde": False}


def _engine_outputs(
    execution: dict[str, Any], feiten: dict[str, Any]
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return reference_engine.evaluate(execution, feiten)["outputs"], None
    except reference_engine.EngineError as e:
        return None, str(e)


def build_toets(
    *,
    instrument_id: str,
    instrument: dict[str, Any],
    locatie: dict[str, Any] | None,
    tpod_index: dict[str, Any],
    yaml_doc: dict[str, Any],
    gegenereerd_op: str,
    voorstel: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profielen = {p["artikel"]: p for p in tpod_index["artikelProfielen"]}
    form_in_hit = sorted(
        (n for n, p in profielen.items() if p["formalized"]), key=artikel_sleutel
    )
    gebiedsaanwijzingen = tpod_index["geoFeiten"]["gebiedsaanwijzingen"]
    tijdelijk_deel_op_punt = any(
        "tijdelijk" in (g.get("naam") or "").lower() for g in gebiedsaanwijzingen
    )
    noemer_by_ref = {
        l["identificatie"]: l.get("noemer")
        for l in tpod_index["geoFeiten"]["locaties"]
    }
    machine_readable = {
        a["number"]: a.get("machine_readable")
        for a in yaml_doc.get("articles") or []
    }
    voorstel_params = (voorstel or {}).get("parameters") or {}

    artikelen: list[dict[str, Any]] = []
    tellingen = {"getoetst": 0, "scenario": 0, "onthouding": 0, "engineFout": 0}
    uitkomsten: dict[str, int] = {"waar": 0, "onwaar": 0}

    for num in form_in_hit:
        mr = machine_readable.get(num)
        if not mr:
            artikelen.append(
                {
                    "artikel": num,
                    "status": "onthouding",
                    "reden": "geen_machine_readable_in_export",
                }
            )
            tellingen["onthouding"] += 1
            continue
        execution = mr.get("execution") or {}

        oplossingen: dict[str, dict[str, Any]] = {}
        onbekend: list[str] = []
        scenario_velden: list[str] = []
        for i in execution.get("input") or []:
            res = resolve_input(
                i["name"],
                gebiedsaanwijzingen=gebiedsaanwijzingen,
                voorstel_params=voorstel_params,
            )
            oplossingen[i["name"]] = res
            if res["bron"] == "onbekend":
                onbekend.append(i["name"])
            elif res["bron"] == "scenario":
                scenario_velden.append(i["name"])

        entry: dict[str, Any] = {
            "artikel": num,
            "inputs": [
                {"naam": naam, **oplossingen[naam]} for naam in sorted(oplossingen)
            ],
            "zones": [
                {"ref": ref, "noemer": noemer_by_ref.get(ref)}
                for ref in profielen[num]["locatieRefs"]
            ],
        }

        if onbekend:
            entry["status"] = "onthouding"
            entry["reden"] = "input_onbekend:" + ",".join(sorted(onbekend))
            artikelen.append(entry)
            tellingen["onthouding"] += 1
            continue

        feiten = {n: r["waarde"] for n, r in oplossingen.items()}

        if scenario_velden:
            velden = sorted(scenario_velden)
            runs = []
            fout = None
            for combo in itertools.product((False, True), repeat=len(velden)):
                probeer = dict(feiten)
                label = "&".join(
                    f"{veld}={'true' if val else 'false'}"
                    for veld, val in zip(velden, combo)
                )
                for veld, val in zip(velden, combo):
                    probeer[veld] = val
                outputs, err = _engine_outputs(execution, probeer)
                if err:
                    fout = err
                    break
                runs.append({"scenario": label, "inputs": probeer, "outputs": outputs})
            if fout:
                entry["status"] = "engineFout"
                entry["reden"] = fout
                tellingen["engineFout"] += 1
            else:
                entry["status"] = "scenario"
                entry["scenarioVelden"] = velden
                entry["scenarioContext"] = {
                    "tijdelijkDeelGeldtOpPunt": tijdelijk_deel_op_punt,
                    "toelichting": "Scenariovelden hangen aan het concrete voorstel "
                    "en zijn geen feiten; alle polariteitscombinaties zijn "
                    "doorgerekend, geen daarvan is een besluit.",
                }
                entry["runs"] = runs
                tellingen["scenario"] += 1
            artikelen.append(entry)
            continue

        outputs, err = _engine_outputs(execution, feiten)
        if err:
            entry["status"] = "engineFout"
            entry["reden"] = err
            tellingen["engineFout"] += 1
        else:
            entry["status"] = "getoetst"
            entry["inputsWaarden"] = feiten
            entry["outputs"] = outputs
            entry["trace"] = reference_engine.evaluate(execution, feiten)["trace"]
            tellingen["getoetst"] += 1
            for waarde in outputs.values():
                if waarde is True:
                    uitkomsten["waar"] += 1
                elif waarde is False:
                    uitkomsten["onwaar"] += 1
        artikelen.append(entry)

    resultaat: dict[str, Any] = {
        "contract": CONTRACT,
        "instrument": {
            "id": instrument_id,
            "label": instrument["label"],
            "cvdr": instrument["cvdr"],
        },
        "locatie": {"id": (locatie or {}).get("id")},
        "gegenereerdOp": gegenereerd_op,
        "feiten": {
            "bron": "tpod-index (geoFeiten): Presenteren-annotaties op de "
            "bevraagde geometrie",
            "tijdelijkDeelGeldtOpPunt": tijdelijk_deel_op_punt,
            "gebiedsaanwijzingenInHit": [
                g.get("naam") for g in gebiedsaanwijzingen
            ],
        },
        "tellingen": {
            **tellingen,
            "formalizedInHit": len(form_in_hit),
            "artikelen": len(artikelen),
        },
        "artikelen": artikelen,
    }
    if voorstel is not None:
        resultaat["voorstel"] = {
            "label": voorstel.get("label"),
            "parameters": voorstel.get("parameters") or {},
            "toelichting": voorstel.get("toelichting"),
            "scorecard": {
                "uitkomsten": uitkomsten,
                "toelichting": "waar = uitkomst van de machine_readable-output "
                "is True (toegestaan/houdbaar); onwaar = False. Bij 1-op-1 "
                "outputs is dat per artikel een ja/nee.",
            },
        }
    return resultaat


def bouw_sweep(
    *,
    instrument_id: str,
    instrument: dict[str, Any],
    locatie: dict[str, Any] | None,
    tpod_index: dict[str, Any],
    yaml_doc: dict[str, Any],
    gegenereerd_op: str,
    voorstel: dict[str, Any],
) -> dict[str, Any]:
    """Variant-sweep bovenop een voorstel: de mechanische verkenruimte (laag 3).

    ``voorstel["variaties"]`` is een lijst van partiële parameter-mappen die
    over de basisparameters worden gelegd. Per variant draait de volledige
    punt-toets; het rapport aggregeert scorecards en kantelpunten: welke
    artikelen omslaan tussen varianten (de gevoelige regels) en waar.
    Deterministisch en gelabeld — dit is verkenning, geen besluit (MC-6).
    """
    basis = dict(voorstel.get("parameters") or {})
    variaties = voorstel.get("variaties") or []
    varianten: list[dict[str, Any]] = []
    uitslagen_per_artikel: dict[str, list[bool]] = {}

    for i, variatie in enumerate(variaties):
        waarden = {**basis, **variatie}
        toets = build_toets(
            instrument_id=instrument_id,
            instrument=instrument,
            locatie=locatie,
            tpod_index=tpod_index,
            yaml_doc=yaml_doc,
            gegenereerd_op=gegenereerd_op,
            voorstel={
                "label": f"{voorstel.get('label')} — variatie {i + 1}",
                "parameters": waarden,
            },
        )
        afgewezen: list[str] = []
        for a in toets["artikelen"]:
            if a["status"] != "getoetst":
                continue
            valst = any(v is False for v in a["outputs"].values())
            uitslagen_per_artikel.setdefault(a["artikel"], []).append(not valst)
            if valst:
                afgewezen.append(a["artikel"])
        varianten.append(
            {
                "variant": i + 1,
                "waarden": variatie,
                "tellingen": toets["tellingen"],
                "uitkomsten": toets["voorstel"]["scorecard"]["uitkomsten"],
                "afgewezenArtikelen": afgewezen,
            }
        )

    kantel = [
        {
            "artikel": artikel,
            "aantalWissels": sum(
                1 for j in range(1, len(uitslagen))
                if uitslagen[j] != uitslagen[j - 1]
            ),
            "variaties": len(uitslagen),
        }
        for artikel, uitslagen in sorted(uitslagen_per_artikel.items())
        if len(set(uitslagen)) > 1
    ]
    return {
        "contract": SWEEP_CONTRACT,
        "instrument": {
            "id": instrument_id,
            "label": instrument["label"],
            "cvdr": instrument["cvdr"],
        },
        "locatie": {"id": (locatie or {}).get("id")},
        "gegenereerdOp": gegenereerd_op,
        "voorstel": {
            "label": voorstel.get("label"),
            "basisparameters": basis,
            "toelichting": voorstel.get("toelichting"),
        },
        "aantalVarianten": len(variaties),
        "kantelArtikelen": kantel,
        "varianten": varianten,
        "interpretatie": "Sweep is verkenning (notitie-laag 3): welke "
        "varianten van een voorstel zijn het proberen waard, en welke regels "
        "kantelen bij welke waarden. Geen variant is een besluit; de "
        "juristtoets blijft open (MC-6).",
    }
