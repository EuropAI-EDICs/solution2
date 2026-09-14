# GovChat-NL ↔ nLDT — beleidskompas integration (BK-0/BK-1)

How to run the governed MVP: beleidskompas (or any GovChat-NL app) consumes
nLDT capabilities via authenticated MCP servers. Plan:
[`../14-beleidskompas-integration.md`](../14-beleidskompas-integration.md).

## 1. Start nLDT with auth + MCP-over-HTTP

```bash
cd nldt
export NLDT_AUTH_MODE=static
export NLDT_STATIC_TOKENS="beleidskompas-svc-tok"   # any string; one per consumer
export NLDT_MCP_BEARER_TOKEN="beleidskompas-svc-tok" # used by MCP servers upstream
export NLDT_MCP_HTTP_HOST=0.0.0.0   # Dockerised clients (host.docker.internal); disables SDK loopback allowlist behind our bearer gate
NLDT_START_MCP_HTTP=1 ./scripts/start-services.sh
```

Ports: services :8081–:8085 (context3d :8084 deliberately public — export
URLs), MCP streamable-HTTP: catalog :8090, process :8091, data :8092,
poc :8093 — endpoint `POST /mcp` on each, `Authorization: Bearer <token>`.

Keycloak instead of static tokens: `NLDT_AUTH_MODE=keycloak` with
`KEYCLOAK_URL/REALM/CLIENT_ID/CLIENT_SECRET` (EU LDT Identity Management);
MCP servers then fetch service tokens automatically.

## 2. Connect a GovChat-NL app

From the bridge/workflow engine — engine-agnostic (Kestra in the testbed;
any MCP-capable or plain-HTTP client works): connect to
`http://host.docker.internal:8091/mcp` with header
`Authorization: Bearer beleidskompas-svc-tok`. Tools: `describe_process`,
`execute_process`, `get_job_status`. Catalog server (:8090) adds
`search_records`, `list_processes`; poc server (:8093) adds `ask_scan`,
`propose_scenarios`, `run_scenario_sweep`, `run_opportunity_map`, ….
(Kestra: `io.kestra.plugin.core.http.Request` against the MCP endpoint, or an
MCP plugin if the installed version ships one — MCP client support across
engines is still maturing; the HTTP/OGC seam always works.) Clients connect
from Docker via `http://host.docker.internal:8091/mcp` — this requires the
non-loopback bind from §1; on a loopback bind the MCP SDK's DNS-rebinding
protection rejects non-loopback Host headers with 421.

## 3. The two wired policy steps

| Beleidskompas step | MCP call | nLDT asset |
|---|---|---|
| Omgevingsanalyse | `execute_process` / recipe `beleidskompas-omgevingsanalyse` | `recipes/beleidskompas-omgevingsanalyse.json` |
| Substantiation Q&A (S4, cite-or-abstain) | `ask_scan` (poc server) | recipe `breda-scan-qa` → process `breda-scan-query` |

`ask_scan` returns the full S4 bundle (answer, citations, verdict/gates);
beleidskompas must quote only from it (seam S9, integration plan §6).

### 3a. Run annex for the policy document (S9)

Save a recipe execution, then generate the traceability annex (JSON + Markdown)
that travels with the exported document:

```bash
PYTHONPATH=. python -m services.cli run-recipe beleidskompas-omgevingsanalyse \
  --aoi-file examples/rijnsweerd/aoi.geojson \
  --input layerAUri=file://$(pwd)/examples/rijnsweerd/layer-a.geojson \
  --input layerBUri=file://$(pwd)/examples/rijnsweerd/layer-b.geojson \
  > /tmp/exec.json
PYTHONPATH=. python -m services.cli build-run-annex /tmp/exec.json --out annex.md
```

Beleidskompas (S9 contract): quote only figures that trace to an annex entry.

## 4. Verify

```bash
# unauthenticated MCP call must fail
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8091/mcp \
  -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
# → 401
```

BK-0 spike artifacts: [`BK0-FINDINGS.md`](BK0-FINDINGS.md),
[`kestra-bk0-bridge-flow.yaml`](kestra-bk0-bridge-flow.yaml) (throwaway
plain-HTTP bridge, superseded by the MCP path; engine pluggable — decision 6).
Governed demo (BK-1):
[`kestra-bk1-mcp-ask-scan.yaml`](kestra-bk1-mcp-ask-scan.yaml) — webhook →
MCP handshake on :8093 with bearer token → `tools/call ask_scan`; verified
2026-09-14 (status `answered`, `groundingFails: []`, jobId traceable, whole
chain a per-task audited Kestra execution).

