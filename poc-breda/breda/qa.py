"""Grounded Q&A over de Breda vijf-waardenscan (GenAI-seam S4-analoog, PoC-4).

Architectuur — *LLMs propose, deterministic engines dispose* (GENAI_SEAMS.md):

  vraag (NL)
     │  asker: deterministische parser (cite-or-abstain) of LLM (voorstel)
     ▼
  ScanQuery (schema-gevalideerd contract — geen prompt is de query)
     │  gate: schema + woordenschatgronding (buurtnaam moet resolven)
     ▼
  execute_query — deterministisch over value-scan.json (geen LLM)
     ▼
  antwoord — deterministisch sjabloon, of LLM-narratie achter een
             numerieke grounding-gate (elk cijfer resolvet, teken-gevouwen;
             geen nieuwe buurtnamen); afkeuring → ledger + fallback

De transports zijn dezelfde als PoC-1 (``LDT_SCENARIO_LLM_ENDPOINT`` /
``LDT_SCENARIO_LLM_MODEL`` / ``LDT_SCENARIO_LLM_API``), met injecteerbare
``llm_call`` voor offline tests.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

WAARDEN = ("democratic", "spatial", "economic", "social")
WAARDE_LABELS = {
    "democratic": "democratic value",
    "spatial": "spatial value",
    "economic": "economic value",
    "social": "social value",
    "alle": "all four values",
}
_WAARDE_SYNONIEMEN = [
    (("democra",), "democratic"),
    (("ruimtelij", "groen", "ruggegraat", "spatial", "backbone", "green"), "spatial"),
    (("econom", "dak", "zon", "bedrijv", "roof", "solar", "business"), "economic"),
    (("sociaa", "sociale", "hitte", "warm", "verhard", "klimaatadaptatie", "kwetsbaar",
      "social", "heat", "paved", "vulnerab", "wellbeing"), "social"),
    (("alle waarden", "alle vier", "waardenprofiel", "all values", "all four",
      "value profile"), "alle"),
]

DEFAULT_LIMIT = 5


class QAError(RuntimeError):
    """Infrastructuurfout (geen endpoint, kapotte run-directory)."""


# --------------------------------------------------------------------------- #
# Normalisatie / woordenschat
# --------------------------------------------------------------------------- #


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).lower()
    return "".join(c for c in text if not unicodedata.combining(c))


def buurt_woordenschat(scan: dict) -> list[tuple[str, str]]:
    """(gevouwen, canoniek) per buurt — langste naam eerst voor deelm matching."""
    pairs = []
    for b in scan["buurten"]:
        naam = b.get("buurtnaam")
        if naam:
            pairs.append((_fold(naam), naam))
    pairs.sort(key=lambda p: -len(p[0]))
    return pairs


def resolve_buurt(text: str, scan: dict) -> str | None:
    """Canonieke buurtnaam als de tekst er precies één noemt; anders None."""
    folded = _fold(text)
    hits = [canoniek for gevod, canoniek in buurt_woordenschat(scan) if gevod in folded]
    if not hits:
        return None
    # meerdere treffers: alleen eenduidig als de langste de rest bevat
    langste = hits[0]
    if all(h in langste for h in hits):
        return langste
    return None


def detect_waarde(text: str) -> str | None:
    folded = _fold(text)
    for patronen, waarde in _WAARDE_SYNONIEMEN:
        if any(p in folded for p in patronen):
            return waarde
    return None


# --------------------------------------------------------------------------- #
# Deterministische asker — cite-or-abstain, nooit giswerk
# --------------------------------------------------------------------------- #


def parse_question(question: str, scan: dict) -> dict | None:
    """NL-vraag → ScanQuery-voorstel; ``None`` = onmappabel (onthouden)."""
    q = _fold(question)
    buurt = resolve_buurt(question, scan)
    waarde = detect_waarde(question)
    ranking = None
    if re.search(r"\b(hoogst\w*|top|best\w*|meeste|highest|most)\b", q):
        ranking = "hoogste"
    elif re.search(r"\b(laagst\w*|slechtst\w*|onderkant|minst\w*|lowest|worst|bottom|least)\b", q):
        ranking = "laagste"

    limit = None
    for m in re.findall(r"\b(\d{1,2})\b", question):
        n = int(m)
        if 1 <= n <= 10:
            limit = n

    if buurt is None and waarde is None:
        return None  # niets herkend — geen vraag-giswerk
    if buurt is None and ranking is None and waarde is None:
        return None

    return {
        "question": question.strip(),
        "buurtNaam": buurt,
        "waarde": waarde,
        "ranking": ranking if buurt is None else None,
        "limit": limit or DEFAULT_LIMIT,
        "focus": waarde if (buurt is not None and waarde in WAARDEN) else None,
        "proposedBy": "deterministic-parser",
    }


# --------------------------------------------------------------------------- #
# Deterministische runner — leest alleen het scan-artefact
# --------------------------------------------------------------------------- #


def _score(buurt: dict, waarde: str):
    if waarde not in WAARDEN:
        return None
    return (buurt.get("scores") or {}).get(waarde, {}).get("score")


def _median(scores: list) -> float | None:
    w = sorted(s for s in scores if s is not None)
    if not w:
        return None
    m = len(w) // 2
    return w[m] if len(w) % 2 else round((w[m - 1] + w[m]) / 2, 1)


def execute_query(query: dict, scan: dict) -> dict:
    buurten = [b for b in scan["buurten"] if b.get("water") == "NEE"]
    naam = query.get("buurtNaam")
    waarde = query.get("waarde") if query.get("waarde") in WAARDEN + ("alle",) else None

    if naam is not None:
        rows = [b for b in scan["buurten"] if b.get("buurtnaam") == naam]
        if not rows:  # afgevangen door de gate, maar de runner vertrouwt niets
            raise QAError(f"buurt {naam!r} niet in scan")
        row = rows[0]
        context = {}
        for v in WAARDEN:
            stad = [ _score(b, v) for b in buurten ]
            context[v] = {
                "mediaanGemeente": _median(stad),
                "nGescoord": sum(1 for s in stad if s is not None),
            }
        return {
            "query": query,
            "mode": "detail",
            "rows": [row],
            "context": context,
            "cityStats": {"nBuurten": len(scan["buurten"]),
                          "nLandBuurten": len(buurten)},
        }

    rijen = buurten
    if waarde in WAARDEN:
        rijen = [b for b in buurten if _score(b, waarde) is not None]
        rijen.sort(key=lambda b: (-b["scores"][waarde]["score"], b["buurtnaam"]))
        if query.get("ranking") == "laagste":
            rijen = list(reversed(rijen))
        limit = query.get("limit") or DEFAULT_LIMIT
        rijen = rijen[:limit]

    stats = {v: {"mediaan": _median([_score(b, v) for b in buurten]),
                 "nGescoord": sum(1 for b in buurten if _score(b, v) is not None)}
             for v in WAARDEN}
    return {
        "query": query,
        "mode": "ranking" if query.get("ranking") else "overzicht",
        "rows": rijen,
        "context": {},
        "cityStats": {"nBuurten": len(scan["buurten"]),
                      "nLandBuurten": len(buurten), "waardeStats": stats},
    }


# --------------------------------------------------------------------------- #
# Deterministische narrator + grounding-gate
# --------------------------------------------------------------------------- #


def _fmt(v):
    if v is None:
        return "onbekend"
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v)


def deterministic_answer(result: dict, scan: dict) -> str:
    q = result["query"]
    lines = [f"Question: {q['question']}"]
    if result["mode"] == "detail":
        b = result["rows"][0]
        lines.append(
            f"Neighbourhood {b['buurtnaam']} ({b['buurtcode']}, district {b['wijkcode']}, "
            f"{_fmt(b.get('aantalInwoners'))} residents):"
        )
        for v in WAARDEN:
            score = _score(b, v)
            ctx = result["context"][v]
            lines.append(
                f"- {WAARDE_LABELS[v]}: score {_fmt(score)} "
                f"(municipal median {_fmt(ctx['mediaanGemeente'])} over "
                f"{ctx['nGescoord']} neighbourhoods)"
            )
            for k, val in (b["scores"][v].get("inputs") or {}).items():
                if val is not None:
                    lines.append(f"    {k}: {_fmt(val)}")
            miss = (b.get("missing") or {}).get(v) or []
            if miss:
                lines.append(f"    missing: {', '.join(miss)}")
        kans = b.get("kansenkaart") or []
        if kans:
            lines.append(f"Climate opportunities: {'; '.join(kans)}")
        lines.append(
            "Scores are percentiles within Breda: higher means a higher rank "
            "among the scored neighbourhoods."
        )
        return "\n".join(lines)

    waarde = q.get("waarde")
    if waarde in WAARDEN and q.get("ranking"):
        label = WAARDE_LABELS[waarde]
        richting = "highest" if q["ranking"] == "hoogste" else "lowest"
        lines.append(f"The {richting} {len(result['rows'])} neighbourhoods on {label}:")
        for b in result["rows"]:
            lines.append(f"• {b['buurtnaam']} — {_fmt(_score(b, waarde))}")
        stats = result["cityStats"]["waardeStats"][waarde]
        lines.append(
            f"(median {_fmt(stats['mediaan'])}, {stats['nGescoord']} of "
            f"{result['cityStats']['nLandBuurten']} land neighbourhoods scored)"
        )
        return "\n".join(lines)

    if waarde in WAARDEN:
        stats = result["cityStats"]["waardeStats"][waarde]
        top = execute_query(
            {**q, "ranking": "hoogste", "limit": 3}, scan
        )
        lines.append(
            f"{WAARDE_LABELS[waarde].capitalize()} across the municipality: "
            f"{stats['nGescoord']} of {result['cityStats']['nLandBuurten']} "
            f"land neighbourhoods scored, median {_fmt(stats['mediaan'])}."
        )
        lines.append("Highest three: " + ", ".join(
            f"{b['buurtnaam']} ({_fmt(_score(b, waarde))})" for b in top["rows"]
        ))
        return "\n".join(lines)

    lines.append(
        f"The scan covers {result['cityStats']['nBuurten']} neighbourhoods "
        f"({result['cityStats']['nLandBuurten']} land neighbourhoods). "
        "Ask about a neighbourhood or a value (democratic, spatial, "
        "economic, social) for specific figures."
    )
    return "\n".join(lines)


def _collect_numbers(obj, out: set[str]) -> None:
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        s = repr(obj)  # volle precisie — het model moet verbatim kopiëren
        out.add(s)
        if "." in s:
            out.add(s.rstrip("0").rstrip("."))
    elif isinstance(obj, str):
        # cijferreeksen ín strings (buurtcode BU07580001, wijkcode, "deal-3")
        # zijn gegeground — anders valse afkeuringen bij het citeren ervan
        out.update(re.findall(r"\d+(?:[.,]\d+)?", obj))
    elif isinstance(obj, dict):
        for k in obj:
            if isinstance(k, str):
                # ook keys: "bomen_per_100_inw" groundt "per 100 inwoners"
                out.update(re.findall(r"\d+(?:[.,]\d+)?", k))
        for v in obj.values():
            _collect_numbers(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _collect_numbers(v, out)


def check_answer_grounding(answer: str, result: dict, scan: dict) -> list[str]:
    """Elk numeriek token in de prosa moet resolven tegen het geserialiseerde
    resultaat (teken-gevouwen, op eigen precisie); elke genoemde buurtnaam uit
    de scan-woordenschat moet in de rijen voorkomen. Geeft schendingen terug
    (leeg = geaccepteerd)."""
    serialized = json.dumps(
        {k: v for k, v in result.items() if k != "_scan"}, ensure_ascii=False
    )
    known = set()
    _collect_numbers(json.loads(serialized), known)
    for k in list(known):
        if "." in k:
            known.add(k.rstrip("0").rstrip("."))

    schendingen = []
    # lettergrens: "WK075800" en "qwen3.8" leveren géén losse tokens op
    for token in re.findall(r"(?<!\w)\d+(?:[.,]\d+)?(?!\w)", answer):
        kandidaten = [token.replace(",", ".")]
        # PoC-1-les (sign-fold): natuurlijke prosa herformatteert cijfers.
        # Nederlandse duizendtallen ("4.245" = 4245) en komma-decimalen zijn
        # gegronde formuleringen van dezelfde waarde — accepteren indien
        # één van de interpretaties resolvet.
        streepjes = kandidaten[0]
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", streepjes):
            kandidaten.append(streepjes.replace(".", ""))
        if re.fullmatch(r"\d{1,3}(,\d{3})+", token):
            kandidaten.append(token.replace(",", ""))
        kandidaten += [f"-{k}" for k in list(kandidaten)]
        if not any(k in known for k in kandidaten):
            schendingen.append(f"cijfer '{token}' komt niet voor in het resultaat")

    rij_namen = {(b.get("buurtnaam") or "").strip().lower() for b in result.get("rows", [])}
    for _gevod, canoniek in buurt_woordenschat(scan):
        lage = canoniek.strip().lower()
        if len(lage) < 5 or " " not in lage:
            continue  # korte/enkelwoordige namen zijn te ruisgevoelig
        if lage in answer.lower() and lage not in rij_namen:
            schendingen.append(
                f"buurt '{canoniek}' wordt genoemd maar zit niet in de resultaatrijen"
            )
    return schendingen


# --------------------------------------------------------------------------- #
# LLM-seam — asker & narrator (voorstel-only, injecteerbaar transport)
# --------------------------------------------------------------------------- #


def _strip_think(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", str(text), flags=re.S).strip()


def _http_chat_completions(endpoint, model, system, user, timeout):
    import os

    import requests

    payload = {
        "model": model, "temperature": 0, "max_tokens": 1024,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
    }
    if os.environ.get("LDT_SCENARIO_LLM_DISABLE_THINK", "1") != "0":
        payload["think"] = False
    resp = requests.post(
        f"{endpoint.rstrip('/')}/chat/completions", json=payload, timeout=timeout
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _ollama_chat(endpoint, model, system, user, timeout):
    import os

    import requests

    base = endpoint.rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    payload = {
        "model": model, "stream": False,
        "options": {"temperature": 0, "num_predict": 1024},
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
    }
    if os.environ.get("LDT_SCENARIO_LLM_DISABLE_THINK", "1") != "0":
        payload["think"] = False
    resp = requests.post(f"{base}/api/chat", json=payload, timeout=timeout)
    resp.raise_for_status()
    body = resp.json()
    if not body.get("done", True):
        raise QAError(f"ollama chat not done: {str(body)[:200]}")
    return (body.get("message") or {}).get("content") or ""


def resolve_transport():
    import os

    if os.environ.get("LDT_SCENARIO_LLM_API", "openai").lower() == "ollama":
        return _ollama_chat
    return _http_chat_completions


class LLMAsker:
    """Stelt een ScanQuery voor uit een NL-vraag; beslist nooit.

    Gate vóór executie: schema + woordenschatgronding (buurtNaam moet met
    resolve_buurt resolven). Gehallucineerde buurten/velden landen in de
    rejection-ledger, nooit in de runner.
    """

    def __init__(self, scan: dict, llm_call=None, model=None, endpoint=None,
                 timeout=120.0):
        import os

        self.scan = scan
        self.endpoint = endpoint if endpoint is not None else os.environ.get(
            "LDT_SCENARIO_LLM_ENDPOINT", ""
        )
        self.model = model or os.environ.get("LDT_SCENARIO_LLM_MODEL", "open-model-local")
        self._llm_call = llm_call or resolve_transport()
        self.timeout = timeout

    def system_prompt(self) -> str:
        namen = [canoniek for _, canoniek in buurt_woordenschat(self.scan)][::-1]
        return (
            "You translate a Dutch or English question about the Breda five-value "
            "scan into EXACTLY ONE JSON object (no prose around it). A "
            "deterministic runner executes it and answers WITH DATA; you only "
            "choose the query shape. Question forms: (a) 'waarom/hoe scoort "
            "<buurt> laag/hoog op <waarde>' or 'why/how does <neighbourhood> "
            "score low/high on <value>' → detail query: fill buurtNaam + waarde "
            "('why' is a data question, NOT a reason to abstain); (b) 'welke "
            "buurten … hoogst/laagst/top N' or 'which neighbourhoods … "
            "highest/lowest/top N' → ranking query: waarde + ranking + limit; "
            "(c) a median/municipality question → waarde without ranking; "
            "(d) anything else about one neighbourhood → buurtNaam. Rules: "
            "(1) buurtNaam must be VERBATIM a name from the list or null — "
            "never invent neighbourhood names; (2) waarde ∈ democratic|spatial|"
            "economic|social|alle|null; (3) ranking ∈ hoogste|laagste|null; "
            "(4) limit 1–10 or null; (5) focus is ONLY the named value "
            "(democratic|spatial|economic|social|null), never a neighbourhood "
            "name; (6) abstain ONLY if the question has nothing to do with "
            "Breda, neighbourhoods or values. Shape: "
            '{"question": "...", "buurtNaam": ..., "waarde": ..., '
            '"ranking": ..., "limit": ..., "focus": ...}. Example: question '
            '"why does Ginneken score low on green?" → {"question": '
            '"why does Ginneken score low on green?", "buurtNaam": "Ginneken", '
            '"waarde": "spatial", "ranking": null, "limit": null, '
            '"focus": "spatial"}. '
            f"Neighbourhood list: {json.dumps(namen, ensure_ascii=False)}"
        )

    @staticmethod
    def _normalize(p: dict) -> dict:
        """Seam-normalisatie van goedaardige vormdrift (PoC-1-les §5.2):
        modellen vullen 'Belcrum' in 'focus', voegen velden toe of vergeten
        limit. Alleen deterministisch afleidbare correcties; de rest valt
        door de schema-gate en belandt in de ledger."""
        out = {"question": p.get("question")}
        waarde = p.get("waarde")
        out["waarde"] = waarde if waarde in ("democratic", "spatial", "economic",
                                             "social", "alle") else None
        ranking = p.get("ranking")
        out["ranking"] = ranking if ranking in ("hoogste", "laagste") else None
        buurt = p.get("buurtNaam")
        out["buurtNaam"] = buurt if isinstance(buurt, str) and buurt else None
        try:
            limit = int(p.get("limit"))
        except (TypeError, ValueError):
            limit = 0
        out["limit"] = limit if 1 <= limit <= 10 else None
        focus = p.get("focus")
        focus = focus if focus in ("democratic", "spatial", "economic", "social") else None
        if focus is None and out["buurtNaam"] and out["waarde"] in WAARDEN:
            focus = out["waarde"]  # enige verdedigbare afleiding
        out["focus"] = focus
        return out

    def user_prompt(self, question: str) -> str:
        return f"Vraag: {question}"

    def propose(self, question: str) -> tuple[dict | None, dict | None]:
        """→ (query, afwijzing). Afwijzing gaat naar de ledger."""
        if not self.endpoint:
            raise QAError(
                "LLMAsker vereist LDT_SCENARIO_LLM_ENDPOINT (geen gisfallback)"
            )
        raw = _strip_think(self._llm_call(
            self.endpoint, self.model,
            self.system_prompt(), self.user_prompt(question), self.timeout,
        ))
        try:
            proposal = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
        except (ValueError, IndexError) as exc:
            return None, {"reason": f"JSON onparseerbaar: {exc}", "raw": raw[:400]}
        if proposal.get("abstain"):
            return None, {"reason": f"model onthield zich: {proposal.get('reason')}"}
        # identiteitsstempel door de seam: de query beantwoordt de GESTELDE
        # vraag — het model mag de vraag niet paraphraseren of vervangen
        proposal["question"] = question.strip()
        proposal = self._normalize(proposal)
        proposal["proposedBy"] = f"llm-proposal#{_slug(self.model)}"
        # gate 1: schema
        schema = json.loads(
            (Path(__file__).resolve().parent.parent / "schemas" / "scan-query.schema.json")
            .read_text(encoding="utf-8")
        )
        try:
            import jsonschema

            jsonschema.validate(proposal, schema)
        except ImportError:  # pragma: no cover
            pass
        except Exception as exc:
            return None, {"reason": f"schema-schending: {exc}", "proposal": proposal}
        # gate 2: woordenschat — buurt moet resolven; vreemde buurt = hallucinatie
        naam = proposal.get("buurtNaam")
        if naam is not None and resolve_buurt(naam, self.scan) is None:
            return None, {
                "reason": f"buurtnaam '{naam}' komt niet in de scan voor "
                          "(gehallucineerd of verouderd)",
                "proposal": proposal,
            }
        if naam is not None:
            proposal["buurtNaam"] = resolve_buurt(naam, self.scan)
        return proposal, None


class LLMNarrator:
    """Vertelt het deterministische antwoord in prosa — achter de gate."""

    def __init__(self, llm_call=None, model=None, endpoint=None, timeout=120.0):
        import os

        self.endpoint = endpoint if endpoint is not None else os.environ.get(
            "LDT_SCENARIO_LLM_ENDPOINT", ""
        )
        self.model = model or os.environ.get("LDT_SCENARIO_LLM_MODEL", "open-model-local")
        self._llm_call = llm_call or resolve_transport()
        self.timeout = timeout

    def system_prompt(self) -> str:
        return (
            "You answer a question about the Breda five-value scan in "
            "English, for a policy audience. HARD RULES: (1) copy EVERY "
            "figure verbatim from the provided JSON result — never invent, "
            "round or calculate; (2) name only neighbourhoods present in the "
            "rows; (3) no advice or conclusions beyond the data; (4) max 120 "
            "words; (5) state that scores are percentiles within Breda. "
            "Neighbourhood names stay in Dutch — they are data."
        )

    def narrate(self, result: dict, deterministic: str) -> str:
        if not self.endpoint:
            raise QAError("LLMNarrator requires LDT_SCENARIO_LLM_ENDPOINT")
        payload = json.dumps(
            {k: v for k, v in result.items() if k != "_scan"}, ensure_ascii=False
        )
        raw = _strip_think(self._llm_call(
            self.endpoint, self.model, self.system_prompt(),
            f"Question: {result['query']['question']}\nJSON result:\n{payload}",
            self.timeout,
        ))
        return raw.strip()


def _slug(model: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(model).lower()).strip("-")
