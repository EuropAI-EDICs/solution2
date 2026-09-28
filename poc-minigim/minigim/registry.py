"""Laadt en indexeert de MiniGIM-registries (lijst, ILS, bindings, bronnen).

De registries onder registry/ zijn gegenereerd uit de gepinde Excel-artefacten
(zie tools/convert_minigim_xlsx.py) en zijn de norm voor de runner.
"""

from __future__ import annotations

import json
from pathlib import Path

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


class MiniGimRegistry:
    """Geïndexeerde view over lijst + bindings + bronnen + ILS."""

    def __init__(self) -> None:
        self.lijst = load_lijst()
        self.ils = load_ils()
        self.bindings = load_bindings()
        self.sources = load_sources()

        self.items = {i["id"]: i for i in self.lijst["items"]}
        self.bindings_by_id = {b["lijstItemId"]: b for b in self.bindings["bindings"]}
        self.sources_by_id = {s["id"]: s for s in self.sources["sources"]}

        self.ils_nodes = {n["id"]: n for n in self.ils["nodes"]}
        self._path_cache: dict[str, list[str]] = {}

        self._check_complete()

    # ------------------------------------------------------------------ #
    def _check_complete(self) -> None:
        """V2-voorwaarde: elk lijst-item exact één binding; elke binding een
        bekend item; elke serviceRef een geregistreerde bron."""
        missing = set(self.items) - set(self.bindings_by_id)
        extra = set(self.bindings_by_id) - set(self.items)
        if missing or extra:
            raise AssertionError(
                f"bindings/dekking inconsistent — missing={sorted(missing)} extra={sorted(extra)}"
            )
        for b in self.bindings["bindings"]:
            for ref in b.get("serviceRefs", []):
                if ref not in self.sources_by_id:
                    raise AssertionError(f"onbekende serviceRef {ref} in {b['lijstItemId']}")

    def item(self, item_id: str) -> dict:
        return self.items[item_id]

    def binding(self, item_id: str) -> dict:
        return self.bindings_by_id[item_id]

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
