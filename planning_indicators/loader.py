"""Loader voor de gedeelde DigitalPlanning_Indicators-datasect.

Bron: https://github.com/ivan-cardenas/DigitalPlanning_Indicators (release
v1.2, upstream-commit b81ebfad3c3a3fa6f90ec44cfb95455cc90ba5fa, 2025-12-04),
vendored onder ``planning_indicators/dataset/CSV/`` — zie package-README en
``docs/superpowers/specs/2026-10-14-planning-indicators-design.md``.

Puur stdlib (csv/json/html.parser), offline-first, geen mutatie van de data:
de CSV's zijn byte-identiek aan upstream; alle quirk-afhandeling gebeurt in
deze loader. Bekende upstream-quirks:

- FK-kolommen zijn float-geformatteerd ("12.0") — ``as_int`` coërceert.
- ``Indicators.csv`` eindigt op een komma → spookkolom (csv-restkey) die
  hier wordt verworpen.
- ``Paper.csv``-titels bevatten HTML → ``strip_html``-helper.
- ``schema.json`` (verbatim vendored) dokumenteert het relationele model,
  maar de kolomnamen/paden kloppen niet 1-op-1 met de echte CSV-headers
  (en de ``research_paper.country_id``-FK bestaat niet in de CSV); de
  relationele regels hieronder reflecteren de werkelijke headers.
"""

from __future__ import annotations

import csv
import json
from html.parser import HTMLParser
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
DATASET_DIR = PKG_DIR / "dataset" / "CSV"

SOURCE_URL = "https://github.com/ivan-cardenas/DigitalPlanning_Indicators"
ZENODO_URL = "https://doi.org/10.5281/zenodo.17464468"
DOI = "10.5281/zenodo.17464468"
UPSTREAM_COMMIT = "b81ebfad3c3a3fa6f90ec44cfb95455cc90ba5fa"
VERSION = "1.2"
LICENSE = "CC-BY-NC-SA-4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by-nc-sa/4.0/"
AUTHORS = ("Ivan Cardenas-Leon", "Pirouz Nourian", "Mila Koeva", "Karin Pfeffer")
TITLE = "Urban Indicators Dataset: Drinking Water, Urban Heat, and Housing Provision"
CITATION = (
    f"Cardenas-Leon, I.; Nourian, P.; Koeva, M.; Pfeffer, K. ({VERSION}): "
    f"{TITLE}. Dataset. {DOI} — {LICENSE}."
)

# Logische tabelnaam → bestandsnaam zoals vendored. De namen volgen de
# upstream-schema-tabelrollen, niet de (willekeurig-gecapitaliseerde)
# bestandsnamen; ``schema.json``-paden zijn case-anders (upstream-quirk).
TABLES = {
    "indicators": "Indicators.csv",
    "main_table": "MainTable.csv",
    "paper": "Paper.csv",
    "objective": "Objective.csv",
    "topic": "Topic.csv",
    "planning_sector": "PlanningSector.csv",
    "system_parts": "System_Parts.csv",
    "countries": "Countries.csv",
    "region": "Region.csv",
    "income_type": "IncomeType.csv",
}

# Primary key per logische tabel (echte CSV-header).
PRIMARY_KEYS = {name: "ID" for name in TABLES}

# Fremdsleutel-relaties die in de CSV's daadwerkelijk bestaan:
# (tabel, kolom) → (referentietabel, referentiekolom).
FOREIGN_KEYS = {
    ("main_table", "IndicatorName"): ("indicators", "ID"),
    ("main_table", "Lookup Paper"): ("paper", "ID"),
    ("indicators", "Objective"): ("objective", "ID"),
    ("indicators", "System Part"): ("system_parts", "ID"),
    ("objective", "Topic"): ("topic", "ID"),
    ("topic", "Sector"): ("planning_sector", "ID"),
    ("countries", "Region_ID"): ("region", "ID"),
    ("countries", "IncomeType_ID"): ("income_type", "ID"),
}

# Upstream-schema noemt deze FK, maar de CSV-kolom bestaat niet (Paper.csv
# heeft ``Country`` als naam, geen id) — geregistreerd, niet afgedwongen.
KNOWN_STALE_FKS = (("paper", "country_id", "countries", "id"),)

SECTORS = {"water": 1, "heat": 2, "housing": 3}


def as_int(value):
    """Int-coercie die upstreams float-geformatteerde FK's ("12.0") aankan."""
    if value is None or value == "":
        return None
    return int(float(value))


