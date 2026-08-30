"""MC-7 — het enkele-file HTML-rapport: beide kanten in context, controleerbaar.

Everything is inlined: the report works when opened directly from disk (file://).
"""

from __future__ import annotations

import html as _html
from pathlib import Path
from typing import Dict, List, Optional

from . import __version__

REPORT_AGENT = f"report#{__version__}"

_MC_IMPL = [
    ("MC-1", "Transitiestrategie met doelregeling (02:31–07:33)",
     "De index van alle 24-hoofdstuk-artikelen van Omgevingsplan Eindhoven (CVDR696400, geldend 29-06-2026) is de doelregeling; de analyse signaleert waar deze eerst uitgebreid moet worden."),
    ("MC-2", "Beleidsneutraal omzetten (15:44–16:31)",
     "conversion-request pinned op beleid=neutraal; rijen die beleid zouden veranderen gaan naar needs_human, nooit automatisch gekoppeld."),
    ("MC-3", "De omzettabel als kernartefact (20:13–30:06)",
     "omzettabel.json / omzettabel.md / dit rapport: links de letterlijke bronregel, rechts 1..n doelregels (activiteiten stapelen)."),
    ("MC-4", "Automatisch inlezen en opknippen (21:07–26:55)",
     "Deterministische parsers knippen CVDR + Gemeenteblad-publicaties op tot artikel-regels met letterlijke tekst en dieptelinks; validatie blijft altijd nodig (V2)."),
    ("MC-5", "Kennisbank met hergebruik en match-scores (33:13–34:58)",
     "275 ‘komt in de plaats van’-relaties uit het Eindhovense wijzigingsbesluit 2025 + de gebruiksdoel-taxonomie vormen de kennisbank; TF-IDF-cosinus + kennisbank-boost geven gescoorde suggesties in de banden 90/70."),
    ("MC-6", "Mens blijft op de knoppen (26:07–35:45)",
     "Status blijft ‘voorgesteld’; V4-juristtoets is een eigen, altijd-pendent validatieniveau; de Critic draait een onafhankelijke matcher (V3)."),
    ("MC-7", "Controleerbaarheid (34:23–37:26)",
     "Elke regel draagt permalink + letterlijk citaat; rijen hebben toelichting-veld en reviewTrail (wijzigingsgeschiedenis); rapport toont beide kanten in context."),
    ("MC-8", "Bulk-analyse voor planning (54:43–55:43)",
     "coverage-report: match-ratio per brondocument, conversie-gereedheid, ‘doelregeling eerst uitbreiden’-clusters, portefeuillestatistiek."),
    ("MC-9", "Procesontwerp (09:04–17:26)",
     "Pilotcriteria (laagdynamisch, geen open beleidswijziging, vergelijkbare gebieden, deelgebied toegestaan) staan in de request; de Amsterdams cijfers (1000 u/plan → 450 FTE; 20× sneller met tool) staan als business case in het rapport."),
    ("MC-10", "Input-kwaliteit en stapeling (60:00–63:20)",
     "Elke bronregel documenteert haar herkomst; stapelingsrisico (postzegelplannen/TAM over moederplannen) staat als expliciete needs_human-reden en in de beperkingen."),
    ("MC-11", "Werkingsgebieden zijn (nog) geen AI (37:28–38:11)",
     "Bewust géén geometriemotor: het schema houdt werkingsgebiedRef vrij voor de robotiseringsstap; citaat in de beperkingen."),
    ("MC-12", "Kwaliteitsborging van de tool (52:53–54:13)",
     "Deze pipeline is deterministisch en standaard offline (geen data verlaat de machine); run_summary bevat de self-assessment-checklist (algoritmeregister / privacy / modelkeuze)."),
]

