#!/usr/bin/env python3
"""Demo-portaal: één website die alle LDT-toolbox-demo's aanroept.

Offline, deterministisch, geen API-sleutels — stdlib http.server (zelfde
patroon als deep-agents/live_server.py). Start:

    cd /Users/marc/Projecten/ldttoolbox
    nldt/.venv/bin/python demo/server.py
    # → http://127.0.0.1:8766/

Endpoints (allemaal GET, behalve waar POST logisch is — de portal gebruikt
uitsluitend GET zodat elke demo ook als losse URL deellinkbaar is):
  /                          portal.html
  /api/matrix?poc=minigim|nspd          agent–fase–tool matrix (markdown)
  /api/runs                             demo-runs van de gebiedscheck
  /api/run/minigim                      draai de gebiedscheck (cache-first)
  /api/artifact?run=<id>&name=<naam>    run-artefact (report.html, fase-matrix.md, …)
  /api/verify                           transport-bewijs (processes + a2a)
  /api/golden                           golden-reproductie (M2-bewijs)
  /api/suite?name=fundament|minigim|nspd|deepagents   test-suite
  /api/status                           ping op deep-agents-dashboard (8765) en NSPD-viewer (8000)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
PORT = int(os.environ.get("DEMO_PORT", "8766"))
VENV_PY = str(ROOT / "nldt" / ".venv" / "bin" / "python")
RUNS_DIR = ROOT / "poc-minigim" / "runs"
ARTIFACT_WHITELIST = {"report.html", "fase-matrix.md", "validation.json",
                      "run_summary.json", "prov.json"}
RUN_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-minigim-gebiedscheck$")


def _run(args: list[str], cwd: Path, timeout: int = 600,
         env_extra: dict[str, str] | None = None) -> dict:
    env = {**os.environ, **(env_extra or {})}
    try:
        proc = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True,
                              timeout=timeout, env=env)
        return {"ok": proc.returncode == 0, "rc": proc.returncode,
                "stdout": proc.stdout[-8000:], "stderr": proc.stderr[-4000:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "rc": -1, "stdout": "", "stderr": f"timeout na {timeout}s"}


def _matrix(poc: str) -> dict:
    home = {"minigim": ROOT / "poc-minigim", "nspd": ROOT / "poc-nspd"}[poc]
    # bewust als subprocess: de server zelf importeert geen shapely/GEOS —
    # native libs in het ouderproces + fork laten kinderen op macOS segfaillen
    code = ("import sys; sys.path.append(r'{fund}'); "
            "from fundament.manifest import load_manifest; "
            "from fundament.matrix import render_matrix; "
            "print(render_matrix(load_manifest(r'{manif}')), end='')"
            ).format(fund=ROOT / "poc-fundament", manif=home / "fase-manifest.json")
    out = _run([VENV_PY, "-c", code], cwd=ROOT, timeout=120)
    return {"poc": poc, "markdown": out.get("stdout", ""),
            "ok": out["ok"], "stderr": out["stderr"]}


def _latest_run() -> str | None:
    runs = sorted(p.name for p in RUNS_DIR.glob("*-minigim-gebiedscheck") if p.is_dir())
    return runs[-1] if runs else None


def _minigim_run() -> dict:
    out = _run([VENV_PY, str(ROOT / "poc-minigim" / "run.py"),
                "--aoi", str(ROOT / "poc-minigim" / "examples" / "plangrens-breda-teteringen.28992.geojson"),
                "--label", "Demo-portaal"], cwd=ROOT, timeout=600)
    out["run"] = _latest_run()
    return out


def _verify() -> dict:
    return _run([VENV_PY, "tools/verify_transports.py"],
                cwd=ROOT / "poc-minigim", timeout=300,
                env_extra={"PYTHONPATH": str(ROOT / "nldt")})


def _golden() -> dict:
    return _run([VENV_PY, "-m", "unittest", "tests.test_golden", "-v"],
                cwd=ROOT / "poc-minigim", timeout=300)


def _suite(name: str) -> dict:
    suite = {
        "fundament": {"args": [VENV_PY, "-m", "unittest", "discover", "-s", "tests", "-q"],
                      "cwd": ROOT / "poc-fundament"},
        "minigim": {"args": [VENV_PY, "-m", "unittest", "discover", "-s", "tests", "-q"],
                    "cwd": ROOT / "poc-minigim"},
        "nspd": {"args": [str(ROOT / "poc-nspd" / ".venv" / "bin" / "python"),
                          "-m", "pytest", "-q"],
                 "cwd": ROOT / "poc-nspd"},
        "deepagents": {"args": [VENV_PY, "-m", "pytest", "tests", "-q"],
                       "cwd": ROOT / "deep-agents",
                       "env": {"PYTHONPATH": str(ROOT / "deep-agents" / ".venv" / "lib" / "python3.14"
                                                 / "site-packages")}},
    }[name]
    return _run(suite["args"], cwd=suite["cwd"], timeout=900,
                env_extra=suite.get("env"))


def _status() -> dict:
    def ping(url: str) -> bool:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as resp:
                return resp.status == 200
        except Exception:  # noqa: BLE001 — status is status
            return False
    return {"deepagents_dashboard": ping("http://127.0.0.1:8765/"),
            "nspd_viewer": ping("http://127.0.0.1:8000/")}


class Handler(BaseHTTPRequestHandler):
    def _json(self, payload: dict, code: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path, content_type: str) -> None:
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 — http.server-conventie
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        route = parsed.path
        try:
            if route == "/":
                return self._file(HERE / "portal.html", "text/html; charset=utf-8")
            if route == "/api/matrix":
                return self._json(_matrix(qs.get("poc", ["minigim"])[0]))
            if route == "/api/runs":
                return self._json({"runs": sorted((p.name for p in RUNS_DIR.glob("*-minigim-gebiedscheck")
                                                   if p.is_dir()), reverse=True)[:20]})
            if route == "/api/run/minigim":
                return self._json(_minigim_run())
            if route == "/api/artifact":
                run, name = qs.get("run", [""])[0], qs.get("name", [""])[0]
                if not RUN_ID_RE.match(run) or name not in ARTIFACT_WHITELIST:
                    return self._json({"error": "onbekende run of artefact"}, 400)
                path = RUNS_DIR / run / name
                if not path.is_file():
                    return self._json({"error": "artefact bestaat niet"}, 404)
                ctype = "text/html; charset=utf-8" if name.endswith(".html") else \
                    "text/markdown; charset=utf-8" if name.endswith(".md") else \
                    "application/json; charset=utf-8"
                return self._file(path, ctype)
            if route == "/api/verify":
                return self._json(_verify())
            if route == "/api/golden":
                return self._json(_golden())
            if route == "/api/suite":
                name = qs.get("name", [""])[0]
                if name not in {"fundament", "minigim", "nspd", "deepagents"}:
                    return self._json({"error": "onbekende suite"}, 400)
                return self._json(_suite(name))
            if route == "/api/status":
                return self._json(_status())
            return self._json({"error": "onbekende route"}, 404)
        except Exception as exc:  # noqa: BLE001 — luide fout naar de portal
            return self._json({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 500)

    def log_message(self, fmt, *args):  # rustiger loggen
        sys.stderr.write("[demo] " + fmt % args + "\n")


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"demo-portaal → http://127.0.0.1:{PORT}/  (Ctrl-C om te stoppen)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
