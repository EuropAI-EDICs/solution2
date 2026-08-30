+:---------------------------------:+:----------------------------------+
|                                   |                                   |
+-----------------------------------+-----------------------------------+
| **Rob Peters**                    | **Willem Treurniet**              |
|                                   |                                   |
| Province of Utrecht               | Netherlands Institute for Public  |
|                                   | Safety (NIPV)                     |
| <rob.peters@provincie-utrecht.nl> |                                   |
|                                   | <willem.treurniet@nipv.nl>        |
+-----------------------------------+-----------------------------------+
|                                   |                                   |
+-----------------------------------+-----------------------------------+
| **Guido Legemaate**               |                                   |
|                                   |                                   |
| Safety Region                     |                                   |
| Amsterdam-Amstelland              |                                   |
|                                   |                                   |
| <guido                            |                                   |
| .legemaate@veiligheidsregioaa.nl> |                                   |
+-----------------------------------+-----------------------------------+

# ABSTRACT

This practitioner's paper examines three generative AI proofs‑of‑concept
co-developed by professionals to enhance rapid decision support in
emergency management. The prototypes include a spatial opportunity‑map
generator, a 3D geolocation and object‑classification tool, and an
operational Virtual Assistant that automates situational awareness
during incidents. Together, they demonstrate the growing potential of
hybrid GeoAI systems to integrate scenario generation, spatial analysis
and legislative constraints. While results show promising accuracy and
applicability, particularly in accelerating incident information
management, they also reveal limitations in interpreting complex policy
frameworks. The paper assesses whether current AI solutions are
sufficiently trustworthy and transparent for responsible operational
adoption. The assessment was carried out by members of Inowit, the Dutch
National advisory board on digital technology and innovation for
emergency management. The aim of this assessment is to feed the future
research agenda regarding validation of AI supported crisis information
management.

## Keywords

Geo AI, Emergency Information Management, Trustworthy AI

# INTRODUCTION

