#!/usr/bin/env python3
"""Extract the capability model from the LDT CitiVERSE EDIC Reference
Architecture (ReSpec sources) into nldt/edic/ra-capability-snapshot.json.

The EDIC publishes the RA as a ReSpec document plus an ArchiMate HTML
report; an exchangeable .archimate model is not in the repository. This
script therefore extracts from the ReSpec markdown, pinned to a commit so
the snapshot always records its provenance. Re-run with --commit <sha|latest>
to refresh; --check reports drift against the existing snapshot without
writing. See nldt/edic/ra-conformity.md for how the snapshot is consumed.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from datetime import date
from pathlib import Path

import httpx

REPO = "Geonovum/ldt-citiverse-edic-ra"
# Pinned commit of the current snapshot (2026-09-28). Override with --commit.
PINNED_COMMIT = "0e8519a8be89e4e2bb2a281c2256fdf5d248f145"
RA_MODEL = "id-ldt-fixed-arch-003"
FILES = [
    "h1-motivation.md",
    "h2-capabilities.md",
    "h3-business-application.md",
    "h4-application-technology.md",
]
OUT = Path(__file__).resolve().parents[1] / "edic" / "ra-capability-snapshot.json"


def fetch(commit: str) -> dict[str, str]:
    base = f"https://raw.githubusercontent.com/{REPO}/{commit}/respec/"
    texts: dict[str, str] = {}
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        for name in FILES:
            resp = client.get(base + name)
            resp.raise_for_status()
            texts[name] = resp.text
    return texts


def strip_md(line: str) -> str:
    return re.sub(r"(__|\*\*)", "", line).strip()


def sections(text: str) -> list[tuple[str, list[str]]]:
    """Split markdown into (heading-path, body lines) sections."""
    out: list[tuple[str, list[str]]] = []
    stack: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            depth = len(m.group(1))
            stack = stack[: depth - 1] + [strip_md(m.group(2))]
            out.append(("/".join(stack), []))
        elif out:
            out[-1][1].append(line)
    return out


def bullets(lines: list[str]) -> list[str]:
    return [strip_md(l.strip()[2:]) for l in lines if re.match(r"^\s*[-*]\s+", l)]


def labeled_lists(lines: list[str]) -> dict[str, list[str]]:
    """Group bullet items under the last preceding text line (the label)."""
    out: dict[str, list[str]] = {}
    label = "General"
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if re.match(r"^[-*]\s+", s):
            out.setdefault(label, []).append(strip_md(s[2:]))
        elif not s.startswith(("|", ">", "#", "![")):
            label = strip_md(s.rstrip(":"))
    return out


def numbered(lines: list[str]) -> list[str]:
    items: list[str] = []
    for line in lines:
        m = re.match(r"^\s*(\d+)\.\s+(.*)$", line)
        if m:
            items.append(strip_md(m.group(2)))
        elif items and line.strip():
            items[-1] += " " + strip_md(line)
    return items


def table_col(lines: list[str], col: int = 0) -> list[str]:
    vals: list[str] = []
    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) <= col or re.match(r"^[-: ]+$", cells[col] or "-"):
            continue
        vals.append(strip_md(cells[col]))
    return [v for v in vals if v not in ("Capability", "Requirement")]


def first_paragraph(lines: list[str]) -> str:
    for line in lines:
        if line.strip() and not line.strip().startswith(("|", "-", ">", "#")):
            return strip_md(line)
    return ""


def blockquote(lines: list[str]) -> str:
    for line in lines:
        if line.strip().startswith(">"):
            return strip_md(line.lstrip("> "))
    return ""


def parse_h2(text: str) -> dict:
    sec = {path: lines for path, lines in sections(text)}
    items = numbered(sec.get("Strategy/LDT CitiVERSE Capabilities", []))
    profiles = parse_profiles(sections(text))
    foundation = "Strategy/Types of Local Digital Twins/Conformance Profiles"
    return {
        "valueStream": {"sequentialStages": items[:4], "enablingCapabilities": items[4:]},
        "foundationRequirements": {
            "mandatoryCapabilities": bullets(sec.get(f"{foundation}/Mandatory Capabilities", [])),
            "mandatoryCharacteristics": bullets(sec.get(f"{foundation}/Mandatory Characteristics", [])),
        },
        "conformanceProfiles": profiles,
    }


def parse_profiles(secs: list[tuple[str, list[str]]]) -> list[dict]:
    by_leaf: dict[str, dict] = {}
    order: list[str] = []
    for path, lines in secs:
        parts = path.split("/")
        if len(parts) == 3 and parts[1] == "Types of Local Digital Twins" and parts[2].startswith("Profile "):
            m = re.match(r"Profile (\d+) [–-] (.+?)(?: LDT)?$", parts[2])
            if m and parts[2] not in by_leaf:
                by_leaf[parts[2]] = {"id": "P" + m.group(1), "name": m.group(2) + " LDT"}
                order.append(parts[2])
        elif len(parts) == 4 and parts[1] == "Types of Local Digital Twins":
            rec = by_leaf.get(parts[2])
            if not rec:
                continue
            sub = parts[3]
            if sub == "Purpose":
                rec["purpose"] = first_paragraph(lines)
            elif sub == "Primary Question":
                rec["primaryQuestion"] = blockquote(lines)
            elif sub == "Required Capabilities":
                rec["requiredCapabilities"] = table_col(lines, 0)
            elif sub == "Additional Required Capabilities":
                rec["additionalRequiredCapabilities"] = table_col(lines, 0)
            elif sub == "Typical Building Blocks":
                rec["buildingBlocks"] = bullets(lines)
            elif sub == "Typical Outputs":
                rec["outputs"] = bullets(lines)
    return [by_leaf[k] for k in order]


def parse_h3(text: str) -> dict:
    business: list[dict] = []
    application: list[dict] = []
    standards: dict[str, dict[str, list[str]]] = {}
    for path, lines in sections(text):
        parts = path.split("/")
        if len(parts) == 2 and parts[0] == "Business Service Architecture" and parts[1] != "Business Services as Public Capabilities":
            business.append({"name": parts[1], "purpose": first_paragraph(lines), "typicalFunctions": [], "supportedProfiles": []})
        elif len(parts) == 3 and parts[0] == "Business Service Architecture":
            svc = next((b for b in business if b["name"] == parts[1]), None)
            if svc and parts[2] == "Typical Functions":
                svc["typicalFunctions"] = bullets(lines)
            elif svc and parts[2] == "Supported LDT Profiles":
                svc["supportedProfiles"] = bullets(lines)
            elif svc and parts[2] == "Purpose":
                svc["purpose"] = first_paragraph(lines)
        elif len(parts) == 2 and parts[0] == "Application Service Architecture":
            application.append({"name": parts[1], "responsibilities": [], "buildingBlocks": [], "formats": []})
        elif len(parts) == 3 and parts[0] == "Application Service Architecture":
            svc = next((a for a in application if a["name"] == parts[1]), None)
            if svc and parts[2] == "Responsibilities":
                svc["responsibilities"] = bullets(lines)
            elif svc and parts[2] == "Typical Building Blocks":
                svc["buildingBlocks"] = bullets(lines)
            elif svc and parts[2] in ("Supported Formats", "Typical Technologies"):
                svc["formats"] = bullets(lines)
        elif len(parts) == 2 and parts[0] == "Open Interfaces and Standards":
            standards[parts[1]] = labeled_lists(lines)
        elif len(parts) == 3 and parts[0] == "Information Models and Semantic Assets" and parts[2] == "Examples":
            standards["Information Models and Semantic Assets"] = {"Examples": bullets(lines)}
    return {"businessServices": business, "applicationServices": application, "standards": standards}


def build_snapshot(texts: dict[str, str], commit: str) -> dict:
    snap: dict = {"raModel": RA_MODEL}
    snap.update(parse_h2(texts["h2-capabilities.md"]))
    snap.update(parse_h3(texts["h3-business-application.md"]))
    snap["source"] = {
        "repo": f"https://github.com/{REPO}",
        "commit": commit,
        "fetched": date.today().isoformat(),
        "files": {n: f"https://raw.githubusercontent.com/{REPO}/{commit}/respec/{n}" for n in FILES},
        "archimateReport": "https://geonovum.github.io/ldt-citiverse-edic-ra/archimate/",
        "caveat": "Archimate HTML report only; no .archimate/Open Exchange file in the repo. "
                  "Coded subcapabilities (DS.*/IR.*/IC.*/MG.*/TW.*/UX.*) and MIMs 0-8 exist in the "
                  "ArchiMate model but not (yet) in the ReSpec text, so they are absent from this snapshot. "
                  "Repo states: temporary, first draft, no licence noted — record provenance, do not republish.",
    }
    return snap


def drift(old: dict, new: dict) -> list[str]:
    a = json.dumps(old, indent=1, sort_keys=True).splitlines()
    b = json.dumps(new, indent=1, sort_keys=True).splitlines()
    return [l for l in difflib.unified_diff(a, b, lineterm="", n=0)
            if (l.startswith("+") or l.startswith("-")) and not l.startswith(("+++", "---"))]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commit", default=PINNED_COMMIT, help="commit sha or 'latest'")
    ap.add_argument("--check", action="store_true", help="report drift vs existing snapshot; no write")
    args = ap.parse_args()

    commit = args.commit
    if commit == "latest":
        with httpx.Client(timeout=60.0) as client:
            commit = client.get(f"https://api.github.com/repos/{REPO}/commits/main").json()["sha"]

    snap = build_snapshot(fetch(commit), commit)
    profiles = [p["name"] for p in snap["conformanceProfiles"]]
    if not profiles or len(snap["businessServices"]) < 3 or not snap["standards"].get("API Standards"):
        print("ERROR: parse looks incomplete — RA structure changed?", file=sys.stderr)
        return 1

    print(f"commit {commit[:12]} · profiles: {', '.join(profiles)}")
    print(f"business services: {len(snap['businessServices'])} · application services: {len(snap['applicationServices'])} · standards groups: {len(snap['standards'])}")

    if OUT.exists():
        old = json.loads(OUT.read_text())
        d = drift(old, snap)
        if not d:
            print("no drift vs existing snapshot (dates aside)")
        else:
            print(f"DRIFT vs snapshot at {old.get('source', {}).get('commit', '?')[:12]}: {len(d)} changed lines")
            for line in d[:40]:
                print(" ", line[:160])
    if args.check:
        return 0
    OUT.write_text(json.dumps(snap, indent=2, ensure_ascii=False) + "\n")
    print(f"written {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
