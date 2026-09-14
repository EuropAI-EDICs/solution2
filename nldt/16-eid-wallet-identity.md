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
- **Data minimisation by construction.** Selective disclosure means nLDT
  requests the minimal claim set (e.g. `is_official` + organisation, not name)
  — matching the Geonovum principle already in [03](03-building-blocks.md).
- **Timing.** Integrating as an early RP during the NL pre-launch window
  positions the testbed as a reference consumer for the national rollout — a
  reusable App Store asset ("wallet-ready front doors").

## 3. Integration principle

> **The wallet verifies the human; the token carries the claims; the engines
> record the actor; the trust policy gates on it.**

nLDT does **not** become a wallet implementation. It adds one Relying-Party
edge that turns a verified wallet presentation into nLDT identity claims, and
threads those claims through the existing auth → jobs/PROV → annex →
trustPolicy chain. Wrap, don't rebuild — again.

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
└──────────────────────────┘   │  → issues nLDT user token (opaque,       │
        QR / redirect          │    TTL, claims: sub, loa, org, roles)    │
                               │  → RFC 7662 introspection endpoint       │
Front door (OpenWebUI /        │                                            │
 beleidskompas / any app)      │ services (:8081-8085, :8090-8093)         │
  user token + svc token  ───▶ │  NLDT_AUTH_MODE=wallet → introspect at    │
                               │  :8087 (same shape as keycloak mode)      │
                               │  verified claims → jobs.actor → PROV,     │
                               │  annex, trustPolicy gates (LoA/role)      │
                               └──────────────────────────────────────────┘
```

Two-layer identity, deliberately:

| Layer | Who | Credential | Where it applies |
|---|---|---|---|
| User identity | Human | Wallet attestation → nLDT user token | Front door login; recorded as `actor` on every job |
| Service identity | App/engine | beleidskompas-svc token / Keycloak client | MCP/OGC/A2A calls (unchanged, BK-1) |

## 6. Claims and governance design

- **Token claims (introspected):** `sub` (pseudonymous subject id — stable per
  wallet+relying-party pair, no name needed), `loa` (e.g. `low|substantial|high`
  per eIDAS LoA mapping), `org` (organisation attestation, if presented),
  `roles` (e.g. `policy-officer`), `exp`. New contract:
  [`schemas/wallet-claims.schema.json`](schemas/) in W1.
- **Actor propagation:** `create_job` gains an optional `actor` dict; services
  populate it from the introspected token (the request that executed the
  process). PROV bundle and the S9 run annex include it → *"checked by
  whom"* becomes wallet-anchored without changing the annex format's shape
  (additive field).
- **trustPolicy extension (twin instance):**
  `"identity": {"wallet": {"required": false, "minLoa": "substantial",
  "requiredRoles": ["policy-officer"]}}` — per-twin, overridable per recipe
  by riskLevel (high → minLoa high + role gate before HITL approval is
  accepted).

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
  `create_job` actor, 401/503 shapes consistent with existing modes.

**Done when:** a mock-wallet-authenticated request reaches `:8082`, the job
record carries the actor claims, and anonymous/expired/low-LoA behave
fail-closed — all in the test suite.

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
  check: recipe riskLevel vs actor LoA/roles → run or 403 with reason).
- PROV + run annex carry `actor`; GENAI_SEAMS receipt-trail wording updated
  ("checked by whom" → wallet-anchored).
- HITL: high-risk recipe approval records the approver's wallet claims.

**Done when:** a high-risk recipe is rejected for insufficient LoA in a test,
and an approved run's annex shows the wallet-verified approver.

### W4 — Front-door & federation (aligns with BK-4)

- GovChat-NL/OpenWebUI: wallet login option at the front door; beleidskompas
  passes user-token context alongside its service token (header contract in
  [govchat/README.md](govchat/README.md)).
- A2A/MCP: actor claims propagate on `execute-recipe` tasks.
- Outreach addendum: "wallet-ready" positioning for the NL rollout.

**Done when:** the beleidskompas-shaped flow authenticates a user via wallet
and the grounded answer's annex carries that user's verified identity.

## 8. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| NL wallet launches late / profile shifts (ARF 2.x churn, DCQL) | W2 rework | W1's pluggable verifier + claims model are profile-agnostic; pin profiles in the adapter only |
| pyeudiw targets the Italian profile; Dutch deltas | Integration friction | Adapter isolates profile specifics; NL Wallet is the W2 interop target, pyeudiw only a candidate |
| RP registration/certification is a legal process | Production blocked | Testbed runs mock/reference trust framework; registration tracked as an organisational action (W2) |
| Keycloak verifier remains extension-grade | Option A slips | Option B adapter is the fallback by design |
| Privacy scope creep (collecting more than needed) | DPIA/legal exposure | Claims set fixed at sub/loa/org/roles; selective disclosure requested minimally; documented in W1 |
| Wallet identity ≠ authorisation | Over-trust | Roles/org attestations gate via trustPolicy; wallet proves identity, policy decides rights |

## 9. Relation to the previous BK-3 scope

- **Kept (already merged):** S9 run-annex generator, auth hardening
  (constant-time, introspection cache), HITL/OTel remain open items — HITL
  lands in W3 (wallet-verified approver), OTel stays deferred.
- **Dropped (decision 7):** Word/PDF annex attachment and foreign-side
  number-gate — waiting on beleidskompas code; the annex contract itself is
  ready when it lands.
- **Replaced:** "Keycloak client provisioning when IM exists" broadens into
  the wallet track (Keycloak remains the production verifier candidate, W2).

## 10. Open decisions

1. **Verifier path:** confirm C (pluggable, mock-first) with convergence on
   Keycloak — or go straight for pyeudiw direct?
2. **Token model:** opaque tokens + local introspection (recommended — mirrors
   the keycloak mode, zero new deps) vs signed JWTs (needs a JWT library).
3. **Claims set:** is `sub/loa/org/roles` the right minimal set, or do
   scenarios need pseudonymised citizen access (residents asking scan
   questions) with a lower LoA lane?
4. **Port/namespace:** auth_wallet on :8087 as proposed?
5. **NL engagement:** approach Logius/NL Digital Government about reference-RP
   participation — same moment as the GovChat-NL outreach (one story:
   "wallet-ready DT front doors").

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
- Internal: [07-trust-and-governance.md](07-trust-and-governance.md) ·
  [10-toolbox-integration.md](10-toolbox-integration.md) ·
  [14-beleidskompas-integration.md](14-beleidskompas-integration.md) §8/§10
