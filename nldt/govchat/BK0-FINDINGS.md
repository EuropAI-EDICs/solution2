# BK-0 findings — GovChat-NL ↔ nLDT connectivity spike

Started: 2026-09-14. Decisions in force: nldt/14-beleidskompas-integration.md §10.

## nLDT side verified
- [x] S4 Q&A over `POST :8082/processes/breda-scan-query/execution` — jobId: 3342a8ee-4204-4aa1-a382-2784895521f0
- [x] GeoJSON export via `POST :8084/exports` — export URL: http://localhost:8084/exports/a19ecf460705.geojson

## GovChat-NL local instance
Verified 2026-09-14 (Task 2).

**GovChat-NL (OpenWebUI):**
- Clone: `/Users/marc/Projecten/GovChat-NL` @ `a358053356f49113066ea17d656746d6de202e2f` (v0.1.2, 2026-04-10). Their compose deploys the upstream image by default (`ghcr.io/open-webui/open-webui:${WEBUI_DOCKER_TAG-main}`), not a fork-built image.
- Running version: OpenWebUI **0.11.3** (`GET /api/version`; image `ghcr.io/open-webui/open-webui:main`).
- Containers (compose project `govchat-nl`): `open-webui` on `0.0.0.0:8080->8080` (healthy) + `ollama` sidecar (`ollama/ollama:latest`, port 11434 internal only). Started via `run-compose.sh` with the webui port set to 8080 (script/compose default is 3000) — no conflict with nLDT 8081–8085.
- Health: `curl http://localhost:8080/health` → **200**.
- Admin account: headless signup of `bk-admin@local.test` was refused — **403** `{"detail":"You do not have permission to access this resource. Please contact your administrator for assistance."}`. Cause: the compose volume `govchat-nl_open-webui` was reused from an earlier local run on this machine and already contains admin **`marc.minnee@gmail.com`** (role `admin`, created 2025-11-11); persisted config has `ui.enable_signup = false`. No account was reset or created; log in at http://localhost:8080 with the pre-existing admin.

**n8n:**
- Container `bk0-n8n`, image `n8nio/n8n` (official), version **2.38.7** (`docker exec bk0-n8n n8n --version`), `0.0.0.0:5678->5678`, `N8N_ENCRYPTION_KEY=dev-only-key` (dev only).
- Serving: `curl http://localhost:5678` → **200**.
- Onboarding state: **owner setup still pending** — DB has one shell `global:owner` row (email/firstName NULL, created at first container start 2026-09-14 10:32), 0 credentials, 0 workflows. First visit to http://localhost:5678 shows the owner-creation screen.
- Host reachability from inside n8n: `docker exec bk0-n8n sh -c "wget -q -O- http://host.docker.internal:8083/ && echo REACHABLE"` → nLDT catalog landing JSON (`{"title":"nLDT OGC API Records Catalog",...}`) + **REACHABLE**. `host.docker.internal` works unaided on this macOS Docker Desktop.

## Kestra → nLDT bridge
Verified 2026-09-14 (Task 3). Retitled from "n8n → nLDT bridge" — engine swapped to Kestra per decision 6 (spec §10: Apache-2.0, flow-as-code in git, per-task execution audit trail).

**n8n decommissioned:** `docker rm -f bk0-n8n` — nothing lost (owner setup was never completed, 0 workflows, 0 credentials; see Task 2 notes above).

**Kestra:**
- Version **2.0.1** (`kestra/kestra:latest`, pulled 2026-09-14), container `bk0-kestra`, `0.0.0.0:8086->8080`, `server local` mode (embedded H2 — no docker-compose/postgres fallback needed), volume `bk0-kestra-data`.
- Kestra 2.0 requires authentication (anonymous is gone): provisioned via `KESTRA_CONFIGURATION` env (`kestra.server.basic-auth.username=admin@kestra.io`, password meets the mandatory policy lower+upper+digit ≥8 — a first attempt without an uppercase char/digit was silently stored as a config error and left the API 401).
- API is **tenant-scoped** in 2.0: everything lives under `/api/v1/main/...` (the pre-2.0 `/api/v1/...` routes 404). The **webhook execution route is unauthenticated** (covered by default basic-auth openUrls), so an external caller (e.g. OpenWebUI) can trigger the bridge without credentials; reading executions/outputs needs the basic-auth credentials.
- Flow import: `POST /api/v1/main/flows` (create), `PUT /api/v1/main/flows/bk0/bk0-nldt-bridge` (update; POST → 409 once it exists).
- Flow: `nldt/govchat/kestra-bk0-bridge-flow.yaml` (namespace `bk0`, webhook trigger `spike`).

**Expression/plugin fixes vs. the task's starting-point YAML (2.0 changes):**
1. Flow-level `outputs` are a typed **list** (`- id / type: STRING / value`), not a map — map form fails import with a deserialization 422.
2. HTTP task type is `io.kestra.plugin.core.http.Request` — the `fs.http` namespace is gone in 2.0.
3. The Pebble `| json` **filter no longer exists** (first execution FAILED with `Filter [json] does not exist`) — replaced by the `fromJson()` function: e.g. `{{ fromJson(outputs['fetch_layer'].body).jobId }}`.

**Verified end-to-end (execution `1etuYl2yhYxnZdXpEHKwmL`, flow revision 2):**
- Trigger: `POST /api/v1/main/executions/webhook/bk0/bk0-nldt-bridge/spike` → state **SUCCESS**.
- Outputs (read via `GET /api/v1/main/outputs/executions/<id>` — the execution GET itself no longer embeds outputs in 2.0): `jobId` = `8368a631-fab9-4440-858d-a6383a499c67` (nLDT uuid), `exportUrl` = http://localhost:8084/exports/56b5b5fef5a4.geojson → **200**, valid GeoJSON FeatureCollection (rijnsweerd-zone-a).
- Audit record: `taskRunList` has 3 entries (`fetch_layer`, `publish_export`, `answer`, all SUCCESS, 1 attempt each); per-task inputs/outputs are retrievable, e.g. `GET /api/v1/main/outputs/tasks/<execId>/<taskRunId>` shows `publish_export`'s request URI, HTTP 200 and response body — the durable per-task audit trail decision 6 wanted. The two failed revision-1 executions remain in the log as iteration evidence.

**Remaining human step:** surfacing the bridge answer inside GovChat-NL/OpenWebUI needs Marc's admin login (pre-existing admin `marc.minnee@gmail.com`, see above); chat display would require an OpenWebUI-compatible (OpenAI-style) wrapper around the webhook. Reachability is proven: `docker exec open-webui python3 -c ... http://host.docker.internal:8086` → **200**. BK-1 supersedes this with MCP tools instead of an HTTP wrapper.

## Deviations / surprises
- Running OpenWebUI is the **upstream** `:main` image (0.11.3), not a GovChat-NL fork build — that is their compose default; GovChat-NL's repo version label (0.8.12 in package.json) does not match what runs.
- The `govchat-nl_open-webui` Docker volume predates this task (admin account from 2025-11-11), so the planned `bk-admin@local.test` first-run signup could not be created (403, signup disabled + owner exists). Pre-existing admin `marc.minnee@gmail.com` is used instead.
- The GovChat-NL compose includes an `ollama` sidecar that BK-0 does not use (nLDT is the intended backend via the Task 3 n8n bridge); it is left running as-is.
- n8n owner account has not been created yet (setup screen pending) — Task 3 needs it before building workflows.
