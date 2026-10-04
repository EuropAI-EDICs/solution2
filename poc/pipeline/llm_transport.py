"""poc/pipeline/llm_transport.py — GE COMMITTE no-network compat-shim.

Wat dit is: het minimale transport-contract (``LLMTransport`` /
``LLMTransportError`` / ``extract_json_object`` / ``model_slug``) dat het
gecommitte ``pipeline/norm_llm.py`` op modulniveau importeert. De volledige
transport-implementatie is een WIP-module uit de hoofdwerkmap (stash
"s7-pre: scenario_author llm_transport WIP", zie
``.superpowers/sdd/final-review-d0720f7..6088973.md``) en ontbreekt op deze
branch — terwijl ``poc/run.py`` via ``pipeline.norm_llm`` op dit bestand
wacht: een verse checkout kon run.py en de testcollectie niet eens laden.

Waarom gecommit als shim (en niet als lazy import in norm_llm): kleinste
risico — de importketen blijft ongewijzigd, alleen de levering verandert.
De shim doet ZELF NOOIT een netwerkcall: zonder endpoint is ``available``
False (run.py valt luid terug op de deterministische benen), zonder
geïnjecteerde ``llm_call`` raiset ``chat()`` — elk netwerkverkeer blijft
wat het was: expliciet geconfigureerd en buiten dit bestand.
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, Optional


class LLMTransportError(ValueError):
    """Transport/config failure (mirrors the real module's exception)."""


class LLMTransport:
    """Config holder + call dispatcher for the S1/S2 seams (no-network shim)."""

    def __init__(self, env_prefix: str, *, endpoint: Optional[str] = None,
                 model: Optional[str] = None, timeout: Optional[float] = None,
                 llm_call: Optional[Callable[..., str]] = None,
                 max_tokens: int = 2048) -> None:
        self.env_prefix = env_prefix
        self.endpoint = endpoint or os.environ.get(f"{env_prefix}_ENDPOINT")
        self.model = model or os.environ.get(f"{env_prefix}_MODEL", "unknown")
        self.timeout = timeout
        self.max_tokens = max_tokens
        self._llm_call = llm_call

    @property
    def available(self) -> bool:
        return bool(self.endpoint)

    def chat(self, system: str, user: str) -> str:
        if self._llm_call is None:
            raise LLMTransportError(
                "llm_transport shim: no llm_call injected (transport unavailable)"
            )
        return self._llm_call(self.endpoint, self.model, system, user, self.timeout)


def extract_json_object(raw: str) -> Dict[str, Any]:
    """Extract the first balanced JSON object from a model reply (minimal)."""
    text = str(raw)
    start = text.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    obj = json.loads(text[start:i + 1])
                    if isinstance(obj, dict):
                        return obj
                    break
        start = text.find("{", start + 1)
    raise LLMTransportError("no JSON object found in model reply")


def model_slug(model: str) -> str:
    """Model name -> identifier slug (mirrors the real module's stamping)."""
    slug = "".join(c if c.isalnum() else "-" for c in str(model).lower())
    return "-".join(p for p in slug.split("-") if p) or "unknown"
