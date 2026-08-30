"""MC-4 — automatisch inlezen en opknippen.

Deterministic parsers that split the archived official Eindhoven publications into
rule records. Nothing is invented: every record carries its verbatim text plus a
deep link into the official publication. One HTML tokenizer serves both source
families (lokaleregelgeving CVDR and officielebekendmakingen GMB share the same
renderer conventions: data-element containers, docArtikel/docDivisietekst headings).
"""

from __future__ import annotations

import html as _html
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import __version__

PARSER_AGENT = f"regel-parser#{__version__}"

_ANCHOR_RE = re.compile(r'<a id="([^"]+)"')
_ART_ANCHOR_RE = re.compile(r"^chp_(\d+)((?:__[\w.\-]+?)*)__art_(\d+\.\d+[a-z]?)$")
_LID_RE = re.compile(r"__para_(\d+)$")
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _text(fragment: str) -> str:
    txt = _TAG_RE.sub(" ", fragment)
    return _WS_RE.sub(" ", _html.unescape(txt)).strip()


def tokenize(raw_html: str) -> List[Dict[str, Any]]:
    """Linearize the document into (kind, ids, level, text) tokens in document order.

    kind: 'heading' for h2-h6, 'para' for <p>, 'li' for list items.
    Only structural containers are emitted; scripts/styles are stripped first.
    """
    body = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", " ", raw_html, flags=re.S)
    raw_tokens: List[Dict[str, Any]] = []
    for m in re.finditer(r"<(h[2-6]|p|li)\b[^>]*>(.*?)</\1>", body, re.S):
        kind_raw, inner = m.group(1), m.group(2)
        ids = _ANCHOR_RE.findall(m.group(0))
        level = int(kind_raw[1]) if kind_raw.startswith("h") else None
        kind = "heading" if level else ("para" if kind_raw == "p" else "li")
        text = _text(inner)
        if not text:
            continue
        raw_tokens.append({"kind": kind, "level": level, "ids": ids, "text": text,
                           "pos": m.start(), "end": m.end()})
    # an <li> already contains its nested <p>: emit each piece of text once so that
    # joined artikel tekst stays a verbatim substring of the linearized source (V2)
    li_spans = [(t["pos"], t["end"]) for t in raw_tokens if t["kind"] == "li"]
    tokens = [t for t in raw_tokens
              if not (t["kind"] == "para" and any(a <= t["pos"] and t["end"] <= b for a, b in li_spans))]
    return tokens


# --------------------------------------------------------------------------- #
# doelregeling (MC-1): artikel-level index of the CVDR consolidation
# --------------------------------------------------------------------------- #

def _hoofdstuk_titel(text: str) -> Optional[Tuple[int, str]]:
    m = re.match(r"^Hoofdstuk (\d+)\s+(.+)$", text)
    return (int(m.group(1)), m.group(2).strip()) if m else None


