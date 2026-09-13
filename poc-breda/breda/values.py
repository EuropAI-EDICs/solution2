"""Waardedefinities van AI in the City 2026 (indestad.ai) — de inhoudelijke index.

Citaten zijn woordelijk overgenomen van <https://www.indestad.ai/en/#programme>
(geraadpleegd 2026-09-13). Programmeonderdelen zijn naamrijk genoemd zodat elke
kaartlaag in het rapport herleidbaar "beantwoordt" aan het congresprogramma.
"""

CONGRESS = "AI in the City 2026 — Creating Real Value (23–25 september 2026, Breda)"
PROGRAMME_URL = "https://www.indestad.ai/en/#programme"

VALUES = {
    "democratic": {
        "label": "Democratische waarde",
        "description": (
            "Waar is de overheid al dicht bij de bewoner — voorzieningen binnen bereik "
            "en afspraken met bewonersinitiatieven (wijkdeals) aanwezig?"
        ),
        "quote": "AI makes government more accessible, faster and more human. Residents "
                 "get answers sooner, are involved earlier in shaping their neighbourhoods.",
        "programmeItems": [
            "Waardethema Democratic value — indestad.ai/en/#programme",
            "Workshop: Residents in the driving seat (Mike de Kreek & Tessa Steenkamp, HvA)",
            "Demo: Autonomous and democratic (o.a. Gert-Jan Zandbergen, gemeente Breda)",
        ],
        "formula": "score = gem( percentiel⁻¹(gem. afstand tot 6 voorzieningen: huisarts, "
                   "supermarkt, basisschool, kinderdagverblijf, bibliotheek, treinstation), "
                   "percentiel(aantal wijkdeals in de buurt) )",
        "sources": ["cbs-buurten-2024", "breda-wijkdeals"],
    },
    "spatial": {
        "label": "Ruimtelijke waarde",
        "description": (
            "Waar ligt de groen-blauwe ruggegraat van de stad — en waar is ruimte voor "
            "klimaatadaptatie bij ruimtelijke ontwikkelingen?"
        ),
        "quote": "A city is more than a dataset. AI strengthens the quality of the city on "
                 "its own terms — it amplifies the genius loci rather than replacing it.",
        "programmeItems": [
            "Waardethema Spatial value — indestad.ai/en/#programme",
            "Workshop: Green Spaces and Water as the backbone of the city (gemeente Breda)",
            "Pitches: Spatial",
        ],
        "formula": "score = gem( percentiel(dekking Hoofdgroenstructuur), "
                   "percentiel⁻¹(afstand tot openbaar groen), "
                   "percentiel(bomen per 100 inwoners) ) + kansenkaart-omschrijving",
        "sources": ["breda-hoofdgroenstructuur", "breda-bomen", "breda-kansenkaart",
                    "cbs-buurten-2024"],
    },
    "economic": {
        "label": "Economische waarde",
        "description": (
            "Waar liggen de rendementen van efficiëntie en energietransitie — onbenut "
            "dakpotentieel voor zonnestroom en bedrijvigheid per km²?"
        ),
        "quote": "AI makes execution more efficient: lower costs, less waste and more "
                 "output with the same capacity.",
        "programmeItems": [
            "Waardethema Economic value — indestad.ai/en/#programme",
            "AI Walk: Energy savings and impact on infrastructure (TNO)",
            "Pitches: Economic",
            "Workshop: From Research to Economic Value — Zürich (Sabine Müller)",
        ],
        "formula": "score = gem( percentiel(onbenut dakpotentieel = (1−zonnestroom%)×"
                   "eengezins%), percentiel(bedrijven per km²) )",
        "sources": ["cbs-buurten-2024"],
    },
    "social": {
        "label": "Sociale waarde",
        "description": (
            "Waar kan klimaatadaptatie de meeste sociale meerwaarde opleveren: hoge "
            "verharding (hitte) gecombineerd met een groot aandeel 65+-jarigen?"
        ),
        "quote": "AI always serves human wellbeing and contributes to a sustainable and "
                 "prosperous future.",
        "programmeItems": [
            "Waardethema Social value — indestad.ai/en/#programme",
            "Workshop: Green Spaces and Water as the backbone of the city (gemeente Breda)",
            "Pitches: Social",
        ],
        "formula": "score = gem( percentiel(% verharding, klimaatportaal), "
                   "percentiel(aandeel 65+) ) — hoger = meer adaptatie-opbrengst",
        "sources": ["breda-verharding", "cbs-buurten-2024"],
    },
    "autonomous": {
        "label": "Autonome waarde",
        "description": (
            "Geen kaartlaag maar het manifest van deze scan zelf: digitale soevereiniteit "
            "is aantoonbaar, niet claimbaar."
        ),
        "quote": "People retain control over AI systems — not the other way around. "
                 "…strengthening Europe's digital sovereignty.",
        "programmeItems": [
            "Waardethema Autonomous value — indestad.ai/en/#programme",
            "Workshop: Sovereignty (City Deal on AI)",
            "AI Walk: Data sovereignty and -continuity (KPN)",
            "Lecture: From European AI strategy to opportunities for your city "
            "(LDT CitiVERSE EDIC)",
            "Lecture: Is your city ready for AI? (OECD & Platform AI & Overheid)",
        ],
    },
}

