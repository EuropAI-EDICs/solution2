"""TaskRegistry: geïndexeerde view over taken, bindings en bronnen.

Generalisatie van de checklist-relevantie-helft van poc-minigim
MiniGimRegistry (die hier subclass van wordt en het ILS-deel zelf houdt).
De binding-sleutel heet historisch `lijstItemId` (MiniGIM Omgevingsanalyse
Lijst v0.91); de gepinde registries worden niet hernoemd.
"""

from __future__ import annotations


class TaskRegistry:
    """V2-voorwaarde: elke taak exact één binding; elke serviceRef geregistreerd."""

    def __init__(self, tasks: list, bindings: list, sources: list) -> None:
        self._tasks = list(tasks)
        self.items = {t["id"]: t for t in self._tasks}
        self.bindings_by_id = {b["lijstItemId"]: b for b in bindings}
        self.sources_by_id = {s["id"]: s for s in sources}
        self.check_complete()

    def tasks(self) -> list[dict]:
        return self._tasks

    def item(self, task_id: str) -> dict:
        return self.items[task_id]

    def binding(self, task_id: str) -> dict:
        return self.bindings_by_id[task_id]

    def check_complete(self) -> None:
        missing = set(self.items) - set(self.bindings_by_id)
        extra = set(self.bindings_by_id) - set(self.items)
        if missing or extra:
            raise AssertionError(
                f"bindings/dekking inconsistent — missing={sorted(missing)} extra={sorted(extra)}"
            )
        for b in self.bindings_by_id.values():
            for ref in b.get("serviceRefs", []):
                if ref not in self.sources_by_id:
                    raise AssertionError(
                        f"onbekende serviceRef {ref} in {b['lijstItemId']}"
                    )