_LIMITATIONS = [
    "<b>DSO API's zijn key-gated</b> (HTTP 401 geverifieerd, conform PoC-1): de officiële machine-leesbare tijdelijk-deel- en TAM-documenten zijn niet zonder sleutel in te lezen. De PoC leest daarom de officiële publicaties (CVDR-consolidatie + Gemeenteblad-bekendmakingen) — dezelfde bron, andere ontsluiting. De Amsterdam-tool zelf leest via de DSO-overbruggingsfunctie (41:04).",
    "<b>Bruidsschat/tijdelijk-deel-artikelen als bronpopulatie</b>: de omzettabel dekt de hoofdstuk 22/23-artikelen (voortgezette oude-wet-regels) van het geldende omgevingsplan; volledige per-bestemmingsplan regelteksten vereisen de DSO-connector (zie hierboven).",
    "<b>Suggesties ≠ koppelingen</b> (MC-6): elke ‘voorgesteld’-rij wacht op juristtoets; de kennisbank bevat uitsluitend officieel gepubliceerde relaties.",
    "<b>Score-banden zijn kalibreerbaar</b>: de drempels 0,90/0,70 spiegelen de 90–70%-weergave van de tool; de deterministische matcher is bewust eenvoudig (TF-IDF + kennisbank-boost) om uitwisselbaar te blijven met een LLM-hook (MC-4: Europees model bij Amsterdam, 30:49).",
    "<b>Geen werkingsgebieden</b> (MC-11): geometrie verandert niet bij regelwissel; dit is robotisering, geen AI — geciteerd achtergelaten als scope-keuze met placeholder in het contract.",
    "<b>Stapeling en inputkwaliteit</b> (MC-10): waar geen gepubliceerd bewijs van bovenliggende postzegelplannen/TAM's per locatie voorhanden is, kan de pipeline stapeling niet zelf vaststellen — die rijen gaan naar needs_human.",
]


def _esc(s: str) -> str:
    return _html.escape(str(s), quote=True)


