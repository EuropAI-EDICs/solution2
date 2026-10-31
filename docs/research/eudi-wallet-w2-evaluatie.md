# EUDI-wallet W2-evaluatie — echte OpenID4VP-backend (pyeudiw vs Keycloak)

| | |
|---|---|
| **Rol** | Besluitvoorbereiding voor fase W2 van [`nldt/16-eid-wallet-identity.md`](../../nldt/16-eid-wallet-identity.md) (roadmap-gap G8: "W2/W6 wallet backends decision-gated"). W2 is besluit-gated: dit document levert het besluitvoorstel, niet het besluit. |
| **Retrieval-datum** | 2026-10-31 — alle bronnen zijn die dag geraadpleegd (zie §5 verificatielog en §6 bronnen). |
| **Methode** | Cite-or-abstain: elke feitelijke claim is afkomstig uit een geraadpleegde bron; waar een primaire bron ontbreekt of niet gevonden is, staat dat expliciet gemarkeerd (**unverified** / **abstained**). |
| **Vraag** | Welke `VerifierBackend`-adapter bouwen we als W2 (optie B: pyeudiw-RP-edge, of optie A: Keycloak-verifier), onder welke voorwaarden, en wat betekent de Belgische context voor de Gent-piloot? |

---

## 1. Samenvattend advies (besluitvoorstel G8)

1. **De licentie-belemmering voor pyeudiw is weg.** De doctrine eiste expliciet "verify pyeudiw license/profile fit before adopting" — het repo is **Apache-2.0** (licentiebadge + LICENSE-bestand geverifieerd op de repo-pagina). Licentie-fit: akkoord.
2. **Keycloak 26.8.0 (2026-10-01) levert een OID4VP-verifier in core — maar experimenteel.** De release kondigt "issue and verify digital wallet credentials with OID4VCI and OID4VP" aan; de release notes noemen het onderdeel expliciet *"Verify credentials with OID4VP (experimental)"*, met same-device (link) en cross-device (QR). De doctrine-aanname uit september ("verifier support is extension-grade today") is daarmee **achterhaald**: het is nu core-maar-experimenteel. Aan de productieconvergentie-voorwaarde "(i) a Keycloak with verifier support" is software-matig voldaan, aan GA nog niet.
3. **Het ARF staat op 3.0.0** (juli 2026): "mature", met een **nieuw conformance-kader** en een RP-model in **drie lagen**; nieuwe eis dat wallets, RPs én issuers trust anchors uit Trusted Lists (ETSI TS 119 612) én andere bronnen beheren. De referentie "ARF v2.x" in nldt/16 is verouderd (in deze sessie bijgewerkt).
4. **De beperkende factor voor de Gent-piloot is organisatorisch, niet technisch.** België hergebruikt **itsme** als EUDI-wallet (wetgevend mandaat 2024), maar de volledig gecertificeerde wallet stond in recente trackers als "not confirmed" (signing-target najaar 2026); de eIDAS-2-deadline is **24 december 2026**. RP-verplichtingen (registratie in het nationale register, art. 5b(1); datadeclaraties; toegangscertificaat) zijn voor een Vlaamse context nog geen uitgerold pad. Het ACM/IDM-productiepad (INT-01) blijft daarmee voorlopig de realiteit; de mock-first aanpak van `poc-gent` is precies goed.
5. **Voorstel:** bouw W2 als **pyeudiw-adapter achter de bestaande `VerifierBackend`-interface** (optie B): Apache-2.0, de diepste protocoldekking op dit moment (DCQL, X.509 én OpenID Federation 1.0 trust, Token Status List, mso_mdoc + dc+sd-jwt, direct_post.jwt), Python-native dus testbed-passend. **Houd Keycloak als productieconvergentie** (doctrine-besluit 1 blijft staan) en monitor de GA van de verifier; de W6a-KeycloakBackend (machine credentials) en de W2-mensenwallet-adapter blijven gescheiden schakels achter één interface. Profiel-specifieke zaken (Italiaans profiel nu, Belgisch itsme-profiel later) isoleren in de adapter — precies zoals de doctrine voorschrijft. Het besluit zelf laat ik expliciet open (G8); dit is het voorstel om te nemen.

