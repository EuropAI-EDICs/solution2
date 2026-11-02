"""TimingChecks (GT-EVT-01): datum-slot → aanlooptijd-klasse t.o.v. een vaste
referentiedatum uit het manifest. Deterministisch (geen klokkijken in de
replay); herkomst per uitkomst (DATA-01)."""

from __future__ import annotations

from datetime import date


def _parse_datum(raw: str) -> date | None:
    raw = raw.strip()
    for patroon in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return date.fromisoformat(date.strptime(raw, patroon).isoformat())
        except ValueError:
            continue
    return None


def klasse_voor(dagen: int, klassen: list[dict]) -> str:
    """Eerste klas waarvan maxDagen de aanlooptijd dekt; de laatste klas is
    het vangnet zonder maxDagen."""
    for klas in klassen:
        if klas.get("maxDagen") is not None and dagen <= int(klas["maxDagen"]):
            return klas["naam"]
    return klassen[-1]["naam"]


def apply_checks(manifest: dict, context: dict, herkomst: dict, poc_root,
                 suffix: str = "") -> None:
    """Voer alle timingChecks uit op hun input-slot: dagen tot de datum t.o.v.
    de manifest-referentie → klasse; verleden en onleesbare datums krijgen
    eigen waarden zodat beslistabellen erop kunnen matchen."""
    for check in manifest.get("timingChecks", []):
        raw = context.get(check["input"])
        if raw is None:
            continue
        referentie = date.fromisoformat(check["referentie"])
        datum = _parse_datum(str(raw))
        if datum is None:
            waarde = "onbekende-datum"
        else:
            dagen = (datum - referentie).days
            waarde = "verleden" if dagen < 0 else klasse_voor(dagen, check["klassen"])
        context[check["output"]] = waarde
        herkomst[check["output"]] = {"label": "afgeleid",
                                     "bron": f"timing:{check['id']} (referentie {check['referentie']}{suffix})"}