# Soevereiniteitsmanifest — door de orchestrator per run bewezen (evidence ingevuld).
SOVEREIGNTY_CRITERIA = [
    {
        "criterion": "Alle bronnen zijn publiek en Europees/Nederlands",
        "met": True,
        "evidence": "CBS & PDOK (NL), gemeente Breda (data.breda.nl / geo.breda.nl) — zie brontabel",
    },
    {
        "criterion": "Geen API-sleutels of betaalde toegang",
        "met": True,
        "evidence": "alle endpoints anoniem benaderd (recon 2026-09-13); geen .env, geen tokens",
    },
    {
        "criterion": "Geen afhankelijkheid van één cloud-vendor",
        "met": True,
        "evidence": "deterministische stdlib+shapely-pipeline, lokaal draaibaar; cache maakt "
                    "her-run offline mogelijk",
    },
    {
        "criterion": "Elk cijfer is herleidbaar naar bron met retrievedatum",
        "met": True,
        "evidence": "layers.json + prov.json: per laag serviceUrl, lastChecked, fetchedAt, sha256",
    },
    {
        "criterion": "Ontbrekende data wordt nooit geimputeerd",
        "met": True,
        "evidence": "CBS-sentinels (< -90000) → None + missing-registratie per buurt in "
                    "validation.json",
    },
    {
        "criterion": "Geen LLM in de beslislijn at runtime",
        "met": True,
        "evidence": "volledig deterministisch; LLM-seam (lokale modellen) optioneel en "
                    "gedocumenteerd, uitgeschakeld",
    },
    {
        "criterion": "Herdraaibaar & controleerbaar door derden",
        "met": True,
        "evidence": "python3 poc-breda/run.py her-speelt de scan uit de cache; exit 0 alleen "
                    "bij validatorverdict pass; unittests offline",
    },
]

LIMITATIONS = [
    "CBS 2024-buurtstatistiek is op buurtniveau afgerond/geheimgehouden; kleine buurten "
    "hebben daarom soms ontbrekende inputs (genoteerd per buurt, nooit aangevuld).",
    "De klimaatportaal-lagen (verharding, kansenkaart) zijn wijk-/gebiedsniveau van de "
    "gemeente Breda; de join naar buurten gebeurt via grootste-oppervlakte-overlap.",
    "Onbenut dakpotentieel is een proxy ((1−zonnestroom%)×eengezins-aandeel), geen "
    "3D-dakanalyse (BAG/AHN-variant is vervolgstap).",
    "Bomen-per-buurt telt alleen de gemeentelijke bomenlaag (openbaar groen), niet "
    "privaatgroen.",
    "Hoofdgroenstructuur is 'stedelijk gebied te behouden groen' (v1) — geen totaal "
    "groenbestand.",
    "Scores zijn percentielscores binnen Breda (relatief, niet absoluut); richting per "
    "waarde staat bij de kaartlegioog en in values.py gequoteerd.",
]
