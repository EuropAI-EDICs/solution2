"""Serve Agent Skills (SEP-2640) as MCP resources under skill://.

Skills live on disk under ``nldt/skills/poc/<name>/`` and are co-located on
``nldt-poc-mcp`` next to PoC tools. See ``nldt/20-poc-mcp-skills.md``.
"""

from __future__ import annotations

import json
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp.server.extension import Extension

SKILLS_EXTENSION_ID = "io.modelcontextprotocol/skills"
SKILL_URI_PREFIX = "skill://nldt/poc"
INDEX_URI = "skill://index.json"
INDEX_SCHEMA = "https://schemas.agentskills.io/discovery/0.2.0/schema.json"

_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(.*?)\n---\s*\n?",
    re.DOTALL,
)


@dataclass(frozen=True)
class SkillFile:
    """One file inside a skill directory."""

    skill_name: str
    relpath: str  # posix path relative to skill root
    path: Path
    uri: str
    mime_type: str
    name: str | None
    description: str


def default_skills_root() -> Path:
    """``nldt/skills/poc`` relative to this package."""
    return Path(__file__).resolve().parents[2] / "skills" / "poc"


def parse_frontmatter(text: str) -> dict[str, str]:
    """Minimal YAML frontmatter parser for ``name`` / ``description`` fields."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    out: dict[str, str] = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key:
            out[key] = value
    return out


def _mime_for(path: Path) -> str:
    if path.name == "SKILL.md" or path.suffix.lower() == ".md":
        return "text/markdown"
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def discover_skill_files(skills_root: Path | None = None) -> list[SkillFile]:
    """Walk skill directories; each must contain SKILL.md with matching ``name``."""
    root = skills_root or default_skills_root()
    if not root.is_dir():
        return []

    files: list[SkillFile] = []
    for skill_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        meta = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        skill_name = meta.get("name") or skill_dir.name
        if skill_name != skill_dir.name:
            raise ValueError(
                f"Skill frontmatter name {skill_name!r} must equal directory "
                f"{skill_dir.name!r} ({skill_md})"
            )
        description = meta.get("description") or skill_name

        for path in sorted(skill_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.name.startswith(".") or "__pycache__" in path.parts:
                continue
            rel = path.relative_to(skill_dir).as_posix()
            uri = f"{SKILL_URI_PREFIX}/{skill_name}/{rel}"
            is_root = rel == "SKILL.md"
            files.append(
                SkillFile(
                    skill_name=skill_name,
                    relpath=rel,
                    path=path,
                    uri=uri,
                    mime_type=_mime_for(path),
                    name=skill_name if is_root else None,
                    description=description if is_root else f"{skill_name}/{rel}",
                )
            )
    return files


def build_skill_index(skills_root: Path | None = None) -> dict[str, Any]:
    """SEP-2640 ``skill://index.json`` payload (skill-md entries only)."""
    seen: dict[str, SkillFile] = {}
    for sf in discover_skill_files(skills_root):
        if sf.relpath == "SKILL.md":
            seen[sf.skill_name] = sf
    skills = [
        {
            "name": sf.skill_name,
            "type": "skill-md",
            "description": sf.description,
            "url": sf.uri,
        }
        for sf in sorted(seen.values(), key=lambda s: s.skill_name)
    ]
    return {"$schema": INDEX_SCHEMA, "skills": skills}


def index_json(skills_root: Path | None = None) -> str:
    return json.dumps(build_skill_index(skills_root), indent=2)


class SkillsExtension(Extension):
    """SEP-2640 capability advertisement (empty settings)."""

    identifier = SKILLS_EXTENSION_ID


POC_SKILLS_INSTRUCTIONS = (
    "Default entry: read skill://nldt/poc/nldt-poc-lifecycle/SKILL.md "
    "(discover → lake → scenarios → demo). Then use nldt-poc-router or a domain "
    "skill (breda-scan, utrecht-scenario, rijnland-peilen). Enumerate via "
    "skill://index.json. Skills are instructions only — dispose via registered "
    "tools/processes."
)


def register_poc_skills(mcp: Any, skills_root: Path | None = None) -> list[SkillFile]:
    """Register ``skill://index.json`` and every skill file on an MCPServer."""
    root = skills_root or default_skills_root()
    files = discover_skill_files(root)

    @mcp.resource(
        INDEX_URI,
        name="skill-index",
        description="SEP-2640 Agent Skills index for nLDT PoC playbooks",
        mime_type="application/json",
    )
    def skill_index() -> str:
        return index_json(root)

    for sf in files:
        _register_skill_file(mcp, sf)

    return files


def _register_skill_file(mcp: Any, sf: SkillFile) -> None:
    path = sf.path
    uri = sf.uri
    res_name = sf.name or sf.relpath.replace("/", "-")
    description = sf.description
    mime_type = sf.mime_type
    meta = (
        {"io.modelcontextprotocol.skills/skillName": sf.skill_name}
        if sf.relpath == "SKILL.md"
        else None
    )

    @mcp.resource(
        uri,
        name=res_name,
        description=description,
        mime_type=mime_type,
        meta=meta,
    )
    def _reader() -> str:
        return path.read_text(encoding="utf-8")

    _reader.__name__ = (
        f"skill_{sf.skill_name}_{sf.relpath}".replace("/", "_").replace(".", "_")
    )
