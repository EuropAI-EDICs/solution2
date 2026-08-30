"""Typed data contracts for the LDT Toolbox PoC planning plane.

Implements the JSON Schema contracts of MULTI_AGENT_PLAN.md section 5 as plain
dataclasses with to/from-dict conversion and schema validation, so that every
agent boundary in the PoC emits schema-validated JSON (the V0 syntactic gate).

Schemas live in poc/schemas/*.schema.json (draft 2020-12, self-contained:
no cross-file $refs, so plain ``jsonschema`` validation needs no registry).

Usage::

    from pipeline import contracts

    card = contracts.NormCard.from_dict(payload)   # validates first
    contracts.validate(card.to_dict(), "norm-card")
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

import jsonschema

POC_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = POC_ROOT / "schemas"

SCHEMA_NAMES = (
    "opportunity-map-request",
    "norm-card",
    "formal-rule",
    "zone-result",
    "validation-report",
    "decision-table",
)

#: domains where these contracts are deliberately strict (see schema files)
OBJECT_TYPES = ("wind_turbine", "solar_field", "forest_planting", "biomass_installation", "energy_storage")
ZONE_SEMANTICS = ("inclusion", "exclusion", "conditional", "attention", "compensation", "none")
RULE_STATUSES = ("formalized", "ambiguous", "rejected")


class ContractError(ValueError):
    """Raised when an artifact does not satisfy its JSON Schema contract."""


# ---------------------------------------------------------------------------
# schema loading and validation
# ---------------------------------------------------------------------------

def _check_schema_name(schema_name: str) -> None:
    if schema_name not in SCHEMA_NAMES:
        raise ContractError(
            f"unknown schema name {schema_name!r}; expected one of {SCHEMA_NAMES}"
        )


@lru_cache(maxsize=None)
def load_schema(schema_name: str) -> Dict[str, Any]:
    """Load and meta-validate one PoC schema by name; cached."""
    _check_schema_name(schema_name)
    path = SCHEMA_DIR / f"{schema_name}.schema.json"
    if not path.is_file():
        raise ContractError(f"schema file missing: {path}")
    with path.open(encoding="utf-8") as fh:
        schema = json.load(fh)
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except jsonschema.SchemaError as exc:  # pragma: no cover - authoring guard
        raise ContractError(
            f"schema {schema_name!r} is not valid draft 2020-12: {exc.message}"
        ) from exc
    return schema


@lru_cache(maxsize=None)
def _validator(schema_name: str) -> jsonschema.Draft202012Validator:
    return jsonschema.Draft202012Validator(load_schema(schema_name))


def validate(instance: Any, schema_name: str) -> None:
    """Validate a plain-python instance against a named PoC schema.

    Raises ContractError with the accumulated human-readable error list
    (location + message per error) so agent boundaries can log precisely
    why an artifact was rejected.
    """
    _check_schema_name(schema_name)
    errors = sorted(
        _validator(schema_name).iter_errors(instance),
        key=lambda err: [str(p) for p in err.absolute_path],
    )
    if not errors:
        return
    parts = []
    for err in errors[:12]:
        location = "/".join(str(p) for p in err.absolute_path) or "$"
        parts.append(f"at {location}: {err.message}")
    suffix = f" (+{len(errors) - 12} more errors)" if len(errors) > 12 else ""
    raise ContractError(
        f"artifact failed schema {schema_name!r}: " + "; ".join(parts) + suffix
    )


# ---------------------------------------------------------------------------
# dataclass plumbing
# ---------------------------------------------------------------------------

def _clean(value: Any) -> Any:
    """Recursively drop None values so optional keys simply disappear."""
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    return value


def _build(cls: type, data: Mapping[str, Any]) -> Any:
    """Construct a dataclass from a dict, coercing nested dicts/lists via __nested__."""
    if not isinstance(data, dict):
        raise ContractError(f"{cls.__name__}.from_dict expects a dict, got {type(data).__name__}")
    nested = getattr(cls, "__nested__", {})
    nested_maps = getattr(cls, "__nested_maps__", {})
    known = {f.name for f in fields(cls)}
    kwargs: Dict[str, Any] = {}
    unknown: List[str] = []
    for key, value in data.items():
        if key in nested_maps and isinstance(value, dict):
            value = {ik: _build(nested_maps[key], iv) for ik, iv in value.items()}
        elif key in nested and value is not None:
            nested_type = nested[key]
            if isinstance(value, dict):
                value = _build(nested_type, value)
            elif isinstance(value, list):
                value = [
                    _build(nested_type, item) if isinstance(item, dict) else item
                    for item in value
                ]
        if key in known:
            kwargs[key] = value
        else:
            unknown.append(key)
    if unknown:
        raise ContractError(f"{cls.__name__}: unknown field(s) {sorted(unknown)}")
    try:
        return cls(**kwargs)
    except TypeError as exc:
        raise ContractError(f"{cls.__name__}: {exc}") from exc


class _ContractMixin:
    SCHEMA_NAME: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _clean(asdict(self))  # type: ignore[arg-type]

    def validate(self) -> None:
        validate(self.to_dict(), self.SCHEMA_NAME)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]):
        cleaned = _clean(dict(data))
        validate(cleaned, cls.SCHEMA_NAME)
        return _build(cls, cleaned)


# ---------------------------------------------------------------------------
# OpportunityMapRequest (planning-plane entry)
# ---------------------------------------------------------------------------

@dataclass
class EffortBudget:
    maxSubagents: int
    maxCostEur: Optional[float] = None
    maxLatencyS: Optional[float] = None


@dataclass
class AreaOfInterest:
    geometry: Union[Dict[str, Any], str]
    crs: str = "EPSG:28992"


@dataclass
class OpportunityMapRequest(_ContractMixin):
    SCHEMA_NAME = "opportunity-map-request"
    __nested__ = {"areaOfInterest": AreaOfInterest, "effortBudget": EffortBudget}

    id: str
    objectType: str
    areaOfInterest: AreaOfInterest
    policyStage: str
    effortBudget: EffortBudget
    requestedAt: str
    ambitions: Optional[List[str]] = None
    requestedBy: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# NormCard (Norm Analyst output)
# ---------------------------------------------------------------------------

@dataclass
class NormCardSource:
    docId: str
    article: str
    version: str
    quote: str
    uri: str
    quoteLanguage: str = "nl"
    retrievedAt: Optional[str] = None


@dataclass
class AppliesTo:
    objectType: str
    contextTags: Optional[List[str]] = None


@dataclass
class GeoBinding:
    zoneIds: List[str]
    geometrySource: str
    gioJoinId: Optional[str] = None
    caveat: Optional[str] = None


@dataclass
class NormCard(_ContractMixin):
    SCHEMA_NAME = "norm-card"
    __nested__ = {"source": NormCardSource, "appliesTo": AppliesTo, "geoBinding": GeoBinding}

    id: str
    evidenceId: str
    claim: str
    source: NormCardSource
    instrument: str
    legalForce: str
    theme: str
    confidence: float
    verified: bool
    extractedBy: str
    extractedAt: str
    appliesTo: AppliesTo
    geoBinding: Optional[GeoBinding] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# FormalRule (Norm Formalizer output)
# ---------------------------------------------------------------------------

@dataclass
class Condition:
    parameter: str
    operator: str
    value: Union[float, int, str, bool]
    unit: Optional[str] = None


@dataclass
class ZoneSelector:
    zoneIds: List[str]
    geometrySource: str
    selection: str = "within"
    gioJoinId: Optional[str] = None
    bufferDistanceM: Optional[float] = None
    derivedFrom: Optional[str] = None
    caveat: Optional[str] = None


@dataclass
class FormalRule(_ContractMixin):
    SCHEMA_NAME = "formal-rule"
    __nested__ = {"appliesTo": AppliesTo, "zoneSelector": ZoneSelector, "conditions": Condition}

    id: str
    normCardId: str
    status: str
    ruleType: str
    zoneSemantics: str
    appliesTo: AppliesTo
    executableRef: str
    formalizedBy: str
    formalizedAt: str
    zoneSelector: Optional[ZoneSelector] = None
    conditions: Optional[List[Condition]] = None
    relatedNormCardIds: Optional[List[str]] = None
    reason: Optional[str] = None
    rationale: Optional[str] = None


# ---------------------------------------------------------------------------
# ZoneResult (Geo Analyst output)
# ---------------------------------------------------------------------------

@dataclass
class ZoneResultGeometry:
    format: str
    payload: Union[Dict[str, Any], str]
    crs: str = "EPSG:28992"


@dataclass
class ZoneResult(_ContractMixin):
    SCHEMA_NAME = "zone-result"
    __nested__ = {"geometry": ZoneResultGeometry}

    id: str
    ruleIds: List[str]
    operation: str
    geometry: ZoneResultGeometry
    geometryValid: bool
    provenance: str
    computedBy: str
    computedAt: str
    areaKm2: Optional[float] = None
    operands: Optional[List[str]] = None
    requestId: Optional[str] = None


# ---------------------------------------------------------------------------
# ValidationReport (Critic/Validator output)
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    id: str
    status: str
    detail: Optional[str] = None
    evidenceRefs: Optional[List[str]] = None


@dataclass
class LevelResult:
    status: str
    checks: Optional[List[CheckResult]] = None
    notes: Optional[str] = None


@dataclass
class EvidenceRef:
    ref: str
    note: Optional[str] = None


@dataclass
class ValidationReport(_ContractMixin):
    SCHEMA_NAME = "validation-report"
    __nested__ = {"evidence": EvidenceRef}
    __nested_maps__ = {"levels": LevelResult}

    id: str
    artifactId: str
    artifactType: str
    levels: Dict[str, LevelResult]
    verdict: str
    evaluatorRun: str
    evaluatedAt: str
    evidence: Optional[List[EvidenceRef]] = None


# ---------------------------------------------------------------------------
# DecisionTable (Explainer output)
# ---------------------------------------------------------------------------

@dataclass
class DecisionTable(_ContractMixin):
    SCHEMA_NAME = "decision-table"

    id: str
    title: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    generatedBy: str
    generatedAt: str
    provenance: str
    requestId: Optional[str] = None


__all__ = [
    "SCHEMA_NAMES",
    "SCHEMA_DIR",
    "ContractError",
    "load_schema",
    "validate",
    "OpportunityMapRequest",
    "AreaOfInterest",
    "EffortBudget",
    "NormCard",
    "NormCardSource",
    "AppliesTo",
    "GeoBinding",
    "FormalRule",
    "Condition",
    "ZoneSelector",
    "ZoneResult",
    "ZoneResultGeometry",
    "ValidationReport",
    "LevelResult",
    "CheckResult",
    "EvidenceRef",
    "DecisionTable",
]
