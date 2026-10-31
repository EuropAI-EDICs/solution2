"""NL→EN-vertaallaag voor de Gent-embed (presentatielaag van de simulatie).

De engine, het pakket en de run-artefacten blijven Nederlands (taal van de
bron); deze module vertaalt uitsluitend op de presentatiegrens alle teksten
die de simulatie toont, zodat de NL/EN-toggle ook de paneelinhoud dekt.
Volledigheid is testgedekt: `vt(…, streng=True)` verzamelt onvertaalde
teksten in `onbekend()` — de build-test vereist dat die lijst leeg is, zodat
nieuwe teksten in het pakket of de pipeline niet stil in het Nederlands
blijven hangen."""
from __future__ import annotations

import re

DICT: dict[str, str] = {
    # — persona-labels —
    "Sanne — zelfstandig loodgieter, werk aan de Korenmarkt":
        "Sanne — self-employed plumber, working at the Korenmarkt",
    "Ahmed — klusjesman, werk aan het Sint-Pietersplein":
        "Ahmed — handyman, working at the Sint-Pietersplein",
    "Maria — particuliere verhuizing bij station Gent-Sint-Pieters":
        "Maria — private move near Gent-Sint-Pieters station",
    "Fatima — onvolledige situatieschets (gate vraagt aanvulling)":
        "Fatima — incomplete description (gate asks for details)",
    "Jeroen — corrigeert het adres tijdens de contextcheck":
        "Jeroen — corrects the address during the context check",
    "Ellen — weigert het gebruik van haar gegevens":
        "Ellen — refuses the use of her data",
    "Dirk — oud dieselvoertuig (Euro 4), verwacht blokkade":
        "Dirk — old diesel vehicle (Euro 4), expects a block",
    "Wim — wallet op basisniveau (LoA laag), verwacht waarborg-blokkade":
        "Wim — basic-level wallet (low LoA), expects an assurance block",
    "Nadia — geen EUDI-wallet, klassieke authenticatie via ACM/IDM":
        "Nadia — no EUDI wallet, classic authentication via ACM/IDM",
    "Ilse — leververplicht kentekenbewijs niet aan (document-ontbreekt)":
        "Ilse — mandatory registration certificate missing (missing document)",
    "Hanne — weigert de inzending bij H4":
        "Hanne — refuses the submission at H4",
    # — situatieschetsen —
    "Ik ben zelfstandig loodgieter en moet volgende week herstelwerken uitvoeren aan een pand aan de Korenmarkt. Ik kom met mijn bestelwagen.":
        "I am a self-employed plumber and have to carry out repair work at a building on the Korenmarkt next week. I come by van.",
    "Als klusjesman ga ik volgende week een badkamer renoveren aan het Sint-Pietersplein.":
        "As a handyman I will renovate a bathroom at the Sint-Pietersplein next week.",
    "Ik verhuis volgende maand naar het Koningin Maria Hendrikaplein bij het station van Gent en wil weten of ik iets moet regelen voor mijn auto.":
        "Next month I am moving to the Koningin Maria Hendrikaplein near Gent's station and want to know whether I need to arrange anything for my car.",
    "Ik ben ondernemer en moet iets komen doen aan het Sint-Pietersplein.":
        "I am an entrepreneur and have to do some work at the Sint-Pietersplein.",
    "Ik ben ondernemer en ga herstelwerken uitvoeren aan een pand — ik noemde eerst het verkeerde adres bij het station.":
        "I am an entrepreneur and will carry out repair work at a building — I first mentioned the wrong address near the station.",
    "Ik ben ondernemer en moet werken aan het Sint-Pietersplein, maar ik wil mijn gegevens niet delen.":
        "I am an entrepreneur and have to work at the Sint-Pietersplein, but I do not want to share my data.",
    "Ik kom met mijn oude bestelwagen werken aan de Korenmarkt.":
        "I am coming to work at the Korenmarkt with my old van.",
    "Ik ben zelfstandig elektricien en moet herstelwerken uitvoeren aan een pand aan de Korenmarkt. Ik heb alleen een digitale sleutel op basisniveau.":
        "I am a self-employed electrician and have to carry out repair work at a building on the Korenmarkt. I only have a basic-level digital key.",
    "Ik ben zelfstandig schilder en ga herstelwerken uitvoeren aan het Sint-Pietersplein. Een digitale wallet heb ik niet.":
        "I am a self-employed painter and will carry out repair work at the Sint-Pietersplein. I do not have a digital wallet.",
    "Ik ben zelfstandig aannemer en moet volgende week herstelwerken uitvoeren aan een pand aan de Korenmarkt. Mijn kentekenbewijs heb ik nog niet kunnen opzoeken.":
        "I am a self-employed contractor and have to carry out repair work at a building on the Korenmarkt next week. I have not been able to retrieve my registration certificate yet.",
    "Ik ben zelfstandig stukadoor en moet volgende week herstelwerken uitvoeren aan een pand aan de Korenmarkt.":
        "I am a self-employed plasterer and have to carry out repair work at a building on the Korenmarkt next week.",
    # — stap-titels —
    "Je vertelt wat je gaat doen": "You describe what you are going to do",
    "We vragen alleen wat nog niet bekend is": "We only ask what is not known yet",
    "We checken de zone van je adres": "We check the zone of your address",
    "Je checkt de verzamelde feiten": "You check the collected facts",
    "We zeggen welke vergunningen je nodig hebt — en waarom": "We say which permits you need — and why",
    "We leggen het voor aan een medewerker": "We hand it over to a staff member",
    "Je beslist of we je gegevens mogen gebruiken": "You decide whether we may use your data",
    "Je geeft toestemming om je gegevens op te halen": "You give permission to retrieve your data",
    "Je bevestigt wie je bent (EUDI-wallet)": "You confirm who you are (EUDI wallet)",
    "Je bevestigt wie je bent (ACM/IDM)": "You confirm who you are (ACM/IDM)",
    "Je wallet geeft te weinig waarborg — een medewerker helpt verder":
        "Your wallet provides insufficient assurance — a staff member will help you",
    "Een medewerker controleert het mandaat": "A staff member checks the mandate",
    "Je beoordeelt het concept van je aanvraag": "You review the draft of your application",
    "Je bevestigt de inzending van je aanvraag": "You confirm the submission of your application",
    "Je krijgt per aanvraag een ontvangstbewijs": "You receive a receipt per application",
    # — beslistabel-uitleg —
    "Uw adres ligt in de lage-emissiezone en u bent ondernemer: u hebt een LEZ-ontheffing nodig om met een voertuig het centrum in te rijden.":
        "Your address lies in the low-emission zone and you are an entrepreneur: you need a LEZ exemption to drive a vehicle into the centre.",
    "Het adres ligt in het autovrije gebied: voor laden en lossen met een voertuig geldt een ontheffing autovrij gebied.":
        "The address lies in the car-free area: loading and unloading with a vehicle requires a car-free-area exemption.",
    "Het adres ligt buiten de lage-emissiezone en buiten het autovrije gebied: voor dit adres is geen voertuigtoegangsvergunning nodig.":
        "The address lies outside the low-emission zone and outside the car-free area: no vehicle-access permit is needed for this address.",
    # — vaste meldingen en vervolgregels —
    "Controleer of uw diesel Euro 5 een geregistreerd roetfilter heeft; anders geldt de ontheffing niet.":
        "Check whether your Euro 5 diesel has a registered soot filter; otherwise the exemption does not apply.",
    "Virusscan niet schoon — bestand staat in quarantaine; lever opnieuw aan.":
        "Virus scan not clean — the file is quarantined; please supply it again.",
    "Mandaat niet geverifieerd: overname door een medewerker (Gentinfo) voor de mandatencontrole.":
        "Mandate not verified: taken over by a staff member (Gentinfo) for the mandate check.",
    "geen regel van toepassing (unknownPolicy: escalate)": "no rule applies (unknownPolicy: escalate)",
    "Geen aanvragen om in te dienen — je kreeg alleen informatie.":
        "No applications to submit — you only received information.",
    "Je weigerde het gebruik van je gegevens — er is niets opgehaald of ingediend.":
        "You refused the use of your data — nothing was retrieved or submitted.",
    "Geen regel van toepassing: een medewerker van Gentinfo beoordeelt je situatie verder.":
        "No rule applies: a Gentinfo staff member will assess your situation further.",
    "Je bevestigde de inzending niet — er is niets ingediend.":
        "You did not confirm the submission — nothing was submitted.",
    "Volg de status van je aanvragen via Gentinfo.": "Follow the status of your applications via Gentinfo.",
    # — diensttitels, documenttitels, vragen, doelbindingen —
    "Ontheffing LEZ voor zakelijk verkeer": "LEZ exemption for commercial traffic",
    "Ontheffing autovrij gebied (laden/lossen)": "Car-free-area exemption (loading/unloading)",
    "Informatie over de LEZ in Gent": "Information about the LEZ in Ghent",
    "Kentekenbewijs van het voertuig": "Vehicle registration certificate",
    "Bent u particulier, ondernemer of organisatie?": "Are you a private individual, entrepreneur or organisation?",
    "Op welk adres gaat u aan de slag?": "At which address will you be working?",
    "Voor welke periode heeft u toegang nodig?": "For which period do you need access?",
    "Wat gaat u precies doen?": "What exactly will you be doing?",
    "beoordelen van het recht op een LEZ-ontheffing": "assessing entitlement to a LEZ exemption",
    "vaststellen of u namens een ander mag handelen": "establishing whether you may act on someone's behalf",
    # — kaart-bronregel —
    "route & kaart: OSRM + Nominatim op OpenStreetMap (ODbL) · zones: Stad Gent open data (Modellicentie Gratis Hergebruik) · bedrijfsadres: VKBO/KBO open register · innames: GIPOD-mock (productiepad: GIPOD-LDES)":
        "route & map: OSRM + Nominatim on OpenStreetMap (ODbL) · zones: City of Ghent open data (Free Re-use Licence) · company address: VKBO/KBO open register · hindrances: GIPOD mock (production path: GIPOD LDES)",
}

