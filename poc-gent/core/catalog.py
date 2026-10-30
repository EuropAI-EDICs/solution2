"""Pakketlader: laadt en valideert een levensgebeurtenis-pakket (manifest +
beslistabellen + golden set). Configuratie is data; de lader dwingt de
contractvorm af (FR-22, ontwerp §4)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class PackageError(Exception):
    """Pakket is onvolledig of houdt zich niet aan het contract."""


@dataclass(frozen=True)
class Package:
    manifest: dict
    tables: dict
    golden: list


def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise PackageError(f"bestand ontbreekt: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise PackageError(f"ongeldige JSON in {path}: {err}") from err


def _validate(manifest: dict, tables: dict) -> None:
    for key in ("packageId", "version", "status", "lifeEventCode"):
        if not manifest.get(key):
            raise PackageError(f"manifest: verplicht veld '{key}' ontbreekt")
    for key in ("intro", "scope", "aiToelichting", "weigering", "escalatie"):
        if key not in manifest.get("texts", {}):
            raise PackageError(f"manifest.texts: '{key}' ontbreekt")
    slots = manifest.get("contextSchema", {}).get("slots", {})
    if not slots:
        raise PackageError("manifest.contextSchema.slots is leeg")
    for slot, spec in slots.items():
        if "type" not in spec or "required" not in spec:
            raise PackageError(f"slot '{slot}' mist type/required")
        if spec.get("authenticSource") is None and "vraag" not in spec:
            raise PackageError(f"slot '{slot}' mist vraag-tekst")
    outputs = set()
    for check in manifest.get("gisChecks", []):
        for field_name in ("id", "layer", "input", "output"):
            if field_name not in check:
                raise PackageError(f"gisCheck mist veld '{field_name}': {check}")
        if check["input"] != "address":
            raise PackageError(f"gisCheck '{check['id']}': F1 ondersteunt alleen input 'address' (gekregen: '{check['input']}')")
        if check["input"] not in slots:
            raise PackageError(f"gisCheck '{check['id']}': onbekende input-slot '{check['input']}'")
        outputs.add(check["output"])
    services = manifest.get("services", {})
    if not services:
        raise PackageError("manifest.services is leeg")
    bronnen = manifest.get("authenticSources", [])
    gedeclareerd = {b.get("slot") for b in bronnen}
    if len(bronnen) != len(gedeclareerd):
        raise PackageError("authenticSources bevat meerdere entries voor hetzelfde slot")
    authentieke_slots = {s for s, spec in slots.items() if spec.get("authenticSource")}
    for bron in bronnen:
        if not bron.get("purpose"):
            raise PackageError(f"authenticSource '{bron.get('slot')}' mist een niet-lege purpose")
        if slots.get(bron.get("slot", ""), {}).get("authenticSource") != bron.get("source"):
            raise PackageError(f"authenticSource '{bron.get('slot')}' wijkt af van het slot-authenticSource")
    bronnen_zonder_dubbel = {b.get("source") for b in bronnen}
    if len(bronnen_zonder_dubbel) != len(bronnen):
        raise PackageError("authenticSources bevat meerdere entries voor dezelfde bron (één doelbinding per bron)")
    if gedeclareerd != authentieke_slots:
        raise PackageError(f"authenticSources dekken de authentieke slots niet: {gedeclareerd} ≠ {authentieke_slots}")
    for service_id, service in services.items():
        if service.get("type") == "inzending":
            if not service.get("formulier"):
                raise PackageError(f"dienst '{service_id}': inzending zonder formulier")
        if "vereistAuth" not in service or not isinstance(service.get("vereistAuth"), bool):
            raise PackageError(f"dienst '{service_id}': vereistAuth moet een bool zijn")
        if service.get("minLoA") is not None and service["minLoA"] not in ("low", "substantial", "high"):
            raise PackageError(f"dienst '{service_id}': ongeldig minLoA '{service['minLoA']}' (low|substantial|high)")
        if service.get("type") == "inzending" and service.get("vereistAuth") is not True:
            raise PackageError(f"dienst '{service_id}': inzending vereist vereistAuth true")
        if service.get("type") == "inzending" and not service.get("documenten"):
            raise PackageError(f"dienst '{service_id}': inzending zonder documenten-eisen")
        for regel in service.get("formulier", []):
            if not regel.get("veld"):
                raise PackageError(f"dienst '{service_id}': formulierregel mist een niet-lege 'veld'")
            referentie = regel.get("bron", "")
            if referentie.startswith("slot:"):
                geldig = referentie[5:] in slots
            else:
                tool, _, pad = referentie.partition(".")
                geldig = bool(pad) and tool in {b["source"] for b in bronnen}
            if not geldig:
                raise PackageError(f"dienst '{service_id}': onbekende of onvolledige formulierbron '{referentie}'")
        velden = {regel["veld"] for regel in service.get("formulier", [])}
        for check in service.get("validaties", []):
            for veld in check.get("wanneer", {}):
                if veld not in velden:
                    raise PackageError(f"dienst '{service_id}': validatie '{check.get('id')}' verwijst naar onbekend formulierveld '{veld}'")
            if check.get("ernst") not in ("blokkade", "waarschuwing"):
                raise PackageError(f"dienst '{service_id}': validatie '{check.get('id')}' heeft ongeldige ernst")
    rules = tables.get("rules", [])
    if not rules:
        raise PackageError("beslistabellen: 'rules' is leeg")
    for rule in rules:
        for field_name in ("id", "when", "then", "uitleg", "legalBasis"):
            if not rule.get(field_name):
                raise PackageError(f"regel mist veld '{field_name}' of is leeg: {rule.get('id', '?')}")
    for rule in rules:
        for sv in rule.get("then", {}).get("transactions", []) + rule.get("then", {}).get("info", []):
            if sv not in services:
                raise PackageError(f"regel '{rule.get('id')}': onbekende dienst '{sv}'")
        for key in rule.get("when", {}):
            if key not in slots and key not in outputs:
                raise PackageError(f"regel '{rule.get('id')}': onbekende when-sleutel '{key}'")


def load_package(poc_root: Path, package_id: str) -> Package:
    pkg_dir = poc_root / "packages" / package_id
    manifest = _read_json(pkg_dir / "manifest.json")
    for pointer in ("decisionTables", "golden"):
        if not manifest.get(pointer):
            raise PackageError(f"manifest: verplicht veld '{pointer}' ontbreekt")
    tables = _read_json(pkg_dir / manifest["decisionTables"])
    golden_path = pkg_dir / manifest["golden"]
    if not golden_path.is_file():
        raise PackageError(f"golden-set ontbreekt: {golden_path}")
    golden = []
    for regel in [r for r in golden_path.read_text(encoding="utf-8").splitlines() if r.strip()]:
        try:
            golden.append(json.loads(regel))
        except json.JSONDecodeError as err:
            raise PackageError(f"ongeldige JSON-regel in {golden_path}: {err}") from err
    for rij in golden:
        for field_name in ("scenarioId", "persona", "expect"):
            if field_name not in rij:
                raise PackageError(f"golden-regel mist veld '{field_name}': {rij}")
        for field_name in ("outcome", "transactions", "info"):
            if field_name not in rij["expect"]:
                raise PackageError(f"golden-verwachting mist veld '{field_name}': {rij.get('scenarioId', '?')}")
    _validate(manifest, tables)
    return Package(manifest=manifest, tables=tables, golden=golden)