## 5. Kestra bridge (BK-0 artifact)

The bridge flow runs on Kestra **2.0.1** at http://localhost:8086 (basic
auth via env config; webhook trigger unauthenticated; API tenant-scoped
under `/api/v1/main/...`) — see [`BK0-FINDINGS.md`](BK0-FINDINGS.md).

## 6. eID Wallet identity (W1/W5, mock)

EUDI-aligned wallet identity for nLDT: human wallets and agent virtual
wallets present administration-issued credentials at a token edge, with
EBW-style delegation per [16](../16-eid-wallet-identity.md) decision 10.
W1/W5 are the mock stage — a mock verifier and a mock agent credential;
the real OpenID4VP backend lands in W2 (and Keycloak-issued credentials
in W6). Design + roadmap: [`../16-eid-wallet-identity.md`](../16-eid-wallet-identity.md).

Run both services (add `NLDT_START_WALLET=1` to §1 instead to start them
with the rest of the stack):

```bash
cd nldt
NLDT_AUTH_WALLET_URL=http://localhost:8087 python -m services.auth_wallet.app &   # :8087
NLDT_AUTH_WALLET_URL=http://localhost:8087 python -m services.agent_wallet.app &  # :8088
```

Env vars: `NLDT_WALLET_TOKEN_TTL` (token lifetime seconds, default 300,
read by :8087), `NLDT_AUTH_WALLET_URL` (:8087 base URL, required by
:8088 — fails closed 503 without it), `NLDT_WALLET_INTROSPECT_URL`
(point nLDT services at introspection for `NLDT_AUTH_MODE=wallet`).

The verified chain — agent capability → agent-wallet token → introspectable
agent claims:

```bash
# 1. Agent virtual wallet exchanges a covered capability for a token (200)
curl -s -X POST localhost:8088/token -H 'Content-Type: application/json' \
  -d '{"capability":"breda-scan-query"}'
# → {"token":"...","expiresIn":300,"claims":{... agentId, assurance, ...}}

# 2. The auth edge introspects it (RFC 7662) — active agent claims
curl -s -X POST localhost:8087/introspect -d 'token=<token>'
# → {"active":true,"subject_type":"agent","agentId":"beleidskompas-svc",...}

# 3. Uncovered capability fails closed (403)
curl -s -o /dev/null -w "%{http_code}\n" -X POST localhost:8088/token \
  -H 'Content-Type: application/json' -d '{"capability":"rijnland-peil-conflict"}'
```

Honest caveat: these are ARF-*shaped* mock envelopes against a mock
verifier — useful for wiring, claims-schema and governance work, never a
production trust anchor. Protocol truth (real OpenID4VP) is pinned in W2.

### 6a. Trust-policy gates + wallet-verified approver (W3)

Enable (process adapter, `:8082`): point `NLDT_TRUST_POLICY_FILE` at a
policy file — copy
[`../data/trust-policy.example.json`](../data/trust-policy.example.json)
to start from. Without the env var nothing is gated (behavior identical
to pre-W3); with it, each entry under `"gates"` guards one process with
optional `minLoa` (low/substantial/high), `requiredRoles`,
`agentAssurance` (basic/attested/audited, agent executors only) and
`humanOnly` (agent executors refused). A configured-but-unreadable policy
file fails closed: every execution gets 503.

Enforced pre-execution in `POST /processes/{id}/execution`: a denial is a
403 with `{"gate": "<process>", "reason": "..."}` — reasons:
`missing_wallet_claims` (gated process, no wallet claims), `agent_not_allowed`
(`humanOnly`), `agent_capability_missing` (agent lacks the process id in
its `capabilities`), `agent_assurance_below_minimum`, `loa_below_minimum`,
`missing_role`. Agent executors on *any* gated process need the process id
in their claims `capabilities` (RP-side, independent of the agent
wallet's own check in §6).

**Approver header.** Agent runs on gated processes can carry a human
approver: add `X-nLDT-Approver-Token: <human wallet token>` (wallet auth
mode only; introspected like the caller token). The approver must be
`subject_type: human` and satisfy the same gate — refusals reuse the
reasons above prefixed `approver_` (plus `approver_not_human`). On
success the job's `actor` records both `executor` and `approver` claims.

```bash
# agent token from the agent virtual wallet (§6), gated process, approver header
curl -s -X POST localhost:8082/processes/breda-scan-query/execution \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $AGENT_NLDT_TOKEN" \
  -H "X-nLDT-Approver-Token: $HUMAN_WALLET_TOKEN" \
  -d '{"inputs": {...}}'
# 200: actor = {executor: <agent claims>, approver: <human claims>}
```