def parse_doelregeling(raw_html: str, cvdr: str, cvdr_id: str, versie: int,
                       exclude_hoofdstukken: set, today: str) -> List[Dict[str, Any]]:
    """Split the CVDR consolidation into artikel-level DoelRegel records.

    Articles are recognized by their stable chp_ anchor ids, on ANY token kind: the
    renderer emits some artikel titles as heading (h3/h4/h5/h6) but deep-nested ones
    as plain paragraph with the art anchor inside. The toelichting has no chp_
    anchors and is therefore skipped structurally, not by guesswork.
    """
    tokens = tokenize(raw_html)
    regels: List[Dict[str, Any]] = []
    current = {"hoofdstukNr": None, "hoofdstukTitel": None, "afdeling": None, "paragraaf": None}
    artikel: Optional[Dict[str, Any]] = None

    def _flush() -> None:
        nonlocal artikel
        if artikel is None:
            return
        buf = artikel.pop("_buf")
        if not buf:
            buf = [artikel.pop("_kop")]  # fully struck/reserved artikel: keep the
            # printed heading line as its verbatim tekst
        artikel["tekst"] = _WS_RE.sub(" ", " ".join(buf)).strip()
        artikel["lidaantal"] = len(artikel.pop("_lids"))
        regels.append(artikel)
        artikel = None

    def _artikel_anchor(tok) -> Optional[Tuple[str, int, str]]:
        for aid in tok["ids"]:
            m = _ART_ANCHOR_RE.match(aid)
            if m:
                return aid, int(m.group(1)), m.group(3)
        return None

    for tok in tokens:
        text = tok["text"]
        if tok["kind"] == "heading":
            hk = _hoofdstuk_titel(text)
            if hk:
                _flush()
                current = {"hoofdstukNr": hk[0], "hoofdstukTitel": hk[1], "afdeling": None, "paragraaf": None}
                continue
            if text.startswith("Afdeling "):
                _flush()
                current["afdeling"] = text
                current["paragraaf"] = None
                continue
            if text.startswith(("Paragraaf ", "Subparagraaf ", "Subsubparagraaf ")):
                _flush()
                current["paragraaf"] = text
                continue
        anchor = _artikel_anchor(tok)
        if anchor and re.match(r"^Artikel\s+\d+\.\d+", text):
            _flush()
            aid, chp_nr, art_nr = anchor
            title = re.sub(r"^Artikel\s+\d+\.\d+[a-z]?\s*", "", text).strip() or text
            pad_parts = [f"Hoofdstuk {current['hoofdstukNr']} {current['hoofdstukTitel']}"]
            if current["afdeling"]:
                pad_parts.append(current["afdeling"])
            if current["paragraaf"]:
                pad_parts.append(current["paragraaf"])
            artikel = {
                "cvdr": f"{cvdr_id}/{versie}",
                "locator": {
                    "hoofdstukNr": current["hoofdstukNr"],
                    "hoofdstukTitel": current["hoofdstukTitel"],
                    "afdeling": current["afdeling"],
                    "paragraaf": current["paragraaf"],
                    "artikel": art_nr,
                    "titel": title,
                    "pad": " > ".join(pad_parts),
                },
                "tekst": "",
                "url": f"https://lokaleregelgeving.overheid.nl/{cvdr_id}/{versie}#{aid}",
                "_buf": [],
                "_kop": text,
                "_lids": set(),
                "_chp": chp_nr,
            }
            continue
        if artikel is not None:
            if text in ("[Gereserveerd]", "[Vervallen]"):
                continue  # structural markers, not rule text
            if tok["kind"] == "para":
                artikel["_buf"].append(text)
            elif tok["kind"] == "li":
                artikel["_buf"].append(text)
                for aid in tok["ids"]:
                    if _LID_RE.search(aid):
                        artikel["_lids"].add(aid)
    _flush()

    out: List[Dict[str, Any]] = []
    for i, r in enumerate(regels, start=1):
        out.append({
            "id": f"DR-{i:03d}",
            "cvdr": r["cvdr"],
            "locator": r["locator"],
            "tekst": r["tekst"],
            "tekstLanguage": "nl",
            "url": r["url"],
            "lidaantal": r["lidaantal"],
            "gebruiksdoel": r["locator"]["paragraaf"].replace("Paragraaf ", "", 1) if (r["_chp"] == 3 and r["locator"]["paragraaf"]) else None,
            "extractedBy": PARSER_AGENT,
            "extractedAt": today,
        })
    return out


def filter_doel_index(doelregels: List[Dict[str, Any]], hoofdstukken: set) -> List[Dict[str, Any]]:
    """Keep only artikelen of the given hoofdstukken (renumber after filtering)."""
    kept = [d for d in doelregels if d["locator"]["hoofdstukNr"] in hoofdstukken]
    for i, d in enumerate(kept, start=1):
        d["id"] = f"DR-{i:03d}"
    return kept


def bronregels_uit_doelindex(doelregels: List[Dict[str, Any]], hoofdstukken: set, doc_id: str,
                             instrument: str, url: str, today: str) -> List[Dict[str, Any]]:
    """Derive the bron population from the tijdelijk-deel/bruidschat chapters (hoofdstuk 22/23).

    These chapters hold the old-law continuation rules that the transition must
    eventually dissolve into new-deel rules; [Vervallen] markers (later wijzigingen
    already dissolved them) are carried through as statusInBron.
    """
    out: List[Dict[str, Any]] = []
    for d in doelregels:
        if d["locator"]["hoofdstukNr"] not in hoofdstukken:
            continue
        vervallen = bool(re.search(r"\[Vervallen\]", d["locator"]["titel"]))
        out.append({
            "id": f"BR-{len(out) + 1:03d}",
            "docId": doc_id,
            "instrument": instrument,
            "locator": {
                "hoofdstuk": d["locator"]["pad"],
                "artikel": d["locator"]["artikel"],
                "label": ("artikel " + d["locator"]["artikel"] + " " +
                          re.sub(r"\s?\[Vervallen\]", "", d["locator"]["titel"])).strip(),
            },
            "tekst": d["tekst"],
            "tekstLanguage": "nl",
            "url": d["url"],
            "statusInBron": "vervallen_in_bron" if vervallen else "geldend",
            "thema": _thema_van(d),
            "stackingRef": None,
            "extractedBy": PARSER_AGENT,
            "extractedAt": today,
        })
    return out