_PATROON = type("_PATROON", (), {})


def _p(nl: str, en) -> _PATROON:
    return (re.compile(nl), en)


PATRONEN = [
    _p(r"Uw voertuig \(([^)]+)\) mag de lage-emissiezone niet in\. Vervang het voertuig of vraag een menselijke beoordeling via Gentinfo\.",
       lambda g: f"Your vehicle ({g[0]}) is not allowed into the low-emission zone. Replace the vehicle or request a human assessment via Gentinfo."),
    _p(r"Ontbrekend document: (.+)\.",
       lambda g: f"Missing document: {vt(g[0])}."),
    _p(r"Bestandstype niet toegestaan \(([^)]*)\): gebruik pdf, jpg of png\.",
       lambda g: f"File type not allowed ({g[0]}): use pdf, jpg or png."),
    _p(r"Bestand te groot \((\d+) kB; max (\d+) kB\)\.",
       lambda g: f"File too large ({g[0]} kB; max {g[1]} kB)."),
    _p(r"Waarborg onvoldoende: voor deze aanvraag is minimaal niveau '(\w+)' nodig, uw wallet gaf '(\w+)'\. Een medewerker van Gentinfo helpt u verder\.",
       lambda g: f"Insufficient assurance: this application requires at least level '{g[0]}', your wallet provided '{g[1]}'. A Gentinfo staff member will help you."),
    _p(r"(.+) ingediend — referentie (GENT-[A-Z0-9]+)",
       lambda g: f"{vt(g[0])} submitted — reference {g[1]}"),
    _p(r"(.+) — concept \+ bewijzen",
       lambda g: f"{vt(g[0])} — draft + evidence"),
    _p(r"(.+) — (gereed|gereed-met-waarschuwing|blokkade)",
       lambda g: f"{vt(g[0])} — {VT_STATUS.get(g[1], g[1])}"),
    _p(r"(magda:[\w:]+) — (.+)",
       lambda g: f"{g[0]} — {vt(g[1])}"),
    _p(r"(.+) \((grondwerk|evenement), tot ([\d-]+)\)",
       lambda g: f"{g[0]} ({VT_TYPE.get(g[1], g[1])}, until {g[2]})"),
]

VT_STATUS = {"gereed": "complete", "gereed-met-waarschuwing": "complete with warning",
             "blokkade": "blocked", "geweigerd": "refused", "escalatie": "escalation"}
VT_TYPE = {"grondwerk": "roadworks", "evenement": "event"}

_onbekend: set[str] = set()


def vt(tekst: str | None, streng: bool = True) -> str | None:
    """Vertaal een NL-tekst naar EN; bij `streng=False` (soft lacunes zoals
    dataUsed-regels met inline waarden) worden onvertaalde teksten stil
    doorgelaten, anders worden ze verzameld voor de volledigheidstest."""
    if tekst is None:
        return None
    if tekst in DICT:
        return DICT[tekst]
    for patroon, vervang in PATRONEN:
        match = patroon.fullmatch(tekst)
        if match:
            return vervang(match.groups())
    if streng:
        _onbekend.add(tekst)
    return tekst


def onbekend() -> list[str]:
    return sorted(_onbekend)
