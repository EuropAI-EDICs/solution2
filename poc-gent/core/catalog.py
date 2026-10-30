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
    return json.loads(path.read_text(encoding="utf-8"))


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
        if check["input"] not in slots:
            raise PackageError(f"gisCheck '{check['id']}': onbekende input-slot '{check['input']}'")
        outputs.add(check["output"])
    services = manifest.get("services", {})
    if not services:
        raise PackageError("manifest.services is leeg")
    for rule in tables.get("rules", []):
        for sv in rule.get("then", {}).get("transactions", []) + rule.get("then", {}).get("info", []):
            if sv not in services:
                raise PackageError(f"regel '{rule.get('id')}': onbekende dienst '{sv}'")
        for key in rule.get("when", {}):
            if key not in slots and key not in outputs:
                raise PackageError(f"regel '{rule.get('id')}': onbekende when-sleutel '{key}'")


def load_package(poc_root: Path, package_id: str) -> Package:
    pkg_dir = poc_root / "packages" / package_id
    manifest = _read_json(pkg_dir / "manifest.json")
    tables = _read_json(pkg_dir / manifest["decisionTables"])
    golden_path = pkg_dir / manifest["golden"]
    if not golden_path.is_file():
        raise PackageError(f"golden-set ontbreekt: {golden_path}")
    golden = [json.loads(regel) for regel in golden_path.read_text(encoding="utf-8").splitlines() if regel.strip()]
    _validate(manifest, tables)
    return Package(manifest=manifest, tables=tables, golden=golden)
