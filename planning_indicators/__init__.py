"""Gedeelde indicatoren-datasect voor alle LDT-toolbox PoC's.

Vendored kopie van de *Urban Indicators Dataset: Drinking Water, Urban Heat,
and Housing Provision* (Cardenas-Leon, Nourian, Koeva & Pfeffer, ITC Twente),
release v1.2, CC BY-NC-SA 4.0 — zie README.md in deze map voor bron,
provenance en gebruik per PoC.

Gebruik vanuit een PoC (bestaande sys.path-bridge naar de repo-root):

    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

    from planning_indicators import indicators, papers_for_indicator, CITATION

Alle waarden komen rechtstreeks uit de vendored CSV's (geen netwerk, geen
mutatie); publiceer-artefacten dienen ``CITATION``/``DOI``/``LICENSE`` mee te
reten (de dataset is CC BY-NC-SA 4.0 — attribution vereist, share-alike).
"""

from .loader import (
    AUTHORS,
    CITATION,
    DATASET_DIR,
    DOI,
    FOREIGN_KEYS,
    KNOWN_STALE_FKS,
    LICENSE,
    LICENSE_URL,
    PKG_DIR,
    PRIMARY_KEYS,
    SECTORS,
    SOURCE_URL,
    TABLES,
    TITLE,
    UPSTREAM_COMMIT,
    VERSION,
    ZENODO_URL,
    as_int,
    indicator_papers,
    indicators,
    load_all,
    load_table,
    papers_for_indicator,
    search,
    strip_html,
    validate,
)

__all__ = [
    "AUTHORS",
    "CITATION",
    "DATASET_DIR",
    "DOI",
    "FOREIGN_KEYS",
    "KNOWN_STALE_FKS",
    "LICENSE",
    "LICENSE_URL",
    "PKG_DIR",
    "PRIMARY_KEYS",
    "SECTORS",
    "SOURCE_URL",
    "TABLES",
    "TITLE",
    "UPSTREAM_COMMIT",
    "VERSION",
    "ZENODO_URL",
    "as_int",
    "indicator_papers",
    "indicators",
    "load_all",
    "load_table",
    "papers_for_indicator",
    "search",
    "strip_html",
    "validate",
]