## 2. Bevindingen per optie

### 2.1 pyeudiw — `italia/eudi-wallet-it-python` (optie B)

- **Licentie:** Apache-2.0 (geverifieerd).
- **OpenID4VP-dekking** (uit de feature-matrix van het repo): DCQL ("Duckle" query language) 🟢, same-device én cross-device (QR) 🟢, `direct_post.jwt`-versleutelde responses 🟢, formaten dc+sd-jwt én mso_mdoc 🟢, trust-evaluatie via **X.509 én OpenID Federation 1.0** 🟢, status-list-revocatie 🟢. Niet ondersteund: `transaction_data` / `transaction_data_hashes`.
- **OpenID4VCI-dekking** (relevant voor de W6-lens): PAR, OAuth 2.0 attestation-based client authentication, PKCE, DPoP, immediate issuance, SD-JWT VC én mso_mdoc, credential offers via QR, refresh tokens 🟢; batch- en deferred issuance niet.
- **Vorm:** SATOSA-backend — een extra architectuurlaag; Italiaans IT-Wallet-profiel als doelprofiel (IT-Wallet is live in de IO-app, 10,1 mln activaties per februari 2026).
- **Volwassenheid-bedeningen:** géén zichtbare tagged releases op GitHub (releases-pagina leeg) → versiepinnen vereist een commit-pin, geen versienummer; het repo claimt conformantie aan het Italiaanse profiel, niet expliciet aan het ARF; 31 stars/19 forks — klein maar overheids-gedreven en actief (2026-issues/PR's, CI aanwezig).
- **Federation-openpunt:** discussie over X.509-trust-anchors en cross-border trust-chain-interop (issue #533, maart 2026) — relevant voor de Belgische/NL-cross-over, monitoren.

### 2.2 Keycloak (optie A)

- **26.8.0 (2026-10-01):** headline "Issue and verify digital wallet credentials with OID4VCI and OID4VP"; de verifier heet in de release notes *"Verify credentials with OID4VP (experimental)"* — same-device via link, cross-device via QR-code, volgens OpenID4VP 1.0; bruikbaar als EUDI-RP. **26.8.1 (2026-10-13)**: ~19 CVE-fixes (geen boven medium in Keycloak zelf).
- **26.7:** experimentele OID4VCI-issuance + admin-beheer van verifiable credentials per gebruiker.
- **Bekende hiaat:** `issuer_info`-ondersteuning ontbreekt nog (Keycloak-issue #53293, sept 2026) terwijl het EUDI-kader vereist dat PID/attestation-providers registratiecertificaten publiceren.
- **Community-extensie:** "Keycloak Wallet Authenticator" (Apache-2.0; getest tot Keycloak 25 via Testcontainers) — tussenreleases-pad, niet langer nodig sinds core-ondersteuning.
- **Doctrine-voordeel:** Keycloak is de identiteitsbouwsteen van de toolbox-IM ([doc 10](../../nldt/10-toolbox-integration.md)); de W6a-KeycloakBackend (client_credentials, machine credentials) draait al tegen dezelfde seam — één IM-instantie zou W2 (mens) en W6a (machine) kunnen bedienen zodra GA.
- **Abstained:** de DCQL-diepte en credential-formats van de 26.8-verifier kon ik op retrieval-dag niet uit primaire bron verifiëren (release notes via secundaire bronnen geraadpleegd) — niet meegenomen in de vergelijking als feit.

### 2.3 Kader: ARF en conformance

- **ARF 3.0.0 is actueel** (aangekondigd als "now live" en "mature" — geen grote inhoudelijke wijzigingen meer verwacht, alleen kleine updates). Het **conformance-kader is nieuw in v3.0.0** (voorgaande framework-versie 2.0, mei 2026).
- **RP-herstructurering:** de relying party is in drie lagen gemodelleerd (o.a. legale entiteit + register-inschrijving, en de RP-client) — raakt ons claims-model niet (subject_type human/agent blijft), maar wel de RP-registratie-uitwerking.
- **Nieuwe trust-anchor-eis** (changelog juli 2026): wallets, RPs én issuers halen en beheren trust anchors uit Trusted Lists (ETSI TS 119 612) én andere bronnen — bevestigt de pyeudiw-keuze voor dubbele trust-evaluatie (X.509 + Federation) en is een eis om in de adapter te pinnen.
- **conformance.eudi.dev** blijft het officiële portaal; het W2-"done when"-criterium in nldt/16 ("runs the EC conformance materials") blijft onverkort leidend.

### 2.4 Belgische context (Gent-piloot)

- België heeft het wallet-mandaat in 2024 in de wet gezet en **hergebruikt itsme** als EUDI-wallet in plaats van nieuwbouw; het voegt e-documenten/e-attributes toe richting de EU-deadline.
- **Deadline eIDAS 2:** elke lidstaat moet per **24 december 2026** minimaal één gratis, gecertificeerde EUDI-wallet aanbieden. Volwassenheid van de Belgische certificering: in trackers als "not confirmed" gemarkeerd (**unverified** — geen primaire federale bron geraadpleegd).
- **RP-verplichtingen:** registratie in het nationale register van de vestigingslidstaat (art. 5b(1)), declareren welke gegevens worden opgevraagd, toegangscertificaat verkrijgen, en zich vóór opvragen identificeren naar de gebruiker. "Covered" private relying parties (banken, telecom) moeten de wallet per **december 2027** accepteren; de EC draait een Relying Party Programme voor readiness.
- **Consequentie voor Gent:** tot het Belgische RP-pad (itsme/EUDI + nationaal register) uitgerold is, blijft ACM/IDM het productie-authenticatiepad (INT-01) en is de EUDI-route testbed/mock (zoals `poc-gent` nu heeft). De W2-backend-keuze is daarmee **testbed-gedreven**, niet productie-gedreven — wat de rol van het experimentele stadium van Keycloak relativeert en de protocoldiepte van pyeudiw zwaarder laat wegen.

## 3. Afweging op doctrine-criteria

| Criterium | pyeudiw (B) | Keycloak 26.8 (A) |
|---|---|---|
| Licentie | Apache-2.0 ✓ | Apache-2.0 ✓ |
| OpenID4VP-diepgang | DCQL + X.509 én Federation-trust + status list + 2 formaten | core maar **experimenteel**; DCQL-diepte **abstained** |
| Trust anchors (ARF 3.0-eis) | dubbele evaluatie aanwezig | via `issuer_info` nog hiaat (#53293) |
| Python-native testbed | ✓ (SATOSA) | ✗ (Java; wel RFC 7662-introspectie zoals W6a al doet) |
| Toolbox-IM-convergentie | ✗ | ✓ (doc 10; één instantie voor W2-mens + W6a-machine) |
| Bewezen productie (wallet-ecosysteem) | IT-Wallet live (10,1 mln activaties feb 2026) | experimenteel; GA te monitoren |
| Issuance (W6-lens) | OID4VCI breed ondersteund | sinds 26.7 experimenteel |
| Belangrijkste risico | Italiaans profiel; géén tagged releases (commit-pin) | experiment-flag; issuer_info-gap |
| RP-registratie (organisatorisch) | onafhankelijk van keuze: Belgisch pad (itsme/nationaal register) nog niet uitgerold; NL-pad via Logius loopt via de bestaande outreach (besluit 5) | idem |

## 4. Voorgestelde vervolgstappen (na het G8-besluit)

1. W2-implementatie als `PyEudiwBackend(VerifierBackend)` — klein, profiel-specifieke zaken geïsoleerd in de adapter; versiepinnen op commit-hash; offline unit-tests met opgenomen fixtures, netwerk alleen in expliciete interop-tests.
2. Interop-test tegen de EC-reference-wallet (of het Italiaanse IT-Wallet-testmilieu) als "done when"-bewijs, daarna de EC-conformance-materialen via conformance.eudi.dev.
3. Keycloak-GA-monitor als productieconvergentie (doctrine-besluit 1 ongewijzigd): een `KeycloakOpenID4VPBackend` landt achter dezelfde interface zodra de verifier niet-experimenteel is en `issuer_info` er is.
4. ARF-referenties in nldt/16 zijn in deze sessie naar 3.0.0 opgeschort; de adapter pint ARF-requirement-ID's conform de ARF-alignmentregel.
5. Organisatorische acties blijven gescheiden van code: Belgische RP-registratie (Digitaal Vlaanderen/itsme-traject) voor Gent, NL-reference-RP-participatie via de bestaande Logius-outreach (besluit 5).
6. Niet-gewijzigd: claims-model, token-edge + TTL, trustPolicy-gates (W1/W3 blijven geldig) en de W6a-machine-credentials.

## 5. Verificatielog (gehaald / niet gehaald)

- ✓ pyeudiw-repo-pagina: licentie (Apache-2.0), feature-matrix OpenID4VP/VCI, activiteit — direct geraadpleegd.
- ✓ Keycloak 26.8-inhoud: aankondiging + release-notes-citaten via zoekresultaten (o.a. "Verify credentials with OID4VP (experimental)"); **niet** via direct fetch van keycloak.org (eerste URL-gok 404; correcte URL's uit zoekresultaat overgenomen, zie §6).
- ✓ ARF 3.0.0 + conformance-kader + RP-lagen + trust-anchor-eis: via het ARF-GitHub-repo en eudi.dev-zoekresultaten.
- ⚠ België/itsme-status: trackers en nieuwsberichten; **geen primaire federale bron** geraadpleegd — als unverified gemarkeerd waar het certificeringsstatus betreft.
- Abstained: DCQL-diepte en formaten van de Keycloak-26.8-verifier; exacteTAG/pyeudiw-versienummers (releases-pagina leeg); NL-Wallet-lanceringsstatus (niet opgehaald deze sessie — geen rol in het voorstel).

## 6. Bronnen

- pyeudiw: <https://github.com/italia/eudi-wallet-it-python> (licentie, feature-matrix, activiteit; issue #533 over trust-anchors/federation)
- Keycloak 26.8.0-aankondiging: <https://www.keycloak.org/2026/10/keycloak-2680-released> · release notes: <https://www.keycloak.org/docs/latest/release_notes/index.html> · issuer_info-hiaat: <https://github.com/keycloak/keycloak/issues/53293> · Keycloak Wallet Authenticator-extensie (#790, Apache-2.0)
- ARF: <https://github.com/eu-digital-identity-wallet/eudi-doc-architecture-and-reference-framework> (3.0.0, changelog juli 2026) · <https://eudi.dev/latest/main/> · conformance: <https://conformance.eudi.dev>
- eIDAS 2-context: Verordening (EU) 2024/1183; wallet-aanbiedverplichting per 24-12-2026; RP-registratie art. 5b(1); covered-private-RP-acceptatie per 12-2027; EC Relying Party Programme
- Intern: [`nldt/16-eid-wallet-identity.md`](../../nldt/16-eid-wallet-identity.md) (besluiten 1/5/7, ARF-alignmentregel, W6a) · [`nldt/services/auth_wallet/backend.py`](../../nldt/services/auth_wallet/backend.py) (`VerifierBackend`, `MockBackend`, `KeycloakBackend`) · Gent-consumer: [`poc-gent/adapters/eudi_wallet.py`](../../poc-gent/adapters/eudi_wallet.py)
