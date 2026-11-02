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
    # — burgerpakket GT-VERH-01: persona-labels —
    "Lisa — verhuist naar een appartement aan de Veldstraat":
        "Lisa — moves to an apartment on the Veldstraat",
    "Tomas — verhuist naar Gentbrugge, geen parkeerregeling":
        "Tomas — moves to Gentbrugge, no parking scheme",
    "Farah — er staat al een bewonersvergunning op haar adres":
        "Farah — a residents' permit already exists at her address",
    "Noor — heeft een eigen garage bij haar nieuwe woning":
        "Noor — has her own garage at her new home",
    "Emma — geen voertuig op haar naam (verwacht blokkade)":
        "Emma — no vehicle registered in her name (expects a block)",
    "Yana — corrigeert het adres tijdens de contextcheck":
        "Yana — corrects the address during the context check",
    "Robrecht — weigert de inzending bij H4":
        "Robrecht — refuses the submission at H4",
    # — kotpakket GT-KOT-01: persona-labels —
    "Wouter — verhuurt een kamer in zijn woning aan de Overpoort":
        "Wouter — rents out a room in his house near the Overpoort",
    "Saartje — haar kotadres staat al als gemeld kot genoteerd":
        "Saartje — her student-room address is already registered as a notified kot",
    "Gregory — zet zijn woning om naar twee koten":
        "Gregory — converts his house into two student rooms",
    "Lea — meldt een studentenresidentie":
        "Lea — notifies a student residence",
    "Milan — corrigeert het kotadres tijdens de contextcheck":
        "Milan — corrects the student-room address during the context check",
    "Karel — weigert de inzending bij H4":
        "Karel — refuses the submission at H4",
    # — eventpakket GT-EVT-01: persona-labels —
    "Fien — organiseert een straatfeest, ruim op tijd aangevraagd":
        "Fien — organizes a street party, applied well in advance",
    "Mo — vraagt het feest aan met kerst, net op tijd":
        "Mo — applies for the party at Christmas, just in time",
    "Lorne — wil over drie weken een feest, te laat voor online aanvraag":
        "Lorne — wants a party in three weeks, too late to apply online",
    "Nathalie — groot evenement, verwacht risicoanalyse":
        "Nathalie — large event, expects a risk analysis",
    "Gil — wil een pleintje bezetten op de Botermarkt, in de feestenzone":
        "Gil — wants to occupy a square on the Botermarkt, in the festival zone",
    "Jef — weigert de inzending bij H4":
        "Jef — refuses the submission at H4",
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
    # — burgerpakket GT-VERH-01: situatieschetsen —
    "Ik verhuis volgende maand naar een appartement aan de Veldstraat en wil weten wat ik rond parkeren en afval moet regelen.":
        "Next month I am moving to an apartment on the Veldstraat and want to know what to arrange about parking and waste.",
    "Ik verhuis naar een flat aan de Ottergemsesteenweg-Zuid in Gentbrugge en wil weten wanneer mijn afval wordt opgehaald.":
        "I am moving to a flat on the Ottergemsesteenweg-Zuid in Gentbrugge and want to know when my waste is collected.",
    "Ik verhuis in met mijn partner aan de Veldstraat; hij heeft daar al een bewonersvergunning voor zijn auto.":
        "I am moving in with my partner on the Veldstraat; he already has a residents' permit there for his car.",
    "Ik verhuis naar een huis aan de Veldstraat met eigen garage, en overweeg toch een bewonersvergunning voor een tweede auto.":
        "I am moving to a house on the Veldstraat with its own garage, and am still considering a residents' permit for a second car.",
    "Ik verhuis naar de Veldstraat en wil een bewonersvergunning aanvragen, al staat er nog geen auto op mijn naam.":
        "I am moving to the Veldstraat and want to apply for a residents' permit, although no car is registered in my name yet.",
    "Ik verhuis binnen Gent — ik noemde eerst een adres bij het Sint-Pietersplein, maar het wordt de Veldstraat.":
        "I am moving within Ghent — I first mentioned an address near the Sint-Pietersplein, but it will be the Veldstraat.",
    "Ik verhuis naar een loft aan de Veldstraat en wil een bewonersvergunning aanvragen, maar ik twijfel nog.":
        "I am moving to a loft on the Veldstraat and want to apply for a residents' permit, but I am still hesitating.",
    # — kotpakket GT-KOT-01: situatieschetsen —
    "Ik wil vanaf volgend academiejaar een kamer in mijn huis aan de Overpoortstraat aan een student verhuren.":
        "From next academic year I want to rent out a room in my house on the Overpoortstraat to a student.",
    "Ik verhuur al een kot aan de Overpoortstraat en wil mijn melding actualiseren.":
        "I already rent out a student room on the Overpoortstraat and want to update my notification.",
    "Ik wil mijn woning aan de Overpoortstraat omzetten naar twee aparte koten en die dan verhuren.":
        "I want to convert my house on the Overpoortstraat into two separate student rooms and then rent them out.",
    "Ik beheer een studentenresidentie aan de Overpoortstraat en wil de kamers melden.":
        "I manage a student residence on the Overpoortstraat and want to notify the rooms.",
    "Ik ga een kot verhuren — ik noemde eerst het verkeerde adres in Gentbrugge, het wordt de Overpoortstraat.":
        "I am going to rent out a student room — I first mentioned the wrong address in Gentbrugge, it will be the Overpoortstraat.",
    "Ik wil een studio aan de Overpoortstraat als kot melden, maar twijfel nog over de belasting.":
        "I want to notify a studio on the Overpoortstraat as a student room, but I am still hesitating about the tax.",
    # — eventpakket GT-EVT-01: situatieschetsen —
    "Ik wil volgend najaar een eendaags straatfeest aan de Veldstraat organiseren voor onze wijk.":
        "Next autumn I want to organize a one-day street party on the Veldstraat for our neighbourhood.",
    "Ik wil net voor kerst nog een klein buurtfeest aan de Veldstraat houden.":
        "Just before Christmas I still want to hold a small neighbourhood party on the Veldstraat.",
    "Ik wil eind november een eendaags feest aan de Veldstraat organiseren — de datum is al lang gepland.":
        "At the end of November I want to organize a one-day party on the Veldstraat — the date has long been planned.",
    "Onze vereniging wil volgend voorjaar een groot eendaags evenement aan de Veldstraat organiseren.":
        "Next spring our association wants to organize a large one-day event on the Veldstraat.",
    "Ik wil tijdens de zomer van 2027 een klein evenement op de Botermarkt bij het Stadhuis houden.":
        "In the summer of 2027 I want to hold a small event on the Botermarkt near the City Hall.",
    "Ik wil een eendaags straatevenement aan de Veldstraat organiseren, maar twijfel nog over de verzekering.":
        "I want to organize a one-day street event on the Veldstraat, but I am still hesitating about the insurance.",
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
    "We halen de afvalkalender van je straat op": "We fetch the collection calendar for your street",
    # — beslistabel-uitleg —
    "Uw adres ligt in de lage-emissiezone en u bent ondernemer: u hebt een LEZ-ontheffing nodig om met een voertuig het centrum in te rijden.":
        "Your address lies in the low-emission zone and you are an entrepreneur: you need a LEZ exemption to drive a vehicle into the centre.",
    "Het adres ligt in het autovrije gebied: voor laden en lossen met een voertuig geldt een ontheffing autovrij gebied.":
        "The address lies in the car-free area: loading and unloading with a vehicle requires a car-free-area exemption.",
    "Het adres ligt buiten de lage-emissiezone en buiten het autovrije gebied: voor dit adres is geen voertuigtoegangsvergunning nodig.":
        "The address lies outside the low-emission zone and outside the car-free area: no vehicle-access permit is needed for this address.",
    # — burgerpakket GT-VERH-01: beslistabel-uitleg —
    "Uw nieuwe adres ligt in een bewonerszone: u komt in aanmerking voor een bewonersvergunning (eerste gratis per gezin, tweede €300/jaar), gekoppeld aan één kenteken.":
        "Your new address lies in a residents' zone: you qualify for a residents' permit (first one free per household, second €300/year), linked to one number plate.",
    "Uw adres ligt buiten een bewonerszone maar binnen een parkeertariefzone: parkeren gebeurt tegen het geldende tarief; een bewonersvergunning is hier niet mogelijk.":
        "Your address lies outside a residents' zone but inside a paid-parking zone: parking is at the applicable rate; a residents' permit is not possible here.",
    "Uw adres ligt buiten bewoners- en tariefzone: er geldt geen bijzondere parkeerregeling voor uw adres.":
        "Your address lies outside the residents' and paid-parking zones: no special parking scheme applies to your address.",
    "Uw nieuwe adres ligt in de lage-emissiezone: met een oudere wagen heeft u een dagenpas nodig.":
        "Your new address lies in the low-emission zone: with an older vehicle you need a day pass.",
    # — kotpakket GT-KOT-01: beslistabel-uitleg —
    "U gaat een kot verhuren: meld het pand en de kamers via het koteloket — de melding wordt gecontroleerd vóór publicatie.":
        "You are going to rent out a student room: notify the building and the rooms via the kot desk — the notification is checked before publication.",
    "U zet een woning om naar kot(s): daarvoor is een omgevingsvergunning nodig vóór de verhuur.":
        "You are converting a home into student room(s): this requires an environmental permit before the rental.",
    "Uw adres valt buiten de kotzone-indeling: het koteloket beoordeelt de melding handmatig — u krijgt alleen de algemene informatie.":
        "Your address falls outside the kot-zone layout: the kot desk assesses the notification manually — you only receive the general information.",
    # — eventpakket GT-EVT-01: beslistabel-uitleg —
    "Uw evenement ligt ruim genoeg vooruit: u kunt de bezetting van publieke ruimte online aanvragen.":
        "Your event is far enough ahead: you can apply online to occupy public space.",
    "Uw evenement nadert: de aanvraag kan nog online, maar de beoordeling wordt krap — de waarschuwing verschijnt in uw aanvraag.":
        "Your event is approaching: the application can still be filed online, but assessment becomes tight — the warning appears in your application.",
    "Uw evenement is minder dan 30 dagen verwijderd: de online aanvraag wordt geblokkeerd en een medewerker beoordeelt of er nog iets mogelijk is.":
        "Your event is less than 30 days away: the online application is blocked and a staff member assesses whether anything is still possible.",
    "De opgegeven datum ligt in het verleden: de aanvraag wordt geblokkeerd tot de datum klopt.":
        "The date given lies in the past: the application is blocked until the date is correct.",
    "Uw locatie ligt in de lage-emissiezone: informeer bezoekers en leveranciers over de dagenpas.":
        "Your location lies in the low-emission zone: inform visitors and suppliers about the day pass.",
    "Uw locatie valt buiten het online aanvraaggebied van de stad: een medewerker van Gentinfo bekijkt met u wat wel kan.":
        "Your location falls outside the city's online application area: a Gentinfo staff member will look with you at what is possible.",
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
    # — burgerpakket GT-VERH-01: vaste meldingen —
    "Er staat al een bewonersvergunning op dit adres: dit wordt de tweede vergunning (€300/jaar, tarief 2026).":
        "A residents' permit already exists at this address: this will be the second permit (€300/year, 2026 rate).",
    "U heeft eigen parkeergelegenheid: u komt hooguit in aanmerking voor een tijdelijke vergunning. De beoordeling gebeurt door de dienst Parkeren.":
        "You have your own parking facility: you qualify at most for a temporary permit. The assessment is done by the Parking department.",
    # — kotpakket GT-KOT-01: vaste meldingen —
    "Dit adres staat al als gemeld kot genoteerd: beheer uw melding via het koteloket.":
        "This address is already registered as a notified kot: manage your notification via the kot desk.",
    "Een omzettingsvergunning is nodig vóór u het kot verhuurt; vraag die eerst aan (zie de informatie over de omgevingsvergunning).":
        "A conversion permit is required before you rent out the student room; apply for it first (see the environmental-permit information).",
    "Grote studentenresidenties krijgen een voorbehandeling via kot@stad.gent vóór de online melding.":
        "Large student residences receive pre-processing via kot@stad.gent before the online notification.",
    # — eventpakket GT-EVT-01: vaste meldingen —
    "Uw evenement is minder dan 90 dagen verwijderd: de beoordeling wordt krap — vroeg insturen is nodig.":
        "Your event is less than 90 days away: assessment becomes tight — submitting early is necessary.",
    "Uw evenement is minder dan 30 dagen verwijderd: online aanvragen kan niet meer — een medewerker van Gentinfo beoordeelt of het nog kan.":
        "Your event is less than 30 days away: applying online is no longer possible — a Gentinfo staff member assesses whether it can still happen.",
    "De datum van uw evenement ligt in het verleden — controleer de datum of neem contact op met Gentinfo.":
        "Your event's date lies in the past — check the date or contact Gentinfo.",
    "Groot evenement: een risicoanalyse en veiligheidsplan zijn vereist — de dienst Evenementen neemt contact op.":
        "Large event: a risk analysis and safety plan are required — the Events department will contact you.",
    "Uw locatie ligt in de Gentse Feesten-zone (demovereenvoudiging: straatgebonden, niet datumgebonden): coördineer met de feestencoördinator.":
        "Your location lies in the Ghent Festival zone (demo simplification: street-based, not date-based): coordinate with the festival coordinator.",
    # — diensttitels, documenttitels, vragen, doelbindingen —
    "Ontheffing LEZ voor zakelijk verkeer": "LEZ exemption for commercial traffic",
    "Ontheffing autovrij gebied (laden/lossen)": "Car-free-area exemption (loading/unloading)",
    "Informatie over de LEZ in Gent": "Information about the LEZ in Ghent",
    # — burgerpakket GT-VERH-01: diensttitels, vragen, doelbindingen —
    "Bewonersvergunning parkeren (1e of 2e)": "Residents' parking permit (1st or 2nd)",
    "Afvalophaling op uw nieuwe adres (IVAGO)": "Waste collection at your new address (IVAGO)",
    "Parkeren tegen tarief in uw buurt": "Paid parking in your area",
    "Lage-emissiezone: dagenpas bij ouder voertuig": "Low-emission zone: day pass for older vehicles",
    # — kotpakket GT-KOT-01: diensttitels, vragen, doelbinding —
    "Kot melden via het koteloket": "Notify a student room via the kot desk",
    "Omgevingsvergunning bij omzetten naar kot": "Environmental permit when converting into a student room",
    "Conformiteitsattest voor uw kot": "Certificate of conformity for your student room",
    "Kotbelasting vanaf 2027": "Student-room tax from 2027",
    "Afvalophaling op uw kotadres (IVAGO)": "Waste collection at your student-room address (IVAGO)",
    "Op welk adres ligt het kot?": "At which address is the student room located?",
    "Zet u een bestaande woning om naar kot(s)?": "Are you converting an existing home into student room(s)?",
    "Wat voor studentenhuisvesting verhuurt u?": "What type of student housing are you renting out?",
    "vaststellen of dit adres al als gemeld kot genoteerd staat":
        "establishing whether this address is already registered as a notified kot",
    # — eventpakket GT-EVT-01: diensttitels en vragen —
    "Evenement op publieke ruimte aanvragen": "Apply to occupy public space for an event",
    "Aanlooptijden voor evenementenaanvragen": "Lead times for event applications",
    "Gentse Feesten: bezette locaties": "Ghent Festival: occupied locations",
    "Lage-emissiezone: bezoekers en leveranciers": "Low-emission zone: visitors and suppliers",
    "Op welke locatie organiseert u het evenement?": "At which location are you organizing the event?",
    "Op welke datum is het evenement (jjjj-mm-dd)?": "On which date is the event (yyyy-mm-dd)?",
    "Wat voor evenement organiseert u?": "What kind of event are you organizing?",
    "Bezet u daarbij publieke ruimte (straat, plein, park)?": "Will you occupy public space (street, square, park)?",
    "bron: Gentse Feesten 2026 (open data, demo-selectie)":
        "source: Ghent Festival 2026 (open data, demo selection)",
    # — kotpakket GT-KOT-01: kaart-bronregel —
    "kotzones: Stad Gent open data (Modellicentie Gratis Hergebruik) · gemeentegrens: OSM/Nominatim (ODbL)":
        "kot zones: City of Ghent open data (Free Re-use Licence) · city boundary: OSM/Nominatim (ODbL)",
    "lez: Stad Gent open data (Modellicentie Gratis Hergebruik) · gemeentegrens: OSM/Nominatim (ODbL)":
        "LEZ: City of Ghent open data (Free Re-use Licence) · city boundary: OSM/Nominatim (ODbL)",
    "Naar welk adres verhuist u?": "Which address are you moving to?",
    "Heeft u eigen parkeergelegenheid (garage of oprit) bij uw nieuwe adres?":
        "Do you have your own parking facility (garage or driveway) at your new address?",
    "vaststellen van het kenteken voor de bewonersvergunning":
        "establishing the number plate for the residents' permit",
    "vaststellen of er al een bewonersvergunning op het adres geldt":
        "establishing whether a residents' permit already applies at the address",
    # — burgerpakket GT-VERH-01: kaart-bronregel —
    "zones & kalender: Stad Gent open data (Modellicentie Gratis Hergebruik) · gemeentegrens: OSM/Nominatim (ODbL)":
        "zones & calendar: City of Ghent open data (Free Re-use Licence) · city boundary: OSM/Nominatim (ODbL)",
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
    _p(r"Ontbrekend gegeven: (.+) — vraag het aan bij de bronhouder\.",
       lambda g: f"Missing data: {g[0]} — request it from the data holder."),
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
