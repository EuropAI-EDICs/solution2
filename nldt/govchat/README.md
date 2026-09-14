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

## 5. Kestra bridge (BK-0 artifact)

The bridge flow runs on Kestra **2.0.1** at http://localhost:8086 (basic
auth via env config; webhook trigger unauthenticated; API tenant-scoped
under `/api/v1/main/...`) — see [`BK0-FINDINGS.md`](BK0-FINDINGS.md).
