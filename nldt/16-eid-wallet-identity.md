# 16 — eID Wallet identity layer (EUDI Wallet / eIDAS 2)

Plan for integrating **EU Digital Identity Wallet** authentication into the
nLDT architecture as the revised BK-3 identity track (decision 7, 2026-09-14:
annex-attachment work dropped — the annex *generator* stays as merged; the
Word/PDF attachment + foreign-side gate will not be built until beleidskompas
code exists).

| | |
|---|---|
| Status | Plan (2026-09-14) · replaces the identity items of BK-3 in [14](14-beleidskompas-integration.md) §8 |
| Legal frame | eIDAS (EU) 910/2014 + amending Regulation (EU) 2024/1183; ARF v2.x |
| External | [EC EUDI Wallet](https://ec.europa.eu/digital-building-blocks/sites/spaces/EUDIGITALIDENTITYWALLET/pages/694487738/EU+Digital+Identity+Wallet+Home) · [eu-digital-identity-wallet](https://github.com/eu-digital-identity-wallet) · [italia/eudi-wallet-it-python](https://github.com/italia/eudi-wallet-it-python) |
| Related | [07](07-trust-and-governance.md) · [10](10-toolbox-integration.md) (Keycloak) · [`../docs/GENAI_SEAMS.md`](../docs/GENAI_SEAMS.md) (receipt trail) · [`services/common/auth.py`](services/common/auth.py) |

---

## 1. What is integrating

The **EU Digital Identity Wallet** (EUDI Wallet): each member state must offer
at least one wallet (deadline December 2026; NL Wallet under development by
Logius, broad release expected early 2027). Wallets hold verifiable
attestations (PID, role/organisation credentials) and present them to
**Relying Parties** over OpenID4VP (presentation), with selective disclosure.
Relying parties must register/be certified under the implementing regulations
before production use.

For nLDT this means: **humans prove who they are with a wallet attestation;
nLDT services consume that as verified identity claims.** The existing service
identity (beleidskompas-svc bearer tokens, Keycloak client_credentials) stays
for machine-to-machine; the wallet layer adds the *user* identity beneath it.

## 2. Why this fits the doctrine

- **Receipt trail gets a legally anchored "who".** GENAI_SEAMS: *"every number
  keeps its receipt: which source, fetched when, checked by whom."* Today
  "whom" is a bearer-token string. A wallet-verified actor (LoA, organisation,
  role) turns jobs, PROV and run annexes into records signed off by a
  *notified-identity* human — exactly the trust story the App Store line
  (validated models, governance) needs.
- **HITL becomes "a named, wallet-verified person decides".** riskLevel: high
  recipes can require an actor with a minimum Level of Assurance and/or an
  organisation attestation — enforced as data (trustPolicy), not UI promises.
- **Agents become accountable principals.** Deployed agents (beleidskompas,
  orchestrator, engines) today authenticate with shared static secrets — the
  architecture cannot answer *"which agent did this, deployed by whom, under
  what authority?"*. With administration-issued credentials in a virtual
  wallet (§6a), every autonomous actor is verifiable, capability-scoped and
  revocable — the missing half of "humans decide": we can hold both the human
  *and* the machine to account.
- **Data minimisation by construction.** Selective disclosure means nLDT
  requests the minimal claim set (e.g. `is_official` + organisation, not name)
  — matching the Geonovum principle already in [03](03-building-blocks.md).
- **Timing.** Integrating as an early RP during the NL pre-launch window
  positions the testbed as a reference consumer for the national rollout — a
  reusable App Store asset ("wallet-ready front doors").

## 3. Integration principle

> **The wallet verifies the human; the credential verifies the agent; the
> token carries the claims; the engines record executor and approver; the
> trust policy gates on both.**

nLDT does **not** become a wallet implementation. It adds one Relying-Party
edge that turns a verified wallet presentation — from a human's wallet or an
agent's virtual wallet — into nLDT identity claims, and threads those claims
through the existing auth → jobs/PROV → annex → trustPolicy chain. Wrap,
don't rebuild — again.

## 4. Options considered

| Option | Description | Verdict |
|---|---|---|
| **A — Keycloak broker** | EUDI Wallet → Keycloak (OpenID4VP verifier; OID4VCI issuance shipped Jan 2026, verifier via community extension) → OIDC tokens → existing `keycloak` auth mode introspects | ✅ Long-run production path — Keycloak *is* the EU LDT Toolbox identity building block; but verifier support is extension-grade today and the testbed has no IM instance running |
| **B — Python RP edge (pyeudiw-style)** | A small `services/auth_wallet/` FastAPI service implementing the OpenID4VP relying party (Italy's pyeudiw is the Python reference toolchain) and issuing internal nLDT tokens | ✅ Direct control, Python-native, testbed-friendly; more code we own; verify pyeudiw license/profile fit before adopting |
| **C — Pluggable verifier behind our own token edge** | Build the token-issuance + claims plumbing with a `VerifierBackend` interface: a **mock wallet/verifier** now (testable today, no NL wallet needed), a pyeudiw adapter (B) or Keycloak (A) later | ✅ **Recommended** — the token edge, claims model and governance wiring are durable regardless of which verifier wins; protocol-truth lands when the backend adapter does |

**Recommendation:** C now, converging on A for production once (i) a Keycloak
with verifier support is deployed with the toolbox and (ii) NL wallet +
RP registration exist. B is the fallback if Keycloak's verifier stays
extension-grade.

## 5. Target architecture

```text
Human (ambtenaar / resident)          nLDT testbed
┌──────────────────────────┐   ┌──────────────────────────────────────────┐
│ NL Wallet (end-2026) or  │   │ services/auth_wallet  (:8087)            │
│ EC reference wallet      │   │  OpenID4VP RP edge                       │
│  PID + role attestations │──▶│  VerifierBackend: mock | pyeudiw | kc    │
└──────────────────────────┘   │  → issues nLDT token (opaque, TTL,       │
        QR / redirect          │    claims incl. subject_type)            │
                               │  → RFC 7662 introspection endpoint       │
Agent (beleidskompas-svc,       │                                            │
 orchestrator, engine)         │ services (:8081-8085, :8090-8093)         │
┌──────────────────────────┐   │  NLDT_AUTH_MODE=wallet → introspect at    │
│ Virtual wallet (sidecar  │   │  :8087 (same shape as keycloak mode)      │
│  services/agent_wallet)  │──▶│  verified claims → jobs.actor → PROV,     │
│  agent credential issued │   │  annex, trustPolicy gates (LoA/role/      │
│  by deploying admin      │   │  capabilities)                            │
└──────────────────────────┘   │                                            │
       ▲                       │ Deploying administration (issuer)         │
       │ OpenID4VCI issuance   │  Keycloak OID4VCI issuer (toolbox IM)     │
┌──────┴───────────────────┐   │  → agent credentials: agentId, org,      │
│ Public administration    │──▶│    capabilities, validity, status list   │
│ (deployment approval)    │   └──────────────────────────────────────────┘
└──────────────────────────┘
```

Three identity layers, deliberately:

| Layer | Who | Credential | Where it applies |
|---|---|---|---|
| User identity | Human | Wallet attestation → nLDT user token | Front door login; recorded as `actor` on every job |
| Agent identity | Deployed agent / engine | **Agent credential in a virtual wallet** (issued by the deploying administration, OpenID4VCI) → nLDT agent token | MCP/OGC/A2A calls; recorded as `executor` on every job |
| (Legacy) service identity | App/engine | beleidskompas-svc static token / Keycloak client | Backward-compatible fallback until wallet-backed agents (BK-1 status quo) |

The agent credential eventually *replaces* the static service token: instead of
a shared secret in an env var, a deployed agent presents a verifiable,
revocable credential that says **who deployed it, under whose authority, with
which capabilities, valid until when**. Until every consumer is
wallet-backed, the static mode stays available (testbed/dev).

## 6. Claims and governance design

- **Token claims (introspected), one schema for both subject types:**
  `subject_type` (`human` | `agent`), and per type — human: `sub`
  (pseudonymous subject id — stable per wallet+relying-party pair, no name
  needed), `loa` (eIDAS LoA mapping: `low|substantial|high`), `org`, `roles`;
  agent: `agentId`, `deployingOrg`, `capabilities` (recipe/process ids or
  capability tags the administration authorised), `assurance` (administration-
  defined machine-assurance level — eIDAS LoA is person-oriented, so the
  issuing administration defines this scale), `exp`, plus credential status
  (revocation checked at verification). New contract:
  [`schemas/wallet-claims.schema.json`](schemas/) in W1.
- **Actor propagation — executor *and* approver:** `create_job` gains an
  optional `actor` dict with `executor` (the authenticated caller: human or
  agent claims) and, on HITL-approved runs, `approver` (the wallet-verified
  human who approved). PROV bundle and the S9 run annex include both → the
  receipt trail answers *"which agent executed this, deployed by whom"* and
  *"which human signed it off"* — additive fields, no format break.
- **trustPolicy extension (twin instance):**
  `"identity": {"wallet": {"required": false, "minLoa": "substantial",
  "requiredRoles": ["policy-officer"], "agentCapabilityModel": "recipes"}}` —
  per-twin, overridable per recipe by riskLevel (high → minLoa high + role
  gate + agent-executor allowed only with an explicit capability for that
  recipe). Agent `capabilities` bind to the BK-2 `application` record's
  `consumesRecipes` allow-list: the credential authorises what the catalog
  record declares.

## 6a. Agent virtual wallets (design)

- **Wallet form:** a sidecar service (`services/agent_wallet/`) that holds the
  agent's issued credentials and keys and performs OpenID4VP presentations on
  the agent's behalf. One implementation serves all agents; agents keep no
  long-lived secrets themselves. (In-process library is the alternative —
  rejected for now: N runtimes × key management.)
- **Issuance flow (deployment):** when an administration deploys an app/agent
  (the App Store install path, BK-2), its credential issuer (Keycloak
  OpenID4VCI — shipped Jan 2026, and Keycloak is the toolbox identity
  building block) issues the agent credential to the agent's virtual wallet:
  `agentId`, `deployingOrg`, `capabilities` (from the application record's
  `consumesRecipes`), validity window, status-list revocable. Renewal and
  revocation are administrative actions with an audit trail.
- **Runtime flow:** agent → virtual wallet → OpenID4VP presentation to
  `auth_wallet` RP edge → verified agent claims → nLDT agent token →
  MCP/OGC/A2A calls introspected as today. Revocation propagates within the
  credential status check.
- **Testbed first:** mock issuer + mock virtual wallet in W1 (credential
  shapes real, trust anchors local); real Keycloak OID4VCI issuer + EC
  reference wallet interop in W2/W6.

### Alignment with European Business Wallets (EBW)

The deploying administration in §6a is a **legal person** — and the EC's
[European Business Wallets](https://digital-strategy.ec.europa.eu/en/policies/business-wallets)
track covers exactly this: a Regulation on the establishment of European
Business Wallets is in the ordinary legislative procedure (proposal in the
digital omnibus package; Council general approach 9 June 2026; trilogue
pending), building on the EUDI Wallet architecture, with mandatory acceptance
by public administrations two years after adoption. Its function list includes
**"delegate others to act on their behalf in a legal capacity"** — which is
precisely the deploying-administration → agent delegation this plan models.

Consequences:

- The **agent credential is profiled as an EBW-style organisational
  delegation attestation**, not a bespoke format: issuer = the deploying
  administration (organisational wallet / Keycloak OID4VCI in the testbed),
  subject = the agent, semantics = delegation with capability scope. Our
  claims model (`agentId`/`deployingOrg`/`capabilities`/`assurance`) already
  matches; only the credential encoding profiles onto the EBW rulebook when
  it lands (W6 tracks it).
- Public-administration acceptance of business wallets will be **obligatory**
  post-adoption — the nLDT testbed becoming an early EBW-accepting relying
  party is the same strategic play as the EUDI reference-RP positioning
  (decisions 5), and strengthens the App Store governance story.
- The [WeBuild consortium](https://webuildconsortium.eu) pilot (Digital
  Europe Programme) is the observation point for implementation practice.

## 7. Phased plan

### W0 — Contracts & decisions (days, docs only)

- This doc reviewed; open decisions (§10) taken.
- `wallet-claims.schema.json` draft; trustPolicy `identity` block specified;
  14-...md BK-3 re-scoped (done in this commit).

**Done when:** decisions recorded; schemas drafted.

### W1 — Token edge with mock verifier (1 sprint)

- `services/auth_wallet/app.py` (:8087): `POST /present` (accepts a
  presentation), `POST /introspect` (RFC 7662, same response shape our
  keycloak mode already parses), token store with TTL.
- `VerifierBackend` interface + `MockBackend` (deterministic presentations for
  tests/dev — clearly labelled, never enabled in production configs).
- `NLDT_AUTH_MODE=wallet` in `services/common/auth.py`: introspection against
  `NLDT_WALLET_INTROSPECT_URL` (reuses the keycloak-mode code path, different
  URL + fail-closed semantics identical).
- Tests: mode wiring, introspection caching reuse, claims propagation into
  `create_job` actor, 401/503 shapes consistent with existing modes. Both
  subject types from day one: a mock **human** wallet presentation and a mock
  **agent** presentation (per §6a shapes) issue tokens with
  `subject_type`-correct claims.

**Done when:** mock-authenticated requests (human *and* agent) reach `:8082`,
the job record carries executor (and approver where applicable) claims, and
anonymous/expired/insufficient-credential calls behave fail-closed — all in
the test suite.

### W2 — Real OpenID4VP backend (1–2 sprints; decision-gated)

- Evaluate pyeudiw (license, ARF/DCQL conformance, Dutch profile deltas)
  vs Keycloak verifier extension (deploy with toolbox IM per
  [10](10-toolbox-integration.md)). Implement the chosen `VerifierBackend`
  adapter behind the W1 interface; real wallet/reference-wallet interop test
  against the EC reference implementation.
- RP registration path documented (legal prerequisite for production; testbed
  runs on the EC reference trust framework where possible).

**Done when:** a real wallet presentation (EC reference wallet or NL pilot)
produces an nLDT token through the same edge as the mock.

### W3 — Governance wiring (1 sprint)

- trustPolicy identity gates enforced in the process adapter (pre-execution
  check: recipe riskLevel vs human actor LoA/roles **and agent-executor
  capabilities** → run or 403 with reason).
- PROV + run annex carry `executor` and `approver`; GENAI_SEAMS receipt-trail
  wording updated ("checked by whom" → wallet-anchored, "executed by which
  agent, deployed by whom").
- HITL: high-risk recipe approval records the approver's wallet claims; agent
  executions of high-risk recipes require an authorised human approver.

**Done when:** a high-risk recipe is rejected for insufficient LoA in a test,
an agent without the recipe capability gets 403, and an approved run's annex
shows the wallet-verified approver and the credentialed executor.

### W4 — Front-door & federation (aligns with BK-4)

- GovChat-NL/OpenWebUI: wallet login option at the front door; beleidskompas
  passes user-token context alongside its service token (header contract in
  [govchat/README.md](govchat/README.md)).
- A2A/MCP: actor claims propagate on `execute-recipe` tasks.
- Outreach addendum: "wallet-ready" positioning for the NL rollout.

**Done when:** the beleidskompas-shaped flow authenticates a user via wallet
and the grounded answer's annex carries that user's verified identity.

### W5 — Agent virtual wallet (1 sprint; may run parallel to W2/W3)

- `services/agent_wallet/` sidecar: credential store (issued agent
  credentials + keys), `POST /present` (OpenID4VP presentation on behalf of
  the agent), `GET /credentials`. Mock credentials from W1 initially.
- `beleidskompas-svc` / orchestrator wiring: the agent's MCP/OGC calls obtain
  their nLDT token via the virtual wallet instead of a static env token
  (static mode stays as fallback).
- Capability binding: virtual wallet only presents credentials whose
  `capabilities` cover the requested recipe/process (fail closed client-side
  too).

**Done when:** the BK-1 Kestra demo flow authenticates as a wallet-backed
agent (mock credential) and a capability-revoked agent is refused.

### W6 — Issuance by the deploying administration (decision-gated, toolbox IM)

- Deploy Keycloak as OID4VCI issuer in the testbed (toolbox Identity
  building block, [10](10-toolbox-integration.md)); define the agent
  credential (schema + claims per §6) as an issuer credential configuration.
- Deployment flow: app install (BK-2 `application` record) → administration
  approval → OpenID4VCI issuance into the agent's virtual wallet (capabilities
  derived from the record's `consumesRecipes`) → runtime per §6a.
- Status-list revocation: revoke/renew as administrative actions; RP edge and
  virtual wallet check status.
- NL/EC alignment: profile the credential with the national wallet programme
  where applicable (ties to the W2/W4 NL engagement).

**Done when:** a credential issued by a testbed Keycloak instance flows
through issuance → virtual wallet → presentation → verified nLDT token, and
revocation blocks a subsequent presentation.

## 8. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| NL wallet launches late / profile shifts (ARF 2.x churn, DCQL) | W2 rework | W1's pluggable verifier + claims model are profile-agnostic; pin profiles in the adapter only |
| pyeudiw targets the Italian profile; Dutch deltas | Integration friction | Adapter isolates profile specifics; NL Wallet is the W2 interop target, pyeudiw only a candidate |
| RP registration/certification is a legal process | Production blocked | Testbed runs mock/reference trust framework; registration tracked as an organisational action (W2) |
| Keycloak verifier remains extension-grade | Option A slips | Option B adapter is the fallback by design |
| Privacy scope creep (collecting more than needed) | DPIA/legal exposure | Claims set fixed (human: sub/loa/org/roles; agent: agentId/deployingOrg/capabilities/assurance); selective disclosure requested minimally; documented in W1 |
| Wallet identity ≠ authorisation | Over-trust | Roles/org attestations gate via trustPolicy; wallet proves identity, policy decides rights |
| Agent key/credential theft (virtual wallet compromised) | Impersonated agent | Sidecar isolates keys from agent runtimes; credentials are status-list revocable; capabilities limit blast radius; short validity windows |
| Machine assurance not standardised (eIDAS LoA is person-oriented) | Confusing trust semantics | Administration defines its own `assurance` scale for agent credentials, documented in the issuer config; nLDT gates on the declared scale, never assumes LoA equivalence |
| Capability drift (credential vs BK-2 application record) | Over-authorised agent | Issuance derives capabilities from the record's `consumesRecipes`; RP edge cross-checks both; re-issuance on record change |
| Agent-credential revocation latency | Revoked agent keeps working | Status-list check at presentation AND token TTL short (minutes, not days); trustPolicy may cap TTL for high-risk recipes |
| Business Wallet Regulation in trilogue (not adopted; shapes may shift) | Agent-credential profile rework in W6 | Claims model is profile-agnostic; W6 profiles onto the EBW rulebook only when final; track the trilogue + WeBuild pilot; post-adoption public-admin acceptance obligation is an opportunity, not a threat |

## 9. Relation to the previous BK-3 scope

- **Kept (already merged):** S9 run-annex generator, auth hardening
  (constant-time, introspection cache), HITL/OTel remain open items — HITL
  lands in W3 (wallet-verified approver), OTel stays deferred.
- **Dropped (decision 7):** Word/PDF annex attachment and foreign-side
  number-gate — waiting on beleidskompas code; the annex contract itself is
  ready when it lands.
- **Replaced:** "Keycloak client provisioning when IM exists" broadens into
  the wallet track (Keycloak remains the production verifier candidate, W2).

## 10. Decisions (2026-09-14 — user directive: follow the EUDI implementation
## guidelines as closely as possible; controller recommendations adopted)

| # | Decision | Choice |
|---|---|---|
| 1 | Verifier path | **C — pluggable, mock-first**, converging on Keycloak (toolbox IM) for production; pyeudiw adapter as fallback |
| 2 | Token model | **Opaque tokens + local RFC 7662 introspection** (mirrors keycloak mode, zero new deps) |
| 3 | Claims set | `subject_type` + human `sub/loa/org/roles` + agent `agentId/deployingOrg/capabilities/assurance`; pseudonymised low-LoA citizen lane deferred (data model allows it) |
| 4 | Ports | **auth_wallet :8087, agent_wallet :8088** |
| 5 | NL engagement | Approach Logius/NL Digital Government on reference-RP participation together with the GovChat-NL outreach (organisational action) |
| 6 | Agent wallet form | **Sidecar service** — one implementation, keys isolated from agent runtimes |
| 7 | Agent assurance scale | Administration-defined three levels: **`basic | attested | audited`** (never equated to eIDAS human LoA) |
| 8 | Capability model | **Recipe/process-level** (`consumesRecipes`-aligned, BK-2) |
| 9 | Token TTL | **Minutes (default 300 s)** for wallet-issued tokens; trustPolicy may cap tighter for high-risk recipes |
| 10 | Agent-credential profiling (2026-09-14, after user review of the EBW track) | **Profile the agent credential as an EBW-style organisational delegation attestation** ("delegate others to act on their behalf in a legal capacity"); W6 profiles onto the final EBW rulebook, tracking the trilogue and the WeBuild pilot |

**ARF alignment (binding for all wallet work):** implementations follow the
[ARF](https://github.com/eu-digital-identity-wallet/eudi-doc-architecture-and-reference-framework)
(latest tagged release; Annex 2 high-level technical requirements) and the
profiles it mandates — OpenID4VP (client_id scheme `x509_san_dns` for
redirect-based RPs), DCQL-style credential queries, mdoc (ISO/IEC 18013-5)
and SD-JWT VC credential formats, and Token Status List for revocation.
W1/W5 use ARF-*shaped* envelopes against the mock verifier; W2 pins the exact
ARF requirement IDs and runs the EC conformance materials
([conformance.eudi.dev](https://conformance.eudi.dev)) when the real backend
lands. Deviations (e.g. a local mock trust anchor) are recorded in the
implementation plan and findings, never silent.

## 11. References

- EC EUDI Wallet home & service-provider programme:
  <https://ec.europa.eu/digital-building-blocks/sites/spaces/EUDIGITALIDENTITYWALLET/pages/694487738/EU+Digital+Identity+Wallet+Home>
- EC reference implementation: <https://github.com/eu-digital-identity-wallet>
- pyeudiw (Python RP toolchain): <https://github.com/italia/eudi-wallet-it-python>
- Keycloak OpenID4VCI (Jan 2026):
  <https://www.keycloak.org/2026/01/issue-credentials-over-openid4vci> ·
  Keycloak wallet-verifier discussion:
  <https://github.com/keycloak/keycloak/discussions/47346>
- NL: <https://www.nldigitalgovernment.nl/overview/identity/id-wallet/> ·
  EU pilots (POTENTIAL incl. NL):
  <https://digital-strategy.ec.europa.eu/en/policies/eudi-wallet-implementation>
- European Business Wallets:
  <https://digital-strategy.ec.europa.eu/en/policies/business-wallets> ·
  proposal:
  <https://digital-strategy.ec.europa.eu/en/library/proposal-regulation-establishment-european-business-wallets> ·
  EP legislative train:
  <https://www.europarl.europa.eu/legislative-train/theme-a-new-plan-for-europe-s-sustainable-prosperity-and-competitiveness/file-european-business-wallet> ·
  WeBuild pilot: <https://webuildconsortium.eu>
- Internal: [07-trust-and-governance.md](07-trust-and-governance.md) ·
  [10-toolbox-integration.md](10-toolbox-integration.md) ·
  [14-beleidskompas-integration.md](14-beleidskompas-integration.md) §8/§10
