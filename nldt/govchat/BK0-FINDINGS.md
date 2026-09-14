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

## n8n → nLDT bridge
(fill in Task 3)

## Deviations / surprises
- Running OpenWebUI is the **upstream** `:main` image (0.11.3), not a GovChat-NL fork build — that is their compose default; GovChat-NL's repo version label (0.8.12 in package.json) does not match what runs.
- The `govchat-nl_open-webui` Docker volume predates this task (admin account from 2025-11-11), so the planned `bk-admin@local.test` first-run signup could not be created (403, signup disabled + owner exists). Pre-existing admin `marc.minnee@gmail.com` is used instead.
- The GovChat-NL compose includes an `ollama` sidecar that BK-0 does not use (nLDT is the intended backend via the Task 3 n8n bridge); it is left running as-is.
- n8n owner account has not been created yet (setup screen pending) — Task 3 needs it before building workflows.
