"""Volledigheid van de NL→EN-vertaallaag over de volledige Gent-embed:
elke streng vertaalde tekst moet een vertaling hebben — nieuwe teksten in
pakket of pipeline vallen hierdoor op in plaats van stil NL te blijven."""

import vertaal_gent
from build_simulation import build_gent


def test_alle_embed_teksten_zijn_vertaald():
    gent = build_gent()
    assert len(gent["personas"]) == 11
    assert vertaal_gent.onbekend() == []


def test_bekende_vertalingen_spotcheck():
    assert vertaal_gent.vt("Je vertelt wat je gaat doen") == "You describe what you are going to do"
    assert "reference" in vertaal_gent.vt("Ontheffing LEZ voor zakelijk verkeer ingediend — referentie GENT-ABC123")
    assert vertaal_gent.vt("Uw voertuig (Euro 4) mag de lage-emissiezone niet in. "
                           "Vervang het voertuig of vraag een menselijke beoordeling via Gentinfo.").startswith("Your vehicle")
