"""MC-5 — kennisbank met hergebruik en match-scores, en de suggestiematcher.

Deterministic Dutch-aware similarity: TF-IDF cosine over normalized unigrams +
bigrams, boosted by kennisbank hits (published replacement relations that resolve
to a doelregeling artikel). The matcher SUGGESTS ONLY (MC-6): rows leave this
module with status 'voorgesteld' — coupling is a human act.

Score bands mirror the recorded tool: >=0.90 sterk, 0.70-0.90 mogelijk, <0.70 zwak
("negen resultaten gevonden met een matching score van 90 tot 70%", 34:06-34:18).
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Dict, List, Optional, Tuple

from . import __version__

MATCHER_AGENT = f"matcher#{__version__}"

BAND_STERK = 0.90
BAND_MOGELIJK = 0.70

_STOPWORDS = set("""
de het een en of van in op voor met tot dat die dit als bij aan door om te naar uit over
is zijn wordt worden kan kunnen mag mogen moet moeten zal zullen heeft hebben had worden
niet geen meer minder meest minstens zodra indien mits tenzij behoudens voorzover
wordt afgekondigd vastgesteld bepaalt bepaald geldt gelden bedoeld bedoelde genoemd genoemde
artikel artikelen eerste tweede derde vierde vijfde lid onder aanhef
in het kader van dezen dien deze dit dat deswege daarbij daarin daarvan hierbij hierin
ons onze hun zijn haar its er dan ook al nog reeds wel slechts enkel uitsluitend zij
zoals volgens krachtens ingevolge overeenkomstig conform tenszij behalve daaronder
""".split())

_SUFFIXES = ("ing", "en", "e", "n", "s", "heid")


def _fold(term: str) -> str:
    term = unicodedata.normalize("NFKD", term)
    term = "".join(c for c in term if not unicodedata.combining(c))
    return term.lower()


def normalize(text: str) -> List[str]:
    """Tokenize + normalize Dutch legal text: fold case/diacritics, drop stopwords and
    pure numbers, strip a small suffix set (very light stemming, deterministic)."""
    raw = re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-']{2,}", text)
    out = []
    for t in raw:
        f = _fold(t)
        if f in _STOPWORDS or len(f) < 3 or f.isdigit():
            continue
        stemmed = f
        for suf in _SUFFIXES:
            if len(stemmed) - len(suf) >= 4 and stemmed.endswith(suf):
                stemmed = stemmed[: -len(suf)]
                break
        out.append(stemmed)
    return out


def terms(text: str) -> List[str]:
    toks = normalize(text)
    bigrams = [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
    return toks + bigrams


class TfidfIndex:
    def __init__(self, docs: Dict[str, str]):
        self._tf: Dict[str, Counter] = {k: Counter(terms(v)) for k, v in docs.items()}
        n_docs = max(1, len(docs))
        self._idf: Dict[str, float] = {}
        df: Counter = Counter()
        for c in self._tf.values():
            for t in c:
                df[t] += 1
        for t, d in df.items():
            self._idf[t] = math.log((1 + n_docs) / (1 + d)) + 1.0
        self._norm: Dict[str, float] = {}
        for k, c in self._tf.items():
            self._norm[k] = math.sqrt(sum((w * self._idf.get(t, 0.0)) ** 2 for t, w in c.items())) or 1.0

    def cosine(self, query: str, key: str) -> float:
        qc = Counter(terms(query))
        target = self._tf.get(key)
        if not target:
            return 0.0
        num = 0.0
        for t, w in qc.items():
            if t in target:
                num += w * self._idf.get(t, 0.0) * target[t] * self._idf.get(t, 0.0)
        return num / (self._query_norm(qc) * self._norm[key])

    def _query_norm(self, qc: Counter) -> float:
        return math.sqrt(sum((w * self._idf.get(t, 0.0)) ** 2 for t, w in qc.items())) or 1.0


class JaccardMatcher:
    """Independent second matcher used by the Critic's V3 re-execution (MC-6:
    an independent path must be able to disagree)."""

    @staticmethod
    def score(query: str, target: str) -> float:
        a, b = set(normalize(query)), set(normalize(target))
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)


class Kennisbank:
    def __init__(self, pairs: List[Dict]):
        self.pairs = pairs
        # bronLocator-number -> list of pairs (e.g. '22.46' from 'artikel 22.46 van de Bruidsschat')
        self._by_artikel: Dict[str, List[Dict]] = {}
        for p in pairs:
            m = re.search(r"(\d+\.\d+[a-z]?)", p["bronLabel"])
            if m:
                self._by_artikel.setdefault(m.group(1), []).append(p)
        # concept pairs (bestemming X) for future BP-side rows
        self._by_concept: Dict[str, List[Dict]] = {}
        for p in pairs:
            if p["relatie"] == "vertaalt_begrip":
                m = re.search(r"bestemming ([\wÀ-ÿ\-]+)", p["bronLabel"], re.I)
                if m:
                    self._by_concept.setdefault(_fold(m.group(1)), []).append(p)

    def hit_voor_bronregel(self, bron: Dict) -> Optional[Dict]:
        """Exact kennisbank hit for a bron regel artikelnummer (published relation)."""
        return (self._by_artikel.get(bron["locator"]["artikel"]) or [None])[0]

    def concept_hits(self, tekst: str) -> List[Dict]:
        toks = set(normalize(tekst))
        return [p for k, ps in self._by_concept.items() for p in ps if k in toks]


def _band(score: float) -> str:
    if score >= BAND_STERK:
        return "sterk"
    if score >= BAND_MOGELIJK:
        return "mogelijk"
    return "zwak"


def suggereer(bron: Dict, doel_index: List[Dict], index: TfidfIndex,
              kennisbank: Kennisbank, top_n: int = 3) -> List[Dict]:
    """Produce scored suggestions for one bron regel.

    A kennisbank hit that resolves to this doelRegel is a published conversion
    decision and scores 1.0 (sterk) — the recorded 'other customers also bought'
    reuse (MC-5). Without a hit the row leans purely on TF-IDF text similarity.
    Either way the row only ever becomes a SUGGESTION (MC-6).
    """
    kb_hit = kennisbank.hit_voor_bronregel(bron)
    query = f"{bron['locator']['label']} {bron['tekst']}"
    scored: List[Tuple[float, Dict]] = []
    for d in doel_index:
        target = f"artikel {d['locator']['artikel']} {d['locator']['titel']} {d['tekst']}"
        cos = index.cosine(query, d["id"])
        is_kb_target = bool(kb_hit and kb_hit.get("doelRegelId") == d["id"])
        if is_kb_target:
            # A published replacement relation IS the recorded conversion decision:
            # strongest possible reuse evidence (MC-5). Score is not blended down by
            # weak text similarity; the jurist still confirms applicability (MC-6/V4).
            score = 1.0
            parts = [f"kennisbank {kb_hit['id']}: officieel vastgestelde relatie '{kb_hit['relatie']}'",
                     f"(tfidf-cosinus ter vergelijking: {cos:.3f})"]
        else:
            score = cos
            parts = [f"tfidf-cosinus={cos:.3f}"]
            if kb_hit and kb_hit.get("doelRegelId"):
                parts.append(f"kennisbank {kb_hit['id']} wijst naar {kb_hit['doelRegelId']}, niet naar deze regel")
        if score <= 0.02:
            continue
        scored.append((score, {"doelRegelId": d["id"], "score": round(score, 4),
                               "band": _band(score), "kennisbankHitId": kb_hit["id"] if is_kb_target else None,
                               "scoreDetail": " + ".join(parts)}))
    scored.sort(key=lambda t: (-t[0], t[1]["doelRegelId"]))
    out: List[Dict] = []
    seen = set()
    for score, s in scored:
        if s["doelRegelId"] in seen:
            continue
        seen.add(s["doelRegelId"])
        out.append(s)
        if len(out) >= top_n:
            break
    return out
