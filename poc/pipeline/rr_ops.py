"""Operator maps between RegelRecht execution ops and PoC FormalRule conditions."""
from __future__ import annotations

RR_TO_POC_OP = {
    "LESS_THAN_OR_EQUAL": "<=",
    "GREATER_THAN_OR_EQUAL": ">=",
    "LESS_THAN": "<",
    "GREATER_THAN": ">",
    "EQUALS": "==",
    "NOT_EQUALS": "!=",
}
POC_TO_RR_OP = {v: k for k, v in RR_TO_POC_OP.items()}
