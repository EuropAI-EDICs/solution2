"""STTR-import: officiële toepasbare regels (DMN) executioneerbaar naast de annotatie.

Ontleedt STTR-bestanden uit de RTR-cache (``dso_overlap.rtr``) of de officiële
voorbeeldbestanden (STTR 3.0.0) tot beslistabellen en projecteert die — waar
deterministisch mogelijk — op de vier operatoren van de reference-engine
(AND, EQUALS, LESS_THAN_OR_EQUAL, IF). Kader: docs/POC_STTR_IMTR_KANSEN.md
(kans 2, richting STTR → RegelRecht). Geen verzonnen mapping: wat niet in de
engine-subset past, heet expliciet niet-projecteerbaar met reden.
"""
from nldt.simulation.regelrecht.sttr.dmn import SttrParseFout, parse_sttr
from nldt.simulation.regelrecht.sttr.executie import (
    projecteer_decision,
    scenario_run,
)

CONTRACT = "sttr-index/v1"

__all__ = [
    "CONTRACT",
    "SttrParseFout",
    "parse_sttr",
    "projecteer_decision",
    "scenario_run",
]
