"""Laadt en indexeert de MiniGIM-registries (lijst, ILS, bindings, bronnen).

De registries onder registry/ zijn gegenereerd uit de gepinde Excel-artefacten
(zie tools/convert_minigim_xlsx.py) en zijn de norm voor de runner. De
taak-/bindings-/bronnen-mechaniek staat sinds M2 in fundament.registers;
dit bestand houdt de MiniGIM-specifieke delen (ILS-niveaus, pad-labels).
"""

from __future__ import annotations

import json
from pathlib import Path

from fundament.registers import TaskRegistry

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry"
DATA = ROOT / "data"


def load_lijst() -> dict:
    return json.loads((REGISTRY / "minigim-lijst.json").read_text(encoding="utf-8"))


def load_ils() -> dict:
    return json.loads((REGISTRY / "minigim-ils.json").read_text(encoding="utf-8"))


def load_bindings() -> dict:
    return json.loads((REGISTRY / "lijst-bindings.json").read_text(encoding="utf-8"))


def load_sources() -> dict:
    return json.loads((DATA / "sources.json").read_text(encoding="utf-8"))


class MiniGimRegistry(TaskRegistry):
    """Geïndexeerde view over lijst + bindings + bronnen + ILS."""

    def __init__(self) -> None:
        self.lijst = load_lijst()
        self.ils = load_ils()
        self.bindings = load_bindings()
        self.sources = load_sources()
        super().__init__(tasks=self.lijst["items"],
                         bindings=self.bindings["bindings"],
                         sources=self.sources["sources"])
        self.ils_nodes = {n["id"]: n for n in self.ils["nodes"]}
        self._path_cache: dict[str, list[str]] = {}

    def tasks(self) -> list[dict]:
        return self.lijst["items"]

    # ------------------------------------------------------------------ #
    def ils_path_labels(self, node_id: str) -> list[str]:
        """Labels van wortel naar knoop (Niveau 0 → …)."""
        if node_id in self._path_cache:
            return self._path_cache[node_id]
        labels: list[str] = []
        nid: str | None = node_id
        while nid is not None:
            node = self.ils_nodes[nid]
            labels.append(node["label"])
            nid = node["parent"]
        labels.reverse()
        self._path_cache[node_id] = labels
        return labels

    def ils_ifc(self, node_id: str) -> str | None:
        """IfcExportAs van de knoop of de dichtstbijzijnde voorouder."""
        nid: str | None = node_id
        while nid is not None:
            node = self.ils_nodes[nid]
            if node.get("ifcExportAs"):
                return node["ifcExportAs"]
            nid = node["parent"]
        return None
