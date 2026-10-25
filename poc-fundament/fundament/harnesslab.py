"""Harness-lab motor: varianten, probe-bewijs en adoptie (harness2-methode,
eigen rechter).

De lab behandelt de agent-harness (prompts, slotgate-toolgrants, model-
pinnen) als versie-bare varianten: voorstellen (variantbestanden) worden
geprobeerd tegen deterministische tasksets, het bewijs komt in
probe-evidence.json, en adoptie (kandidaat → actief in het harnessregister)
mag alleen met voldoende bewijs. De adoptie zelf blijft een mensenknop
(V4-cultuur): deze motor doet het boekhoudwerk, nooit de knop.

Dependency-regel: dit module importeert alleen stdlib + (lazy) jsonschema;
adapters (bv. die van de agent-laag) worden door de CLI geïnjecteerd, niet
hier geïmporteerd.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_REGISTER = Path(__file__).resolve().parents[1] / "schemas" / "harnessregister.schema.json"
SCHEMA_VARIANT = Path(__file__).resolve().parents[1] / "schemas" / "harness-variant.schema.json"
SCHEMA_TASKSET = Path(__file__).resolve().parents[1] / "schemas" / "probe-taskset.schema.json"

EVIDENCE_FILENAME = "probe-evidence.json"

# Velden die per-probe verschillen en buiten canon-vergelijkingen vallen.
EVIDENCE_VOLATILE = {"probeId", "startedAt", "durationS", "runDir"}


class HarnessLabError(RuntimeError):
    """Variant, taskset, register of bewijs ongeldig, of adoptie geweigerd."""


def _load_json(schema_path: Path, path: Path) -> dict:
    import jsonschema

    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(doc, schema)
    except jsonschema.ValidationError as exc:
        where = ".".join(str(p) for p in exc.absolute_path) or "<top>"
        raise HarnessLabError(f"{Path(path).name}: {where}: {exc.message[:300]}") from exc
    return doc


def _require_unique_ids(entries: list[dict], wat: str) -> None:
    ids = [e["id"] for e in entries]
    if len(ids) != len(set(ids)):
        raise HarnessLabError(f"dubbele ids in de {wat}")


def _require_one_actief_per_target(harnesses: list[dict]) -> None:
    actief: dict[tuple, str] = {}
    for h in harnesses:
        if h.get("status", "actief") != "actief":
            continue
        key = (h["component"], h["target"])
        if key in actief:
            raise HarnessLabError(
                f"meerdere actieve entries voor target {h['target']!r} "
                f"({actief[key]} en {h['id']}) — precies één actief per target"
            )
        actief[key] = h["id"]


def load_harness_register(path: Path) -> dict:
    """Leest het harnessregister; luide faal op schema, dubbele ids of
    meerdere actieve entries voor hetzelfde target."""
    doc = _load_json(SCHEMA_REGISTER, path)
    _require_unique_ids(doc["harnesses"], "harnessregister")
    _require_one_actief_per_target(doc["harnesses"])
    return doc


def load_variant(path: Path) -> dict:
    """Leest één harness-variant; luide faal."""
    return _load_json(SCHEMA_VARIANT, path)


def load_taskset(path: Path) -> dict:
    """Leest één probe-taskset; luide faal, ook op dubbele taak-ids."""
    doc = _load_json(SCHEMA_TASKSET, path)
    _require_unique_ids(doc["tasks"], "taskset")
    return doc


def harness_entry_by_id(register: dict, entry_id: str) -> dict:
    for h in register["harnesses"]:
        if h["id"] == entry_id:
            return h
    raise KeyError(entry_id)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def new_probe_id(now: datetime | None = None) -> str:
    ts = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    return f"probe-{ts}"


def new_evidence(
    *,
    variant: dict,
    variant_path: Path,
    taskset: dict,
    taskset_path: Path,
    adapter: str,
    mode: str,
    probe_id: str | None = None,
    started_at: str | None = None,
) -> dict:
    """Evidence-kerndocument: wat is geprobeerd, met welke pinning."""
    components = []
    for comp in variant["components"]:
        entry = {"type": comp["type"], "target": comp["target"]}
        if "path" in comp:
            p = Path(comp["path"])
            entry["sha256"] = sha256_file(p if p.is_absolute() else Path(variant_path).parent / p)
        if "env" in comp:
            entry["env"] = dict(comp["env"])
        components.append(entry)
    return {
        "probeId": probe_id or new_probe_id(),
        "variantId": variant["id"],
        "variantTitle": variant["title"],
        "adapter": adapter,
        "mode": mode,
        "taskset": {"id": taskset["id"], "sha256": sha256_file(taskset_path)},
        "variant": {"sha256": sha256_file(variant_path), "components": components},
        "results": [],
        "score": {"passed": 0, "total": 0, "hardViolations": []},
        "verdict": "fail",
        "startedAt": started_at or datetime.now(timezone.utc).isoformat(),
        "durationS": 0.0,
    }


def record_task(
    evidence: dict,
    *,
    task_id: str,
    kind: str,
    checks: list[dict],
    metrics: dict | None = None,
) -> None:
    """Voeg één taakresultaat toe; checks zijn {check, pass, detail, hard?}."""
    task_pass = all(c["pass"] for c in checks)
    result = {"taskId": task_id, "kind": kind, "pass": task_pass, "checks": checks}
    if metrics:
        result["metrics"] = metrics
    evidence["results"].append(result)
    for c in checks:
        if c.get("hard") and not c["pass"]:
            evidence["score"]["hardViolations"].append(f"{task_id}:{c['check']}")


def finalize_evidence(evidence: dict, *, duration_s: float = 0.0) -> dict:
    """Score + verdict: pass = alle taken pass én geen harde schendingen."""
    total = len(evidence["results"])
    passed = sum(1 for r in evidence["results"] if r["pass"])
    evidence["score"]["passed"] = passed
    evidence["score"]["total"] = total
    evidence["verdict"] = "pass" if passed == total and not evidence["score"]["hardViolations"] else "fail"
    evidence["durationS"] = round(duration_s, 3)
    return evidence


def write_evidence(evidence: dict, out_dir: Path) -> Path:
    """Schrijf probe-evidence.json (kanoniek: sort_keys, stabiele volgorde)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / EVIDENCE_FILENAME
    path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def load_evidence(path: Path) -> dict:
    """Lees geschreven evidence terug (incl. verdict-hervatting uit de score)."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    for field in ("probeId", "variantId", "adapter", "mode", "verdict", "score"):
        if field not in doc:
            raise HarnessLabError(f"{Path(path).name}: veld {field!r} ontbreekt")
    return doc


def canon_evidence(doc: dict):
    """Volatile probe-meta (probeId, tijden) buiten vergelijking."""
    if isinstance(doc, dict):
        return {
            k: canon_evidence(v)
            for k, v in doc.items()
            if k not in EVIDENCE_VOLATILE
        }
    if isinstance(doc, list):
        return [canon_evidence(v) for v in doc]
    return doc


def render_probe_report(evidences: list[dict]) -> str:
    """Vergelijkingsmatrix over varianten (compose-stap). Byte-deterministisch:
    invoervolgorde is de enige volgorde, geen tijden of paden."""
    lines = [
        "# Harness-lab probe-rapport",
        "",
        "| variant | modus | verdict | taken pass | harde schendingen |",
        "|---|---|---|---|---|",
    ]
    for ev in evidences:
        s = ev["score"]
        hard = ", ".join(s["hardViolations"]) or "—"
        lines.append(
            f"| {ev['variantId']} | {ev['mode']} | {ev['verdict']} "
            f"| {s['passed']}/{s['total']} | {hard} |"
        )
    lines.append("")
    lines.append("## Per taak")
    lines.append("")
    lines.append("| variant | taak | soort | pass | gezakte checks |")
    lines.append("|---|---|---|---|---|")
    for ev in evidences:
        for r in ev["results"]:
            gezakt = ", ".join(c["check"] for c in r["checks"] if not c["pass"]) or "—"
            lines.append(
                f"| {ev['variantId']} | {r['taskId']} | {r['kind']} "
                f"| {'ja' if r['pass'] else 'NEE'} | {gezakt} |"
            )
    lines.append("")
    return "\n".join(lines)


def _slug(text: str) -> str:
    uit = []
    for ch in text.lower():
        if ch.isalnum():
            uit.append(ch)
        elif uit and uit[-1] != "-":
            uit.append("-")
    return "".join(uit).strip("-")


def adopt_register(
    *,
    register_path: Path,
    variant_path: Path,
    evidence_path: Path,
    allow_fake: bool = False,
    version: str = "1.0.0",
    actor: str = "harness-lab",
    now: datetime | None = None,
) -> dict:
    """Adoptie: promoveer een variant naar actieve register-entries.

    Weigert (luide HarnessLabError) bij: gezakt verdict, fake-modus zonder
    allow_fake, evidence die niet bij dit variantbestand hoort (sha-vergelijk),
    een target zonder actieve voorganger, of een reeds bestaande adoptie-id.
    De voorganger wordt verworpen (status verworpen, nota met opvolger); de
    adoptant krijgt adoptedFrom + probeEvidence. Schrijft atomisch en geeft
    het nieuwe registerdocument terug.
    """
    register = load_harness_register(register_path)
    variant = load_variant(variant_path)
    evidence = load_evidence(evidence_path)

    if evidence["verdict"] != "pass":
        raise HarnessLabError(
            f"adoptie geweigerd: evidence-verdict is {evidence['verdict']!r}, geen pass"
        )
    if evidence["mode"] == "fake" and not allow_fake:
        raise HarnessLabError(
            "adoptie geweigerd: fake-modus bewijst alleen de montuur; "
            "adoptie vereist llm-modus-bewijs (of expliciet --allow-fake)"
        )
    if evidence.get("variant", {}).get("sha256") != sha256_file(variant_path):
        raise HarnessLabError(
            "adoptie geweigerd: evidence hoort niet bij dit variantbestand "
            "(sha256 verschilt — probeer opnieuw na de probe)"
        )

    actief_by_target = {
        (h["component"], h["target"]): h
        for h in register["harnesses"]
        if h.get("status", "actief") == "actief"
    }
    probed_at = (now or datetime.now(timezone.utc)).isoformat()
    run_dir = evidence.get("runDir", "")
    comp_sha = {c["target"]: c.get("sha256") for c in evidence["variant"]["components"]}
    nieuwe = []
    for comp in variant["components"]:
        ctype = comp["type"]
        target = comp["target"]
        if ctype == "toolGrants":
            raise HarnessLabError(
                f"adoptie geweigerd: toolGrants-adoptie loopt via de "
                f"manifest-generatoren, niet via het register (target {target!r})"
            )
        if comp_sha.get(target) is not None:
            p = Path(comp["path"])
            bestand = p if p.is_absolute() else Path(variant_path).parent / p
            if comp_sha[target] != sha256_file(bestand):
                raise HarnessLabError(
                    f"adoptie geweigerd: component {target!r} is gewijzigd na de "
                    f"probe (sha256 verschilt) — probeer opnieuw met de nieuwe inhoud"
                )
        voorganger = actief_by_target.get((ctype, target))
        if voorganger is None:
            raise HarnessLabError(
                f"adoptie geweigerd: geen actieve register-entry voor "
                f"{ctype}:{target} — pin eerst de baselijn (scaffold)"
            )
        entry_id = f"{variant['id']}-{_slug(target)}"
        if any(h["id"] == entry_id for h in register["harnesses"]):
            raise HarnessLabError(
                f"adoptie geweigerd: entry {entry_id!r} bestaat al — "
                "maak een nieuwe variant met een nieuwe id"
            )
        if ctype == "prompt":
            # Adoptie = het live promptbestand wordt de varianttekst. De
            # verworpen voorganger houdt zijn eigen sha256, dus de oude
            # inhoud is altijd reconstrueerbaar (en in git).
            p = Path(comp["path"])
            bron = p if p.is_absolute() else Path(variant_path).parent / p
            live = register_path.parent / voorganger["artifact"]["path"]
            tekst = bron.read_text(encoding="utf-8")
            live.write_text(tekst, encoding="utf-8")
            artifact = {
                "kind": "promptFile",
                "path": voorganger["artifact"]["path"],
                "sha256": sha256_bytes(tekst.encode("utf-8")),
            }
        else:  # modelPin: activatie is het zetten van de env-var waar de run start
            artifact = {"kind": "envPin", "env": dict(comp["env"])}
        nieuwe.append({
            "id": entry_id,
            "title": f"{variant['title']} — {target}",
            "component": ctype,
            "target": target,
            "riskLevel": voorganger["riskLevel"],
            "version": version,
            "status": "actief",
            "artifact": artifact,
            "adoptedFrom": voorganger["id"],
            "probeEvidence": [{
                "probeId": evidence["probeId"],
                "runDir": run_dir,
                "mode": evidence["mode"],
                "verdict": evidence["verdict"],
                "probedAt": probed_at,
            }],
            "prov": {"adoptedBy": actor, "variantSha256": evidence["variant"]["sha256"]},
            "note": f"geadopteerd vanuit variant {variant['id']!r}",
        })
        voorganger["status"] = "verworpen"
        voorganger["note"] = (
            voorganger.get("note", "")
            + f" | vervangen door {entry_id} ({probed_at})"
        ).strip()

    register["harnesses"].extend(nieuwe)
    _require_one_actief_per_target(register["harnesses"])

    fd, tmp_name = tempfile.mkstemp(
        dir=str(register_path.parent), prefix=".harnessregister-", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        tmp.write_text(
            json.dumps(register, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, register_path)
    finally:
        if tmp.exists():
            tmp.unlink()
    return register
