"""ArticleSplitter — CVDR-HTML → artikellijst (RegelRecht full export).

Tokenizer- en ankerlogica byte-dicht overgenomen uit poc-bp2op/pipeline/parsers.py
(geen runtime-import; vermijdt package-__version__-koppeling).
"""
from __future__ import annotations

import hashlib
import html as _html
import json
import pathlib
import re
from typing import Any, Dict, List, Literal, Optional, Tuple, TypedDict

import paths


class Article(TypedDict):
    number: str
    text: str
    url: str
    title: str
    containers: List[Dict[str, str]]


_ANCHOR_RE = re.compile(r'<a id="([^"]+)"')
_ART_ANCHOR_RE = re.compile(r"^chp_(\d+)((?:__[\w.\-]+?)*)__art_(\d+\.\d+[a-z]?)$")
_LID_RE = re.compile(r"__para_(\d+)$")
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _text(fragment: str) -> str:
    txt = _TAG_RE.sub(" ", fragment)
    return _WS_RE.sub(" ", _html.unescape(txt)).strip()


def tokenize(raw_html: str) -> List[Dict[str, Any]]:
    """Linearize the document into (kind, ids, level, text) tokens in document order."""
    body = re.sub(
        r"<script.*?</script>|<style.*?</style>|<!--.*?-->", " ", raw_html, flags=re.S
    )
    raw_tokens: List[Dict[str, Any]] = []
    for m in re.finditer(r"<(h[2-6]|p|li)\b[^>]*>(.*?)</\1>", body, re.S):
        kind_raw, inner = m.group(1), m.group(2)
        ids = _ANCHOR_RE.findall(m.group(0))
        level = int(kind_raw[1]) if kind_raw.startswith("h") else None
        kind = "heading" if level else ("para" if kind_raw == "p" else "li")
        text = _text(inner)
        if not text:
            continue
        raw_tokens.append(
            {
                "kind": kind,
                "level": level,
                "ids": ids,
                "text": text,
                "pos": m.start(),
                "end": m.end(),
            }
        )
    li_spans = [(t["pos"], t["end"]) for t in raw_tokens if t["kind"] == "li"]
    tokens = [
        t
        for t in raw_tokens
        if not (
            t["kind"] == "para"
            and any(a <= t["pos"] and t["end"] <= b for a, b in li_spans)
        )
    ]
    return tokens


def _hoofdstuk_titel(text: str) -> Optional[Tuple[int, str]]:
    m = re.match(r"^Hoofdstuk (\d+)\s+(.+)$", text)
    return (int(m.group(1)), m.group(2).strip()) if m else None


def _split_html(raw_html: str, cvdr_id: str, versie: int) -> List[Article]:
    tokens = tokenize(raw_html)
    regels: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {
        "hoofdstukNr": None,
        "hoofdstukTitel": None,
        "afdeling": None,
        "paragraaf": None,
    }
    artikel: Optional[Dict[str, Any]] = None

    def _flush() -> None:
        nonlocal artikel
        if artikel is None:
            return
        buf = artikel.pop("_buf")
        if not buf:
            buf = [artikel.pop("_kop")]
        else:
            artikel.pop("_kop", None)
        artikel["text"] = _WS_RE.sub(" ", " ".join(buf)).strip()
        artikel.pop("_lids", None)
        regels.append(artikel)
        artikel = None

    def _artikel_anchor(tok: Dict[str, Any]) -> Optional[Tuple[str, int, str]]:
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
                current = {
                    "hoofdstukNr": hk[0],
                    "hoofdstukTitel": hk[1],
                    "afdeling": None,
                    "paragraaf": None,
                }
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
            aid, _chp_nr, art_nr = anchor
            title = re.sub(r"^Artikel\s+\d+\.\d+[a-z]?\s*", "", text).strip() or text
            containers: List[Dict[str, str]] = []
            if current["hoofdstukNr"] is not None:
                containers.append(
                    {
                        "kind": "hoofdstuk",
                        "label": f"Hoofdstuk {current['hoofdstukNr']} {current['hoofdstukTitel']}",
                    }
                )
            if current["afdeling"]:
                containers.append({"kind": "afdeling", "label": current["afdeling"]})
            if current["paragraaf"]:
                containers.append({"kind": "paragraaf", "label": current["paragraaf"]})
            artikel = {
                "number": art_nr,
                "title": title,
                "url": f"https://lokaleregelgeving.overheid.nl/{cvdr_id}/{versie}#{aid}",
                "containers": containers,
                "text": "",
                "_buf": [],
                "_kop": text,
                "_lids": set(),
            }
            continue
        if artikel is not None:
            if text in ("[Gereserveerd]", "[Vervallen]"):
                continue
            if tok["kind"] == "para":
                artikel["_buf"].append(text)
            elif tok["kind"] == "li":
                artikel["_buf"].append(text)
                for lid in tok["ids"]:
                    if _LID_RE.search(lid):
                        artikel["_lids"].add(lid)
    _flush()

    # Dedup on number: keep first non-empty text
    by_num: Dict[str, Article] = {}
    order: List[str] = []
    for r in regels:
        num = r["number"]
        art: Article = {
            "number": num,
            "text": r["text"],
            "url": r["url"],
            "title": r["title"],
            "containers": r["containers"],
        }
        if num not in by_num:
            by_num[num] = art
            order.append(num)
        elif not by_num[num]["text"] and art["text"]:
            by_num[num] = art
    return [by_num[n] for n in order]


def split_instrument(poc: Literal["utrecht", "eindhoven"]) -> List[Article]:
    meta = paths.INSTRUMENTS[poc]
    html_path: pathlib.Path = meta["html"]
    if not html_path.exists():
        raise SystemExit(f"ontbrekende HTML-bron: {html_path}")
    raw = html_path.read_text(encoding="utf-8", errors="ignore")
    arts = _split_html(raw, meta["cvdr"], meta["versie"])
    if not arts:
        raise SystemExit(f"0 artikelen in {html_path}")
    return arts


def write_articles_json(
    poc: Literal["utrecht", "eindhoven"],
    articles: List[Article],
    out_path: pathlib.Path,
) -> None:
    meta = paths.INSTRUMENTS[poc]
    html_path: pathlib.Path = meta["html"]
    rel = html_path.relative_to(paths.ROOT).as_posix()
    payload = {
        "poc": poc,
        "cvdr": meta["cvdr"],
        "sourceHtml": rel,
        "sourceSha256": hashlib.sha256(html_path.read_bytes()).hexdigest(),
        "articles": articles,
    }
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