# --------------------------------------------------------------------------- #
# kennisbank seeds (MC-5) from published replacement relations
# --------------------------------------------------------------------------- #

_PLAATS_RE = re.compile(
    r"Artikel (?P<nieuw>\d+\.\d+[a-z]?)[^.;]{0,200}?komt in de plaats van "
    r"(?:artikel (?P<oud_b>\d+\.\d+[a-z]?) van de Bruidsschat|(?P<oud_vo>artikel \d+\.\d+[a-z]?"
    r"(?: van het )?(?:voormalige )?[\wÀ-ÿ'’\- ]{3,80}?))",
    re.I,
)
_VOORTZETTING_RE = re.compile(
    r"Artikel (?P<nieuw>\d+\.\d+[a-z]?)[^.]{0,140}?(?:is een )?voortzetting van (?P<bron>[^.]{3,140})",
    re.I,
)


def parse_kennisbank_pairs(raw_html: str, doc_id: str, url: str, today: str,
                           doel_index: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract 'komt in de plaats van' / 'voortzetting van' relations from a besluit's toelichting.

    Every pair keeps the verbatim establishing sentence and the permalink of the
    publication it was read from (MC-7). doelLocator→doelRegelId resolution is done
    against the doelregeling index so suggestions can boost on real pairs only.
    """
    plain = _text(re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw_html, flags=re.S))
    plain = _WS_RE.sub(" ", plain)
    by_artikel = {d["locator"]["artikel"]: d["id"] for d in doel_index}
    pairs: List[Dict[str, Any]] = []
    seen: set = set()

    def _add(new_art: str, oud_label: str, relatie: str, quote: str) -> None:
        key = (new_art, oud_label.lower())
        if key in seen:
            return
        seen.add(key)
        pairs.append({
            "id": f"KB-{len(pairs) + 1:03d}",
            "bronLabel": oud_label,
            "doelLocator": f"artikel {new_art}",
            "doelRegelId": by_artikel.get(new_art),
            "relatie": relatie,
            "quote": quote[:600],
            "bronDocId": doc_id,
            "url": url,
            "origin": "officiele_publicatie",
            "methodTrace": ["MC-5", "MC-7"],
            "extractedBy": PARSER_AGENT,
            "extractedAt": today,
        })

    for m in _PLAATS_RE.finditer(plain):
        nieuw = m.group("nieuw")
        if m.group("oud_b"):
            oud = f"artikel {m.group('oud_b')} van de Bruidsschat"
        elif m.group("oud_vo"):
            oud = m.group("oud_vo").strip()
        else:
            continue
        quote = plain[max(0, m.start() - 80):m.end() + 2].strip()
        _add(nieuw, oud, "vervangt", quote)
    for m in _VOORTZETTING_RE.finditer(plain):
        quote = plain[max(0, m.start() - 80):m.end() + 2].strip()
        _add(m.group("nieuw"), m.group("bron").strip().rstrip(" ,"), "voortzetting", quote)
    return pairs


def taxonomie_pairs(doel_index: List[Dict[str, Any]], doc_id: str, url: str, today: str,
                    quote: str) -> List[Dict[str, Any]]:
    """Seed the gebruiksdoel taxonomy (the concept that replaces 'bestemming') as
    vertaalt_begrip pairs from the doelregeling's own hoofdstuk-3.4 paragrafen."""
    pairs: List[Dict[str, Any]] = []
    for d in doel_index:
        gd = d.get("gebruiksdoel")
        if not gd or ":" in gd or " " in gd.strip():
            continue
        pairs.append({
            "id": f"KB-{len(pairs) + 1:03d}",
            "bronLabel": f"bestemming {gd.lower()}",
            "doelLocator": f"artikel {d['locator']['artikel']}",
            "doelRegelId": d["id"],
            "relatie": "vertaalt_begrip",
            "quote": quote,
            "bronDocId": doc_id,
            "url": d["url"],
            "origin": "doelregeling_taxonomie",
            "methodTrace": ["MC-5"],
            "extractedBy": PARSER_AGENT,
            "extractedAt": today,
        })
    return pairs


# --------------------------------------------------------------------------- #
# plan portfolio (MC-8) from the Planviewer inventory page
# --------------------------------------------------------------------------- #

def parse_planviewer_inventory(raw_html: str) -> Dict[str, Any]:
    rows = re.findall(
        r'href="/bestemmingsplannen/view/(NL\.IMRO\.0772\.[^"]+)"[^>]*>(.*?)</a>', raw_html, re.S)
    records: Dict[str, Dict[str, str]] = {}
    for pid, inner in rows:
        t = _text(inner)
        if not t:
            continue
        rec = records.setdefault(pid, {"planidn": pid})
        low = t.lower()
        if low in ("bestemmingsplan", "wijzigingsplan", "structuurvisie", "beheersverordening",
                   "gemeenteblad", "gerechtelijke uitspraak", "uitwerkingsplan"):
            rec.setdefault("type", t)
        elif low.startswith("tam-omgevingsplan") or low.startswith("omgevingsplan"):
            rec.setdefault("type", t if low.startswith("tam") else "omgevingsplan")
            rec.setdefault("naam", t)
        elif low in ("vastgesteld", "ontwerp", "geconsolideerd", "concept"):
            rec.setdefault("status", t)
        elif re.match(r"^\d{2}-\d{2}-\d{4}$", t):
            rec.setdefault("datum", t)
        elif not rec.get("naam") and len(t) > 6 and not t.lower().startswith("bekijk"):
            rec.setdefault("naam", t)
    return {
        "records": records,
        "plannenTotaal": len({p.split("-")[0] for p in records}),
        "vastgesteld": sum(1 for r in records.values() if r.get("status") == "vastgesteld"),
        "tamOmgevingsplannen": sum(1 for r in records.values() if str(r.get("naam", "")).startswith("TAM-omgevingsplan")),
    }


# --------------------------------------------------------------------------- #
# thema classification (shared by bron regels and the coverage analyser)
# --------------------------------------------------------------------------- #

_THEMAS: List[Tuple[str, re.Pattern]] = [
    ("gebruik:wonen", re.compile(r"\bwonen\b|\bwoning\b|\bwoongebied\b", re.I)),
    ("gebruik:bedrijf", re.compile(r"\bbedrijf\b|\bbedrijfsactiviteit\b|\buitoefening van bedrijf\b", re.I)),
    ("gebruik:detailhandel", re.compile(r"\bdetailhandel\b|\bwinkel\b", re.I)),
    ("gebruik:maatschappelijk", re.compile(r"maatschappelijke dienstverlening|maatschappelijk gebied", re.I)),
    ("gebruik:horeca", re.compile(r"\bhoreca\b|\bhorecagelegenheid\b", re.I)),
    ("gebruik:kantoor", re.compile(r"\bkantoor\b", re.I)),
    ("gebruik:agrarisch", re.compile(r"\bagrarisch\b|\bagrarische\b|\bveehouderij\b", re.I)),
    ("gebruik:cultuur_ontspanning", re.compile(r"cultuur en ontspanning|\bcinema\b|\btheater\b", re.I)),
    ("bouwen:bouwwerken", re.compile(r"\bbouwen\b|\bbouwwerk\b|\bbouwregel\b|\bbouwvlak\b|\bhoogte\b|\bgoot\b", re.I)),
    ("milieu:geluid", re.compile(r"\bgeluid\b|\bakoestisch\b", re.I)),
    ("milieu:geur", re.compile(r"\bgeur\b|\bstank\b", re.I)),
    ("milieu:bodemsanering", re.compile(r"bodem(sanering)?\b|bodemkwaliteit", re.I)),
    ("milieu:afval", re.compile(r"\bafval\b|\bvuil\b", re.I)),
    ("veiligheid:brand", re.compile(r"\bbrand\b|\bbrandveilig\b|\bopslag\b|\binrichting\b", re.I)),
    ("veiligheid:externe", re.compile(r"externe veiligheid|\brisicogebied\b|\binformatiezone\b|\bexplosie\b", re.I)),
    ("natuur:flora_fauna", re.compile(r"flora en fauna|\bhoutopstand\b|\bnatuur\b|\bboom\b|\bvellen\b", re.I)),
    ("water:algemeen", re.compile(r"\bwater\b|\bgrondwater\b|\briolering\b|\bwaterhuishouding\b", re.I)),
    ("erfgoed:algemeen", re.compile(r"monument|\bcultuurhistorisch\b|\berfgoed\b", re.I)),
    ("verkeer:parkeren", re.compile(r"\bparkeren\b|\bparkeer\b|\bverkeer\b|\bvoertuig\b", re.I)),
    ("gebruik:overig", re.compile(r".", re.I)),
]


def _thema_van(regel: Dict[str, Any]) -> str:
    tekst = f"{regel['locator'].get('titel', '')} {regel['tekst']}"
    for naam, pat in _THEMAS:
        if pat.search(tekst):
            return naam
    return "gebruik:overig"
