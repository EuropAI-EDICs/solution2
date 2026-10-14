"""Quote-literaliteitsguard — cite-or-abstain-verzekering voor fase 2 (task 1A).

Elke normcard in ``corpus/normcards-*.json`` draagt een ``source.quote`` die
letterlijk uit de brontekst van het eigen ``docId`` moet komen (fase-1-praktijk,
taak 6/7-curatie). Deze guard maakt die controle permanent en machine-herhaalbaar
zodat de fase-2-curatietaken (3–7) en de eindreview erop kunnen leunen:

- docId -> brontekst:  S01  -> ``corpus/nl/CVDR709135/tekst.txt``
                       S02+ -> ``corpus/be/<bestand-zonder-.pdf>.txt`` via de
                       uri-join ``corpus/sources.json`` (docId.uri) tegen
                       ``corpus/be/META.json`` (instrumenten.bronUrl -> bestand)
- normalisatie (conform fase-1-reviewpraktijk): whitespace-collapse plus
  verwijderen van de spatie vóór leesteken — PDF-extractie introduceert beide
  artefacten, en het citaat is "letterlijk" zolang het daarop na normalisatie
  exact overeenkomt. Beide kanten krijgen dezelfde normalisatie.

``verify_all() -> list[str]``: lege lijst = alle citaten letterlijk; anders per
falende kaart één melding ``"<card-id>: quote niet letterlijk in <docId>"``.
Onoplosbare docId's of ontbrekende bronteksten falen even hard (luid, met een
specifieke melding) — een citaat zonder verifieerbare bron is per definitie
niet verifieerbaar letterlijk.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]  # poc-nspd/

# spatie vóór leesteken weg (PDF-extractie-artefact); dezelfde set als de
# fase-1-reviews: komma/punt/dubbele punt/puntkomma/uitroep/vraag/procent
_SPATIE_VOOR_LEESTEKEN = re.compile(r"\s+([,.;:!?%])")
_WHITESPACE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """Fase-1-normalisatie: whitespace-collapse + spatie-voor-leesteken."""
    return _SPATIE_VOOR_LEESTEKEN.sub(r"\1", _WHITESPACE.sub(" ", text)).strip()


def _document_teksten(corpus_root: Path) -> dict[str, str]:
    """docId -> brontekst (.txt-laag) voor S01 (nl) en S02–S05 (be).

    Ontbrekende registers (sources.json / be/META.json) zijn toegestaan voor
    minimale tmp-corpusfixtures: ongefilterde docId's resolvén dan niet en
    falen per kaart luid in ``verify_all`` (geen stil passes).
    """
    teksten: dict[str, str] = {}
    nl_pad = corpus_root / "corpus" / "nl" / "CVDR709135" / "tekst.txt"
    if nl_pad.is_file():  # S01: vaste NL-corpuslay-out
        teksten["S01"] = nl_pad.read_text(encoding="utf-8")
    bronnen_pad = corpus_root / "corpus" / "sources.json"
    meta_pad = corpus_root / "corpus" / "be" / "META.json"
    if not (bronnen_pad.is_file() and meta_pad.is_file()):
        return teksten
    bronnen = json.loads(bronnen_pad.read_text(encoding="utf-8"))
    meta = json.loads(meta_pad.read_text(encoding="utf-8"))
    uri_naar_bestand = {ins["bronUrl"]: ins["bestand"] for ins in meta["instrumenten"]}
    for doc_id, doc in bronnen.items():
        bestand = uri_naar_bestand.get(doc.get("uri"))
        if bestand is None:
            continue
        pad = corpus_root / "corpus" / "be" / bestand.replace(".pdf", ".txt")
        if pad.is_file():
            teksten[doc_id] = pad.read_text(encoding="utf-8")
    return teksten


def verify_all(corpus_root: Path | None = None) -> list[str]:
    """Controleer álle ``corpus/normcards-*.json``; lege lijst = OK.

    Elke kaart: ``source.quote`` moet na normalisatie een substring zijn van
    de genormaliseerde brontekst van ``source.docId``. Afwijzingen-ledgers
    (``normcards-rejected-*.json``) zijn geen kaarten en worden overgeslagen.
    """
    root = Path(corpus_root) if corpus_root is not None else _ROOT
    teksten = _document_teksten(root)
    meldingen: list[str] = []
    for shard in sorted((root / "corpus").glob("normcards-*.json")):
        if "rejected" in shard.name:
            continue
        for kaart in json.loads(shard.read_text(encoding="utf-8")):
            cid = kaart.get("id", "<zonder-id>")
            doc_id = (kaart.get("source") or {}).get("docId", "")
            quote = (kaart.get("source") or {}).get("quote", "")
            if doc_id not in teksten:
                meldingen.append(
                    f"{cid}: geen brontekst geresolveerd voor {doc_id} "
                    f"(quote niet verifieerbaar)")
                continue
            if _normalize(quote) not in _normalize(teksten[doc_id]):
                meldingen.append(f"{cid}: quote niet letterlijk in {doc_id}")
    return meldingen
