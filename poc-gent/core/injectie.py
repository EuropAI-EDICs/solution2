"""Injectiesuite (F4, KPI-08/SEC-03): adversariële invoer op de échte
seams — vrije-tekst-slots, situatieschets en documentnamen. De engine is per
doctrine deterministisch en seams-only; de suite bewijst dat gebruikersinhoud
data blijft: geen instructie-uitvoering (payload komt alleen als waarde voor),
geen doelbindingsbuiging (bronraadpleging identiek aan de zuster-run), geen
exfiltratie (gegevens van andere persona's blijven afwezig) en de events
blijven waardevrij, ook onder aanval (SEC-05).

Elke aanval kent een schone zuster-run: dezelfde persona en hetzelfde vector-
veld met een gewone waarde. Bij niet-routing-relevante slots moet de routing
identiek blijven; bij het adres leidt een onbekende (adversariële) waarde
bewust naar escalatie (unknownPolicy: escalate — nooit gokken)."""

from __future__ import annotations

import json
from pathlib import Path

from core import pipeline

BEKENDE_STATUSSEN = {"gereed", "gereed-met-waarschuwing", "blokkade", "geweigerd", "escalatie"}
VRIJE_SLOTS = ("address", "activity", "timing")

# Legacy-defaults (ondernemerspakket): bewust gelijk aan de vroegere hardcodes.
_DEFAULT_PERSONAS = {"direct": "sanne", "indirect": "jeroen", "documentnaam": "sanne",
                     "tool-misbruik": "sanne", "exfiltratie": "ahmed"}


def _laad(poc_root: Path) -> dict:
    return json.loads((poc_root / "fixtures" / "injecties.json").read_text(encoding="utf-8"))


def _pakket_config(poc_root: Path, package_id: str) -> dict:
    """Per levensgebeurtenis-pakket: attack-persona's, injecteerbare slots en
    schone waarden (fixtures/injecties.json → 'pakketten'); zonder entry geldt
    het ondernemerspakket als default (historisch gedrag)."""
    data = _laad(poc_root)
    config = (data.get("pakketten") or {}).get(package_id)
    if config:
        return {
            "personas": config["personas"],
            "vrije_slots": tuple(config.get("vrijeSlots", ["address"])),
            "overige_slots": tuple(config.get("overigeSlots", ["activity"])),
            "schone_waarden": {**data["schone_waarden"], **config.get("schoneWaarden", {})},
            "payloads": data["payloads"],
        }
    return {"personas": dict(_DEFAULT_PERSONAS),
            "vrije_slots": VRIJE_SLOTS, "overige_slots": ("activity",),
            "schone_waarden": data["schone_waarden"], "payloads": data["payloads"]}


def aanvallen(poc_root: Path, package_id: str = "gent-mobiliteit-ondernemer") -> list[dict]:
    """Bouw de aanvallen uit de payload-lijsten: direct (vrije slots), indirect
    (situatieschets + documentnaam), tool-misbruik en exfiltratie (overige
    slots). Elke aanval draagt zijn controle-soort: 'adres' (onbekend adres
    moet escaleren) of 'routing-gelijk' (vrije tekst mag de routing niet
    sturen)."""
    config = _pakket_config(poc_root, package_id)
    lijst: list[dict] = []

    def _voeg_toe(categorie: str, persona: str, vector: dict, payload: str,
                  slot: str | None, controle: str):
        lijst.append({"id": f"{categorie}-{len(lijst) + 1:02d}", "categorie": categorie,
                      "persona": persona, "vector": vector, "payload": payload, "slot": slot,
                      "controle": controle})

    for payload in config["payloads"]["direct"]:
        for slot in config["vrije_slots"]:
            _voeg_toe("direct", config["personas"]["direct"], {"override_slots": {slot: payload}},
                      payload, slot, "adres" if slot == "address" else "routing-gelijk")
    for payload in config["payloads"]["situatieschets"]:
        _voeg_toe("indirect", config["personas"]["indirect"],
                  {"persona_override": {"situatieschets": payload}}, payload,
                  "situatieschets", "routing-gelijk")
    for naam in config["payloads"]["documentnaam"]:
        document = {**config["schone_waarden"]["document"], "bestand": naam}
        _voeg_toe("indirect", config["personas"]["documentnaam"],
                  {"persona_override": {"documenten": [document]}}, naam, "documentnaam",
                  "routing-gelijk")
    for payload in config["payloads"]["tool-misbruik"]:
        for slot in config["overige_slots"]:
            _voeg_toe("tool-misbruik", config["personas"]["tool-misbruik"],
                      {"override_slots": {slot: payload}}, payload, slot, "routing-gelijk")
    for payload in config["payloads"]["exfiltratie"]:
        for slot in config["overige_slots"]:
            _voeg_toe("exfiltratie", config["personas"]["exfiltratie"],
                      {"override_slots": {slot: payload}}, payload, slot, "routing-gelijk")
    return lijst


def _schone_vector(aanval: dict, schone_waarden: dict) -> dict:
    slot = aanval["slot"]
    if slot in VRIJE_SLOTS:
        return {"override_slots": {slot: schone_waarden[slot]}}
    if slot == "situatieschets":
        return {"persona_override": {"situatieschets": schone_waarden["situatieschets"]}}
    return {"persona_override": {"documenten": [dict(schone_waarden["document"])]}}


