"""Klein taakregister voor executor-tests: vier bindingen, drie bronnen.

De bron `pdok-nwb-wegen` + collectie `wegvakken` bestaat ook in
tests/fixtures.py (synthetische NWB-lijn binnen de test-AOI), zodat de
clip-op een echt resultaat heeft.
"""

TASKS = [
    {"id": "t.echo", "thema": "th", "onderdeel": "ond", "item": "echo", "prioriteit": "laag"},
    {"id": "t.clip", "thema": "th", "onderdeel": "ond", "item": "clip", "prioriteit": "hoog"},
    {"id": "t.man", "thema": "th", "onderdeel": "ond", "item": "manual", "prioriteit": "hoog"},
    {"id": "t.broken-op", "thema": "th", "onderdeel": "ond", "item": "broken", "prioriteit": "laag"},
]
BINDINGS = [
    {"lijstItemId": "t.echo", "status": "auto", "serviceRefs": [],
     "derivation": {"op": "echo_input", "params": {}}, "notes": []},
    {"lijstItemId": "t.clip", "status": "auto", "serviceRefs": ["pdok-nwb-wegen"],
     "derivation": {"op": "clip_layer", "params": {"collection": "wegvakken"}}},
    {"lijstItemId": "t.man", "status": "manual", "manualPointer": "bevoegde bron"},
    {"lijstItemId": "t.broken-op", "status": "auto", "serviceRefs": [],
     "derivation": {"op": "bestaat_niet", "params": {}}},
]
SOURCES = [{"id": "pdok-nwb-wegen", "title": "NWB wegvakken", "protocol": "ogc-api-features"}]


def build():
    from fundament.registers import TaskRegistry
    return TaskRegistry(TASKS, BINDINGS, SOURCES)
