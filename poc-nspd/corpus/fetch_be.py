"""Provenance-script voor corpus/be/ (RUP/Gewestplan/VCRO-documenten, taak 3).

Standaard: verify — controleert sha256 van corpus/be/* tegen META.json (geen netwerk).
Met --fetch: haalt de gepinde bronnen opnieuw op, converteert PDF's naar .txt en
herschrijft META.json (snapshot-pin). Let op: de VCRO-printversie (codex.vlaanderen.be
levert HTML) wordt lokaal naar PDF gerenderd met een headless browser; die render is
niet byte-reproduceerbaar, dus een --fetch-run kan nieuwe sha256's opleveren.

Geen pytest (netwerk / bestandsmutatie). Run: python3 corpus/fetch_be.py [--fetch]
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
from datetime import date
from pathlib import Path

CORPUS = Path(__file__).resolve().parent / "be"
META = CORPUS / "META.json"

BRONNEN = [
    {
        "id": "rup-zeehaven-gent-fase2",
        "instrumentType": "rup-be",
        "titel": "gewestelijk ruimtelijk uitvoeringsplan 'afbakening zeehavengebied Gent - fase 2' — Bijlage II: stedenbouwkundige voorschriften",
        "bronUrl": "https://download.dsi.omgeving.vlaanderen.be/be.vl.omg.dsi.stukonderdeel.RUP_02000_212_00358_00001.BG.3.Dossierstuk.SV.1_1",
        "bestand": "rup-zeehaven-gent-fase2.pdf",
    },
    {
        "id": "rup-zeehaven-gent-papierbedrijf",
        "instrumentType": "rup-be",
        "titel": "gewestelijk ruimtelijk uitvoeringsplan 'zeehavengebied Gent — uitbreiding papierproducerend bedrijf' — Bijlage III: stedenbouwkundige voorschriften",
        "bronUrl": "https://download.dsi.omgeving.vlaanderen.be/be.vl.omg.dsi.stukonderdeel.RUP_02000_212_00008_00001.BG.3.Dossierstuk.SV.1_1",
        "bestand": "rup-zeehaven-gent-papierbedrijf.pdf",
    },
    {
        "id": "gewestplan-voorschriften",
        "instrumentType": "gewestplan-be",
        "titel": "Digitale geactualiseerde gewestplannen van Vlaanderen, vector — Bijlage 3: teksten aanvullende stedenbouwkundige voorschriften (per gewestplan; incl. gewestplan Gentse en Kanaalzone 08), toestand 1 januari 2002",
        "bronUrl": "https://omgeving.vlaanderen.be/sites/default/files/2021-11/bijlage_3_aanvullende_voorschriften_stedenbouwkundige%20gewestplannen.pdf",
        "bestand": "gewestplan.pdf",
    },
    {
        "id": "vcro",
        "instrumentType": "vcro-be",
        "titel": "Gecodificeerd Decreet Vlaamse Codex Ruimtelijke Ordening (VCRO) — geconsolideerde versie geldend op 14/10/2026",
        "bronUrl": "https://codex.vlaanderen.be/PrintDocument.ashx?id=1018245",
        "bestand": "vcro.pdf",
        "bronIsHtml": True,
    },
]

UA = {"User-Agent": "nLDT-toolbox-poc-nspd/1.0"}


def _headless_browser() -> str | None:
    kandidaten = [
        "chromium", "chromium-browser", "google-chrome",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ]
    for k in kandidaten:
        pad = shutil.which(k) or (k if k.startswith("/") and Path(k).exists() else None)
        if pad:
            return pad
    return None


def _download(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def _html_naar_pdf(html: bytes, doel: Path) -> None:
    tmp_html = CORPUS / "_vcro_print.html"
    tmp_html.write_bytes(html)
    browser = _headless_browser()
    if not browser:
        tmp_html.unlink(missing_ok=True)
        raise SystemExit(
            "geen headless browser gevonden voor VCRO-render; "
            "installeer Chrome/Chromium/Brave of render de printversie handmatig"
        )
    subprocess.run(
        [browser, "--headless", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={doel}", tmp_html.as_uri()],
        check=True, capture_output=True, timeout=300,
    )
    tmp_html.unlink(missing_ok=True)


def _pdf_naar_txt(pdf: Path) -> None:
    from pypdf import PdfReader  # fetch-only dependency

    reader = PdfReader(pdf)
    txt = "\n".join((p.extract_text() or "") for p in reader.pages)
    pdf.with_suffix(".txt").write_text(txt, encoding="utf-8")


def verify() -> int:
    meta = json.loads(META.read_text(encoding="utf-8"))
    ok = True
    for ins in meta["instrumenten"]:
        bestand = CORPUS / ins["bestand"]
        sha = hashlib.sha256(bestand.read_bytes()).hexdigest()
        status = "OK" if sha == ins["sha256"] else "AFWIJKEND"
        if sha != ins["sha256"]:
            ok = False
        print(f"{status:9s} {ins['bestand']} {sha}")
    return 0 if ok else 1


def fetch() -> int:
    instrumenten = []
    for bron in BRONNEN:
        doel = CORPUS / bron["bestand"]
        raw = _download(bron["bronUrl"])
        if bron.get("bronIsHtml"):
            _html_naar_pdf(raw, doel)
        else:
            doel.write_bytes(raw)
        _pdf_naar_txt(doel)
        sha = hashlib.sha256(doel.read_bytes()).hexdigest()
        print(f"gedownload {bron['bestand']} sha256={sha}")
        instrumenten.append({
            "id": bron["id"],
            "instrumentType": bron["instrumentType"],
            "titel": bron["titel"],
            "bronUrl": bron["bronUrl"],
            "bestand": bron["bestand"],
            "sha256": sha,
            "retrieved": date.today().isoformat(),
        })
    META.write_text(
        json.dumps({"instrumenten": instrumenten}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    print(f"META.json herschreven ({len(instrumenten)} instrumenten)")
    return 0


def main() -> int:
    if "--fetch" in sys.argv[1:]:
        return fetch()
    if not META.is_file():
        print("META.json ontbreekt — draai eerst --fetch", file=sys.stderr)
        return 1
    return verify()


if __name__ == "__main__":
    raise SystemExit(main())