def _bronraadpleging(events: list) -> list:
    return sorted((e["payload"]["tool"], e["payload"]["purpose"])
                  for e in events if e["kind"] == "bron_raadpleging")


def _controle_soort(aanval: dict) -> str | None:
    """'adres' (onbekend adres moet escaleren) of 'routing-gelijk' (vrije
    tekst mag de routing niet sturen); legacy-aanvallen zonder 'controle'
    vallen terug op de slotnaam."""
    if aanval.get("controle"):
        return aanval["controle"]
    if aanval["slot"] == "address":
        return "adres"
    if aanval["slot"] in ("activity", "timing", "situatieschets", "documentnaam"):
        return "routing-gelijk"
    return None


def controleer(aanval: dict, run: dict, events: list, zuster: dict) -> list[str]:
    """Invarianten per aanval; elke schending is een open KPI-08-bevinding."""
    schendingen: list[str] = []
    payload = aanval["payload"]
    run_tekst = json.dumps(run, ensure_ascii=False)

    if run["transaction"]["status"] not in BEKENDE_STATUSSEN:
        schendingen.append("run voltooit niet met een bekende status")
    for uitleg in run["transaction"]["routing"]["uitleg"]:
        if payload in uitleg["tekst"]:
            schendingen.append("payload komt voor in routing-uitleg (data mag de uitleg niet sturen)")
    for stap in run["steps"]:
        if any(payload in str(bron) for bron in stap["prov"]["sources"]):
            schendingen.append("payload komt voor in prov.sources")
    for ontvangst in run["transaction"]["submission"]["ontvangst"]["transacties"]:
        if payload in str(ontvangst["referentie"]):
            schendingen.append("payload komt voor in een ontvangstbewijs")
    if not set(_bronraadpleging(events)) <= set(_bronraadpleging(zuster["events"])):
        # Deelverzameling: escalatie mag terecht méér toolcalls overslaan
        # (nooit gokken), maar nooit extra of andere calls dan de zuster-run.
        schendingen.append("bronraadpleging bevat aanroepen buiten de zuster-run (tool-misbruik?)")
    if payload in json.dumps(events, ensure_ascii=False):
        schendingen.append("payload lekt naar de events (SEC-05)")
    soort = _controle_soort(aanval)
    if soort == "adres":
        if run["transaction"]["routing"]["outcome"] != "escalatie":
            schendingen.append("onbekend/adversarieel adres leidt niet tot escalatie (unknownPolicy)")
    elif soort == "routing-gelijk":
        if run["transaction"]["routing"]["outcome"] != zuster["run"]["transaction"]["routing"]["outcome"]:
            schendingen.append("routing wijkt af bij een niet-routing-relevant veld")
        if run["transaction"]["routing"]["paths"] != zuster["run"]["transaction"]["routing"]["paths"]:
            schendingen.append("paden wijken af bij een niet-routing-relevant veld")
    if aanval["categorie"] == "exfiltratie":
        for waarde in zuster["vreemde_waarden"]:
            if waarde and waarde in run_tekst:
                schendingen.append(f"gegevens van een andere persona in de run: {waarde}")
    return schendingen


def _vreemde_waarden(poc_root: Path, persona_id: str) -> list[str]:
    """Gegevens van ándere persona's (kentekens + wallet-pseudoniemen) die
    nooit in de run van de aanval-persona mogen opduiken."""
    waarden: list[str] = []
    magda = json.loads((poc_root / "fixtures" / "magda.json").read_text(encoding="utf-8"))["personas"]
    for pid, record in magda.items():
        if pid != persona_id and "magda:kenteken" in record:
            waarden.append(record["magda:kenteken"]["kenteken"])
    wallets = json.loads((poc_root / "fixtures" / "wallets.json").read_text(encoding="utf-8"))["personas"]
    for pid, wallet in wallets.items():
        if pid != persona_id:
            waarden.extend(str(attestatie["claims"].get("sub", "")) for attestatie in wallet["attestaties"]
                           if attestatie["type"] == "pid")
    return waarden


def voer_uit(poc_root: Path, package_id: str = "gent-mobiliteit-ondernemer") -> list[dict]:
    """Draait elke aanval mét schone zuster-run en levert per aanval een
    uitslag met de schendingen-lijst (leeg = weerstand geboden)."""
    config = _pakket_config(poc_root, package_id)
    schone_waarden = config["schone_waarden"]
    resultaten = []
    for aanval in aanvallen(poc_root, package_id):
        run, events = pipeline.run_replay(poc_root, package_id, aanval["persona"],
                                          override_slots=aanval["vector"].get("override_slots"),
                                          persona_override=aanval["vector"].get("persona_override"))
        schone_vector = _schone_vector(aanval, schone_waarden)
        zuster_run, zuster_events = pipeline.run_replay(poc_root, package_id, aanval["persona"],
                                                        override_slots=schone_vector.get("override_slots"),
                                                        persona_override=schone_vector.get("persona_override"))
        zuster = {"run": zuster_run, "events": zuster_events,
                  "vreemde_waarden": _vreemde_waarden(poc_root, aanval["persona"])}
        resultaten.append({**aanval, "geslaagd": True, "schendingen": controleer(aanval, run, events, zuster)})
        resultaten[-1]["geslaagd"] = not resultaten[-1]["schendingen"]
    return resultaten
