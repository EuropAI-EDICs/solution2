"""PoC-5 MiniGIM: gebiedscheck volgens de MiniGIM-methodiek (minigim.nl).

Deterministische, cache-first runner die de Omgevingsanalyse Lijst (v0.91)
voor een plangrens invult uit sleutelloze open bronnen en daaruit een ILS
(Input Grex) draft-gebiedsindeling afleidt. Geen LLM in de beslislijn.
"""

import sys
from pathlib import Path

_FUNDAMENT = Path(__file__).resolve().parents[2] / "poc-fundament"
if _FUNDAMENT.is_dir() and str(_FUNDAMENT) not in sys.path:
    # append, niet prepend: poc-fundament heeft unieke top-level namen
    # (fundament/), maar prepend zou in discovery-modus `tests`/`fixtures`
    # naar poc-fundament/tests laten verwijzen in plaats van dit pakket.
    sys.path.append(str(_FUNDAMENT))
