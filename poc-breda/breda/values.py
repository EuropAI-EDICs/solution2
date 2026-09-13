"""Value definitions of AI in the City 2026 (indestad.ai) — the content index.

Quotes are taken verbatim from <https://www.indestad.ai/en/#programme>
(consulted 2026-09-13). Programme items are named explicitly so every map
layer in the report traces to a congress programme item. Output language:
English (congress edition); neighbourhood and district names stay Dutch —
they are data, not interface.
"""

CONGRESS = "AI in the City 2026 — Creating Real Value (23–25 September 2026, Breda)"
PROGRAMME_URL = "https://www.indestad.ai/en/#programme"

VALUES = {
    "democratic": {
        "label": "Democratic value",
        "description": (
            "Where is government already close to residents — services within "
            "reach and resident agreements (neighbourhood deals, wijkdeals) present?"
        ),
        "quote": "AI makes government more accessible, faster and more human. Residents "
                 "get answers sooner, are involved earlier in shaping their neighbourhoods.",
        "programmeItems": [
            "Value theme Democratic value — indestad.ai/en/#programme",
            "Workshop: Residents in the driving seat (Mike de Kreek & Tessa Steenkamp, HvA)",
            "Demo: Autonomous and democratic (a.o. Gert-Jan Zandbergen, city of Breda)",
        ],
        "formula": "score = mean( percentile⁻¹(mean distance to 6 services: GP, "
                   "supermarket, primary school, childcare, library, train station), "
                   "percentile(neighbourhood-deal count in the neighbourhood) )",
        "sources": ["cbs-buurten-2024", "breda-wijkdeals"],
    },
    "spatial": {
        "label": "Spatial value",
        "description": (
            "Where does the city's green-blue backbone lie — and where is room for "
            "climate adaptation in spatial development?"
        ),
        "quote": "A city is more than a dataset. AI strengthens the quality of the city on "
                 "its own terms — it amplifies the genius loci rather than replacing it.",
        "programmeItems": [
            "Value theme Spatial value — indestad.ai/en/#programme",
            "Workshop: Green Spaces and Water as the backbone of the city (municipality of Breda)",
            "Pitches: Spatial",
        ],
        "formula": "score = mean( percentile(green-backbone coverage), "
                   "percentile⁻¹(distance to public green), "
                   "percentile(trees per 100 residents) ) + climate-opportunity map notes",
        "sources": ["breda-hoofdgroenstructuur", "breda-bomen", "breda-kansenkaart",
                    "cbs-buurten-2024"],
    },
    "economic": {
        "label": "Economic value",
        "description": (
            "Where are the returns on efficiency and energy transition — unused roof "
            "potential for solar and business density per km²?"
        ),
        "quote": "AI makes execution more efficient: lower costs, less waste and more "
                 "output with the same capacity.",
        "programmeItems": [
            "Value theme Economic value — indestad.ai/en/#programme",
            "AI Walk: Energy savings and impact on infrastructure (TNO)",
            "Pitches: Economic",
            "Workshop: From Research to Economic Value — Zürich (Sabine Müller)",
        ],
        "formula": "score = mean( percentile(unused roof potential = (1−solar%)×"
                   "single-family share), percentile(companies per km²) )",
        "sources": ["cbs-buurten-2024"],
    },
    "social": {
        "label": "Social value",
        "description": (
            "Where can climate adaptation yield the most social value: high paved "
            "share (heat) combined with a large share of residents aged 65+?"
        ),
        "quote": "AI always serves human wellbeing and contributes to a sustainable and "
                 "prosperous future.",
        "programmeItems": [
            "Value theme Social value — indestad.ai/en/#programme",
            "Workshop: Green Spaces and Water as the backbone of the city (municipality of Breda)",
            "Pitches: Social",
        ],
        "formula": "score = mean( percentile(paved share, climate portal), "
                   "percentile(65+ share) ) — higher = more adaptation payoff",
        "sources": ["breda-verharding", "cbs-buurten-2024"],
    },
    "autonomous": {
        "label": "Autonomous value",
        "description": (
            "Not a map layer but this scan's own manifest: digital sovereignty is "
            "demonstrable, not claimable."
        ),
        "quote": "People retain control over AI systems — not the other way around. "
                 "…strengthening Europe's digital sovereignty.",
        "programmeItems": [
            "Value theme Autonomous value — indestad.ai/en/#programme",
            "Workshop: Sovereignty (City Deal on AI)",
            "AI Walk: Data sovereignty and -continuity (KPN)",
            "Lecture: From European AI strategy to opportunities for your city "
            "(LDT CitiVERSE EDIC)",
            "Lecture: Is your city ready for AI? (OECD & Platform AI & Overheid)",
        ],
    },
}

# Sovereignty manifest — proven per run by the orchestrator (evidence filled in).
SOVEREIGNTY_CRITERIA = [
    {
        "criterion": "All sources are public and European/Dutch",
        "met": True,
        "evidence": "CBS & PDOK (NL), municipality of Breda (data.breda.nl / geo.breda.nl) — see the source table",
    },
    {
        "criterion": "No API keys or paid access",
        "met": True,
        "evidence": "all endpoints accessed anonymously (recon 2026-09-13); no .env, no tokens",
    },
    {
        "criterion": "No dependence on a single cloud vendor",
        "met": True,
        "evidence": "deterministic stdlib+shapely pipeline, runs locally; the cache "
                    "enables offline re-runs",
    },
    {
        "criterion": "Every number traces to a source with a retrieval date",
        "met": True,
        "evidence": "layers.json + prov.json: per layer serviceUrl, lastChecked, fetchedAt, sha256",
    },
    {
        "criterion": "Missing data is never imputed",
        "met": True,
        "evidence": "CBS sentinels (< -90000) → None + per-neighbourhood missing-input "
                    "registration in validation.json",
    },
    {
        "criterion": "No LLM in the decision line at runtime",
        "met": True,
        "evidence": "fully deterministic; the LLM seam (local models) is optional and "
                    "documented, switched off",
    },
    {
        "criterion": "Re-runnable & verifiable by third parties",
        "met": True,
        "evidence": "python3 poc-breda/run.py replays the scan from cache; exit 0 only "
                    "on validator verdict pass; offline unit tests",
    },
]

LIMITATIONS = [
    "CBS 2024 neighbourhood statistics are rounded/suppressed; small neighbourhoods "
    "therefore sometimes lack inputs (recorded per neighbourhood, never imputed).",
    "The climate-portal layers (paved share, opportunity map) are ward/area level from "
    "the municipality of Breda; joined to neighbourhoods via largest-area overlap.",
    "Unused roof potential is a proxy ((1−solar%)×single-family share), not a 3D roof "
    "analysis (a BAG/AHN variant is a next step).",
    "Trees per neighbourhood counts only the municipal tree layer (public green), not "
    "private green.",
    "The green backbone is 'urban area, green to be preserved' (v1) — not a total "
    "green inventory.",
    "Scores are percentile scores within Breda (relative, not absolute); the direction "
    "per value is stated at the map legend and quoted in values.py.",
]