def render(out_path: Path, *, title: str, subtitle: str, generated: str, run_id: str,
           verdict: str, headline_cards: List[Dict[str, str]], coverage_rows: List[Dict],
           needs_new: List[Dict], portfolio: Dict, kb_pairs: List[Dict],
           omzettabel: List[Dict], bron_regels: List[Dict], doel_regels: List[Dict],
           validation: Dict, footer: str) -> None:
    tpl = (Path(__file__).parent / "report_template.html").read_text(encoding="utf-8")

    cards_html = "\n".join(
        f'<div class="card"><b>{_esc(c["label"])}</b><span class="num">{_esc(c["value"])}</span>'
        f'<div class="mut">{_esc(c["note"])}</div></div>' for c in headline_cards)

    method_rows = "\n".join(
        f'<tr><td><b>{mc}</b></td><td>{_esc(t)}</td><td>{_esc(impl)}</td></tr>'
        for mc, t, impl in _MC_IMPL)

    cov_rows = "\n".join(
        f'<tr><td>{_esc(d["naam"])}</td><td>{d["nRegels"]}</td><td>{d["sterk"]}</td>'
        f'<td>{d["mogelijk"]}</td><td>{d["geenMatch"]}</td><td>{d["matchRatio"]:.0%}</td>'
        f'<td><b>{_esc(d["gereedheid"])}</b></td></tr>' for d in coverage_rows)

    nn_rows = "\n".join(
        f'<tr><td>{_esc(n["thema"])}</td><td>{n["nRegels"]}</td>'
        f'<td>{_esc(", ".join(n["voorbeeldBronRegelIds"]))}</td></tr>' for n in needs_new) or \
        '<tr><td colspan="3">geen — elke bronregel vond minimaal een mogelijke match</td></tr>'

    kb_rows = "\n".join(
        f'<tr><td>{_esc(p["id"])}</td><td>{_esc(p["bronLabel"])}</td><td>→</td>'
        f'<td>{_esc(p["doelLocator"])}</td><td>{_esc(p["relatie"])}</td>'
        f'<td>{_esc(p["origin"])}<br><a href="{_esc(p["url"])}">bron</a></td></tr>'
        for p in kb_pairs[:120])
    kb_summary = (f"{len(kb_pairs)} kennisbank-relaties: "
                  f"{sum(1 for p in kb_pairs if p['relatie'] == 'vervangt')} vervangt, "
                  f"{sum(1 for p in kb_pairs if p['relatie'] == 'voortzetting')} voortzetting, "
                  f"{sum(1 for p in kb_pairs if p['relatie'] == 'vertaalt_begrip')} vertaalt_begrip. "
                  "Eerste 120 hieronder; volledige set in kennisbank.json.")

    bron = {b["id"]: b for b in bron_regels}
    doel = {d["id"]: d for d in doel_regels}
    ot_rows = []
    ot_detail = []
    for row in omzettabel:
        b = bron[row["bronRegelId"]]
        best = row["suggesties"][0] if row["suggesties"] else None
        if best:
            d = doel[best["doelRegelId"]]
            best_txt = f'{_esc(d["locator"]["artikel"])} {_esc(d["locator"]["titel"])}'
            score = f'{best["score"]:.2f}'
            band = best["band"]
        else:
            best_txt, score, band = "— nieuwe doelregel nodig —", "—", "geen"
        ot_rows.append(
            f'<tr><td>{_esc(row["id"])}</td><td>{_esc(b["locator"]["label"])}</td>'
            f'<td>{_esc(b["statusInBron"])}</td><td>{best_txt}</td><td>{score}</td>'
            f'<td><span class="band {_esc(band)}">{_esc(band)}</span></td>'
            f'<td><span class="status">{_esc(row["status"])}</span></td></tr>')
        sugg_html = "".join(
            f'<li><b>{_esc(doel[s["doelRegelId"]]["locator"]["artikel"])} {_esc(doel[s["doelRegelId"]]["locator"]["titel"])}</b> '
            f'— score {s["score"]:.2f} <span class="band {_esc(s["band"])}">{_esc(s["band"])}</span>'
            f'{" · kennisbank " + _esc(s["kennisbankHitId"]) if s["kennisbankHitId"] else ""}<br>'
            f'<span class="mut">{_esc(s["scoreDetail"])}</span> · <a href="{_esc(doel[s["doelRegelId"]]["url"])}">doelregel in context</a></li>'
            for s in row["suggesties"])
        ot_detail.append(
            f'<details><summary>{_esc(row["id"])} — {_esc(b["locator"]["label"])} ({_esc(row["status"])})</summary>'
            f'<p><b>Bron</b> ({_esc(b["instrument"])}, {_esc(b["statusInBron"])}): '
            f'<a href="{_esc(b["url"])}">regel in de publicatie</a></p>'
            f'<p class="quote">„{_esc(b["tekst"][:900])}{"…" if len(b["tekst"]) > 900 else ""}”</p>'
            f'<p><b>Suggesties</b></p><ul>{sugg_html or "<li>geen — doelregeling eerst uitbreiden (MC-1)</li>"}</ul>'
            + (f'<p><b>needs_human</b>: {_esc(row["needsHumanReden"])}</p>' if row.get("needsHumanReden") else "")
            + f'<p class="mut">toelichting (jurist, MC-7): {_esc(row["toelichting"] or "—")} · reviewTrail: '
              + "; ".join(_esc(t["actie"]) for t in row["reviewTrail"]) + "</p></details>")

    lv = validation["levels"]

    def _cls(v: str) -> str:
        return "ok" if v == "pass" else ("pend" if v == "pending" else "bad")

    lv_rows = "".join(
        '<tr><td>{}</td><td class="{}">{}</td></tr>'.format(k, _cls(v), v) for k, v in lv.items())
    ck_rows = "".join(
        f'<tr><td>{_esc(c["id"])}</td><td>{c["level"]}</td>'
        f'<td class="{"ok" if c["passed"] else "bad"}">{"pass" if c["passed"] else "fail"}</td>'
        f'<td>{_esc(c["evidence"])[:300]}</td></tr>' for c in validation["checks"])
    lims = "\n".join(f"<li>{l}</li>" for l in _LIMITATIONS)

    out = (tpl
           .replace("{{ title }}", _esc(title))
           .replace("{{ subtitle }}", _esc(subtitle))
           .replace("{{ generated }}", _esc(generated))
           .replace("{{ run_id }}", _esc(run_id))
           .replace("{{ verdict_class }}", "ok" if verdict == "pass" else "bad")
           .replace("{{ verdict }}", _esc(verdict))
           .replace("{{ headline_cards }}", cards_html)
           .replace("{{ method_rows }}", method_rows)
           .replace("{{ coverage_rows }}", cov_rows)
           .replace("{{ needs_new_rows }}", nn_rows)
           .replace("{{ portfolio_date }}", _esc(portfolio.get("laatstGeverifieerd", "")))
           .replace("{{ portfolio_total }}", str(portfolio.get("plannenTotaal", "?")))
           .replace("{{ portfolio_vast }}", str(portfolio.get("vastgesteld", "?")))
           .replace("{{ portfolio_tam }}", str(portfolio.get("tamOmgevingsplannen", "?")))
           .replace("{{ kb_summary }}", kb_summary)
           .replace("{{ kb_rows }}", kb_rows)
           .replace("{{ n_rows }}", str(len(omzettabel)))
           .replace("{{ omzettabel_rows }}", "\n".join(ot_rows))
           .replace("{{ omzettabel_detail }}", "\n".join(ot_detail))
           .replace("{{ validation_levels }}", lv_rows)
           .replace("{{ validation_checks }}", ck_rows)
           .replace("{{ limitations }}", lims)
           .replace("{{ footer }}", _esc(footer)))
    Path(out_path).write_text(out, encoding="utf-8")