def strip_html(text):
    """Verwijder HTML-opmaak (upstream Paper-titels) en collapse witruimte."""
    if not text:
        return text

    class _Collector(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.parts = []

        def handle_data(self, data):
            self.parts.append(data)

    collector = _Collector()
    collector.feed(text)
    collector.close()
    return " ".join("".join(collector.parts).split())


def load_table(name):
    """Laad één tabel als lijst van dict-rijen (waarden verbatim als str).

    De spookkolom uit upstream trailende komma's (csv-restkey ``None``)
    wordt verworpen; lege trailende velden worden gestript.
    """
    if name not in TABLES:
        raise KeyError(f"onbekende tabel {name!r}; kies uit {sorted(TABLES)}")
    with open(DATASET_DIR / TABLES[name], newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        row.pop(None, None)
        for key, value in list(row.items()):
            if isinstance(value, str) and value == "":
                row[key] = None
    return rows


def load_all():
    """Laad alle tien tabellen; mapping logische naam → rijen."""
    return {name: load_table(name) for name in TABLES}


def _index(rows):
    return {as_int(row["ID"]): row for row in rows}


def indicators():
    """Denormalized view: 280 indicatoren met objective/topic/sector/system-part
    als leesbare namen (naast de FK's, als int)."""
    tables = load_all()
    system_parts = _index(tables["system_parts"])
    objectives = _index(tables["objective"])
    topics = _index(tables["topic"])
    sectors = _index(tables["planning_sector"])

    joined = []
    for row in tables["indicators"]:
        system_part_id = as_int(row["System Part"])
        objective_id = as_int(row["Objective"])
        topic_id = as_int(objectives[objective_id]["Topic"]) if objective_id in objectives else None
        sector_id = as_int(topics[topic_id]["Sector"]) if topic_id in topics else None
        joined.append(
            {
                "id": as_int(row["ID"]),
                "name": row["Indicator"],
                "definition": row["Definition"],
                "units": row["Units"],
                "calculation": row["Calculation"],
                "system_part_id": system_part_id,
                "system_part": system_parts[system_part_id]["System Part"] if system_part_id in system_parts else None,
                "objective_id": objective_id,
                "objective": objectives[objective_id]["Objective"] if objective_id in objectives else None,
                "topic_id": topic_id,
                "topic": topics[topic_id]["IndicatorTopic"] if topic_id in topics else None,
                "sector_id": sector_id,
                "sector": sectors[sector_id]["Sector"] if sector_id in sectors else None,
                "comment": row["Comment"],
            }
        )
    return joined


def papers_for_indicator(indicator_id):
    """Bronpublicaties (via main_table) voor één indicator-id."""
    tables = load_all()
    papers = _index(tables["paper"])
    out = []
    for link in tables["main_table"]:
        if as_int(link["IndicatorName"]) != indicator_id:
            continue
        paper = papers.get(as_int(link["Lookup Paper"]))
        if paper is None:
            continue
        out.append(
            {
                "id": as_int(paper["ID"]),
                "zotero_id": paper["ZoteroID"],
                "title": strip_html(paper["Title"]),
                "year": as_int(paper["Year"]),
                "country": paper["Country"],
            }
        )
    return out


def indicator_papers():
    """Volledige indicator↔paper-join: lijst van
    ``{"indicator_id", "paper_id"}`` (1 rij per main_table-koppel)."""
    return [
        {
            "indicator_id": as_int(link["IndicatorName"]),
            "paper_id": as_int(link["Lookup Paper"]),
        }
        for link in load_table("main_table")
    ]


def search(query, sector=None):
    """Case-insensitive substring over indicatornaam+definitie; optioneel
    sector-filter met de SECTORS-sleutels (``water|heat|housing``)."""
    needle = query.lower()
    sector_id = SECTORS.get(sector) if sector else None
    return [
        ind
        for ind in indicators()
        if (sector_id is None or ind["sector_id"] == sector_id)
        and (needle in (ind["name"] or "").lower() or needle in (ind["definition"] or "").lower())
    ]


def validate():
    """Integriteitschecks op de vendored CSV's; lege lijst = gezond.

    Controleert: kolom-dekking tegen schema.json (header-normaal), PK-
    uniekheid per tabel en FK-integriteit volgens FOREIGN_KEYS. Boven-op
    schema.json gebruik dit de expliciete relatiekaart hierboven, omdat de
    upstream-schema-kolomnamen niet 1-op-1 met de CSV-headers matchen.
    """
    problems = []
    tables = load_all()

    def norm(header):
        # Header-normalisatie: upstream wijkt alleen af in case/underscores/
        # spaties; alfnumeriek-normaliseren maakt de vergelijking exact.
        return "".join(ch for ch in header.lower() if ch.isalnum())

    schema = json.loads((PKG_DIR / "schema.json").read_text(encoding="utf-8"))
    schema_tables = schema.get("tables", {})
    for name, rows in tables.items():
        if not rows:
            problems.append(f"{name}: lege tabel")
            continue
        headers = set(rows[0].keys())
        pk = PRIMARY_KEYS[name]
        if pk not in headers:
            problems.append(f"{name}: pk-kolom {pk!r} ontbreekt")
            continue
        ids = [as_int(row[pk]) for row in rows]
        duplicates = len(ids) - len(set(ids))
        if duplicates:
            problems.append(f"{name}: {duplicates} dubbele pk-waarden")
        if None in ids:
            problems.append(f"{name}: lege pk-waarden")

    schema_by_path = {
        norm(spec.get("path", "")): k for k, spec in schema_tables.items() if spec.get("path")
    }
    for name, filename in TABLES.items():
        key = schema_by_path.get(norm(f"dataset/CSV/{filename}"))
        if key is None:
            problems.append(f"{name}: geen schema-entry voor {filename}")
            continue
        declared = set(schema_tables[key].get("columns", {}).keys())
        actual = set(tables[name][0].keys()) if tables[name] else set()
        actual_norm = {norm(h) for h in actual}
        missing = {c for c in declared if norm(c) not in actual_norm}
        if missing:
            problems.append(f"{name}: schema-kolommen zonder CSV-header: {sorted(missing)}")

    for (table, column), (ref_table, ref_column) in FOREIGN_KEYS.items():
        ref_ids = {as_int(row[ref_column]) for row in tables[ref_table]}
        ref_ids.discard(None)
        for row in tables[table]:
            value = as_int(row.get(column))
            if value is not None and value not in ref_ids:
                problems.append(
                    f"{table}.{column}={value!r} verwijst niet naar {ref_table}.{ref_column}"
                )
                break

    return problems