One of the most promising developments of generative AI in the field of
emergency management information systems is the combination of fast
scenario generation, object identification and multi factor scenario
analyses. The problem in this combined development is to make AI-agents
understand all the aspects that determine the accumulated risk and the
allocation of resources in a truly spatial manner and to keep it
maintainable. In this practitioner's paper we will describe three AI
proof-of-concepts and a validation mechanism that were co-developed by
professionals to help their peers in rapid decision support. We explored
whether we deem AI trustworthy and helpful enough from a practitioner's
point of view to implement such solutions at this moment in time. The
assessment is carried out by an acknowledged expert group that acts as
advisor agency for senior National management ( Inowit
[Informatievoorziening -
BrandweerNederland.nl](https://www.brandweernederland.nl/onderwerpen/informatievoorziening/))

# CURRENT PROTOTYPES AND APPLICATIONS

The first prototype is an on-the-fly 'opportunity map generator' that is
already applicable in the legislative safety permitting stage of spatial
planning to prevent safety issues at a later stage. This application
creates spatial views based on automatic selection of relevant
parameters for the positioning of objects, taking safety aspects and
emergency management processes into account. Think for example of
'hazardous fuel storage' or noisy/high windmill or an evacuation area.
The first step in the N8N (<https://n8n.io/>) based AI-workflow
orchestration is a tuning agent that applies a Retrieval-Augmented
Generation (RAG) cycle that processes all the ![Afbeelding met kaart,
tekst, schermopname Door AI gegenereerde inhoud is mogelijk
onjuist.](media/image1.png){width="4.231944444444444in"
height="2.3777777777777778in"}relevant policy- and risk related
documents and combines it with a general-purpose Large Language Model
(LLM). In so doing it automatically derives the parameters that are
relevant for the object or task from a permitting process or an
emergency management perspective. This can be conditions such as 'near a
hospital' or 'in a Natura 2000' area
(<https://natura2000.eea.europa.eu/>) or 'near housing area' that would
conflict with putting the object near a high-risk environment. The goal
of this tuning agent is to be able to identify relevant parameters and
then eliminate all zones from a city contour or a regional contour that
would hamper the positioning of the object or task. The training agent
then delivers the combined zones that remain available after this
elimination to a spatial agent that generates the remaining opportunity
areas in JavaScript Object Notation (JSON) programming code and
visualises the result in a map-viewer such as QGIS
(<https://qgis.org/>). The prototype did produce a reliable map with
relevant cutouts, but it failed to derive the comprehensive and
sometimes the most relevant sets of legislative norms from all hundreds
of policy documents. The development of the prototype also highlighted
the need for close collaboration between practitioners and AI
developers, especially in the legislative domain about what documents
and semantics exactly are required and which rules or norms should be
applied.

![Afbeelding met schermopname, boom, wolk, Grafische software Door AI
gegenereerde inhoud is mogelijk
onjuist.](media/image2.jpeg){width="3.8201388888888888in"
height="2.270138888888889in"}The second prototype is a similar
identification, geolocation and approximation tool. It is built to
support the rapid generation of all measures that allow or disallow
object allocation near risk objects in a 3D environment. The placement
of housing or buildings near a large UNESCO World Heritage area of - in
this case - protected medieval fortresses is only allowed with
compensating actions such as sound walls, for example. But windmills or
solar panels on top of those walls are not allowed if near a UNESCO
contour. The AI supports fast geolocation in coordinates and
classification of all objects and contours and generates Blender
(<https://code.blender.org/>) or JSON/unity (<https://unity.com/>) code
to identify opportunities and constraints. This second prototype did
generate fast overviews for a very large area during a preliminary
Heritage Impact Assessment and seems applicable for many different
application domains, where legislative muti-factor analyses and scenario
building are required.

![Afbeelding met tekst, diagram, schermopname, cirkel Door AI
gegenereerde inhoud is mogelijk
onjuist.](media/image3.png){width="3.5902777777777777in"
height="2.015277777777778in"}The third prototype is the Virtual
Assistant (VA). The VA provides an automated situational picture of an
incident based on public and restricted information sources. It supports
the emergency coordinator and the operational information manager in
providing information during an incident. The automated collection of
relevant information sources provides a complete picture of all
vulnerable and hazardous objects near the incident, improving and
accelerating picture compilation and decision-making during an incident.
This VA is operationally available for all safety regions in the
Netherlands. Two additional functionalities of the VA are still in the
pilot phase. The first one uses LLM technology to search for past
incidents similar to the current incident, identifying relevant lessons
learned and bringing them to the attention of the response organization.
The second one addresses the challenges of interpreting emergency
Governance Network Maps (BNKs) within a concrete operational context - a
task where previous iterations of the VA faced limitations. While
generic AI often struggles with the broader context of governance
responsibilities, the third prototype utilizes a hybrid AI approach that
combines RAG with Knowledge Graphs (KG) and vector embeddings to
transform complex legal and governance diagrams into machine-readable
'triples'. The KG is the validation mechanism for the professional.

This setup allows the system to analyze a brief, free-text incident
description and, within less than a minute, identify the relevant legal
frameworks and the specific organizations that must be involved.
Evaluations of the proof-of-concept demonstrated high reliability,
achieving accuracy scores between 97% and 98%, while reducing the time
required for manual network mapping from over two hours to just sixty
seconds. Crucially, the use of KGs ensures traceability and
transparency, allowing crisis managers to see exactly why a specific
organization is recommended based on the underlying BNK. This shifts the
role of the information manager from manual searching to expert
validation, ensuring that the right crisis partners are at the table
during the "golden hour" of a crisis.

# RESEARCH CHALLENGE

In the three examples described, validation is crucial. In all three
examples, it was possible to arrive at sufficiently explainable
solutions. The picture below shows how considerations applied by the AI
agent can be traced back to the Environmental Vision of the Province of
Utrecht. At the same time this decision table support user validation
and can be used in SKILLS ([Home \\
Anthropic](https://www.anthropic.com/)) to feed new prompts as a guiding
principle.

![](media/image4.png){width="6.241679790026247in"
height="3.5223884514435695in"}

In our view, an important challenge for researchers is therefore to find
a generalizable solution for validation in such a way that it is an
integral part of the working process and the government policy cycle
(design, programming, permission and monitoring).

# CONCLUSION

The focus of this practitioner paper was to explore whether generative
AI is mature enough to support the challenges of practitioners in a
responsible manner. GeoAI or Spatial AI is getting up to speed. Whereas
large software companies still struggle to bridge GIS knowledge and AI
knowledge, the combination is already very powerful for practitioners.
Developing a generalizable solution to correctly - and, more
importantly, verifiably - infer the legal and policy constraints
affecting safety zones and spatial planning will require additional
time. We therefore propose this as a key challenge for future research.
Validation must be an integral part of the working process, the agent
orchestration architecture and the emergency policy cycle to ensure the
integrity of public values in a FAIR way . In addition to GIS and AI
orchestration knowledge, legislative, safety and policy domain knowledge
is a third knowledge area that requires in depth investments for
developers and practitioners. In the three examples described, hybrid
combinations of rule-based agents and genAI based agents seem to work at
least promising for that purpose.

# ACKNOWLEDGEMENTS

The authors would like to thank the GIS-team of the province of Utrecht,
the University of Applied Sciences Utrecht and the many safety regions
involved in the development of the Virtual Assistant and the
MultAI-functionality for their highly valuable role and contributions.
Part of this research was supported by the Genecity project of the
HORIZON-MISS-2025-04-CIT-02 call of the European Commission.

# 
