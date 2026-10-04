"""Laya (MLX) decision head for the nLDT deep-agent orchestrator.

Laya is non-autoregressive: one forward pass yields typed choices/scores/noul
answers — useful for fast routing hints before the Ollama orchestrator runs.
See https://www.orcarouter.ai/blog/laya-on-apple-silicon-mlx

Enable with DEEP_AGENT_LAYA=1 (default on Apple Silicon when laya-mlx imports).
Requires macOS + Metal; fails soft (no hint) when unavailable.
"""

from __future__ import annotations

import os
import platform
import sys
import threading
from typing import Any

import journal

_router_lock = threading.Lock()
_router: Any | None = None
_router_failed = False


def laya_enabled() -> bool:
    raw = os.environ.get("DEEP_AGENT_LAYA", "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if raw in ("1", "true", "yes", "on"):
        return True
    # Default: try on Apple Silicon macOS when not explicitly disabled
    return platform.system() == "Darwin" and platform.machine() in ("arm64", "aarch64")


def confidence_threshold() -> float:
    """Minimum confidence on routing choices (primary_poc + workflow) to inject a hint."""
    raw = os.environ.get("LAYA_MIN_CONFIDENCE", "0.55").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 0.55
    return max(0.0, min(1.0, value))


def routing_confidence(result: dict[str, Any]) -> tuple[float | None, dict[str, float]]:
    """Return (min conf among routing choices, per-question confidences)."""
    answers = result.get("answers")
    if not isinstance(answers, dict):
        return None, {}
    confs: dict[str, float] = {}
    for qid in ("primary_poc", "workflow"):
        c = _confidence(answers.get(qid))
        if c is not None:
            confs[qid] = c
    if not confs:
        return None, confs
    return min(confs.values()), confs


def passes_confidence_gate(result: dict[str, Any]) -> bool:
    """True when routing choice confidences meet LAYA_MIN_CONFIDENCE (or are unknown)."""
    min_conf, _ = routing_confidence(result)
    if min_conf is None:
        return True
    return min_conf >= confidence_threshold()


def laya_available() -> bool:
    if not laya_enabled():
        return False
    if platform.system() != "Darwin":
        return False
    try:
        import laya_mlx  # noqa: F401
    except ImportError:
        return False
    except Exception:
        return False
    return True


def nldt_orchestrator_questions() -> dict[str, Any]:
    """Question schema tailored to nLDT POC + role specialists."""
    return {
        "primary_poc": {
            "type": "choice",
            "instructions": "Which nLDT POC does `request` primarily concern?",
            "criteria": {
                "breda": "Breda five-value scan or grounded scan QA",
                "rijnland": "peil conflict, water levels, Rijnland what-if",
                "utrecht": "Utrecht opportunity map, world-scene, scenario authoring",
                "crosstrack": "Plane C wind × solar × forest overlay",
                "minigim": "MiniGIM gebiedscheck / Lijst-v0.91",
                "eindhoven": "bestemmingsplan → omgevingsplan bp2op",
                "cross_poc": "multiple POCs or recipe inventory",
                "unclear": "no specific POC yet",
            },
        },
        "workflow": {
            "type": "choice",
            "instructions": "Which workflow shape best matches `request`?",
            "criteria": {
                "plan_only": "run plan only, no execution",
                "execute_demo": "build world scene and show visual demo",
                "full_chain": "intake → norms → formal rule → build → geo/critic → explainer",
                "norm_chain_only": "intake, norm cards, formalizer only",
                "compare_layers": "control vs scenario spatial comparison",
                "geo_and_critic": "build then geospecialist + critic validation",
                "inventory": "list recipes or compare POC capabilities",
                "other": "none of the above",
            },
        },
        "needs_intake": {
            "type": "noul",
            "instructions": "Must `request` start with intake (vague brief → OpportunityMapRequest)?",
        },
        "needs_build": {
            "type": "noul",
            "instructions": "Does `request` require running world-scene-build or a visual demo?",
        },
        "needs_critic": {
            "type": "noul",
            "instructions": "Should the critic validate a built bundle after a build?",
        },
    }


def _answer_value(raw: Any) -> str:
    if raw is None:
        return "?"
    if isinstance(raw, dict):
        if raw.get("type") == "choice" and "choice" in raw:
            return str(raw["choice"])
        if raw.get("type") == "score" and "score" in raw:
            return str(raw["score"])
        if raw.get("type") == "noul" and "noul" in raw:
            return "true" if float(raw["noul"]) >= 0.5 else "false"
        for key in ("answer", "label", "value", "selected", "choice"):
            if key in raw and raw[key] is not None:
                return str(raw[key])
    return str(raw)


def _confidence(raw: Any) -> float | None:
    if isinstance(raw, dict):
        for key in ("confidence", "prob", "probability"):
            if key in raw and raw[key] is not None:
                try:
                    return float(raw[key])
                except (TypeError, ValueError):
                    pass
    return None


def format_routing_hint(result: dict[str, Any]) -> str:
    """Turn a Laya predict payload into orchestrator-facing Dutch/English hint text."""
    answers = result.get("answers") or result
    lines: list[str] = []
    routing = result.get("routing")
    if isinstance(routing, dict):
        lines.append(
            f"Checkpoint: {routing.get('model', '?')} ({routing.get('reason', '')})"
        )

    mapping = {
        "primary_poc": "POC-specialist",
        "workflow": "Workflow",
        "needs_intake": "Start met intake",
        "needs_build": "World-scene build/demo",
        "needs_critic": "Critic na build",
    }
    for qid, label in mapping.items():
        block = answers.get(qid) if isinstance(answers, dict) else None
        if block is None and qid in result:
            block = result[qid]
        if block is None:
            continue
        val = _answer_value(block)
        conf = _confidence(block)
        suffix = f" (conf {conf:.2f})" if conf is not None else ""
        if qid.startswith("needs_"):
            yn = val.lower() in ("true", "yes", "1")
            lines.append(f"- {label}: {'ja' if yn else 'nee'}{suffix}")
        else:
            lines.append(f"- {label}: {val}{suffix}")

    delegate = _suggest_delegate(answers if isinstance(answers, dict) else result)
    if delegate:
        lines.append(f"- Eerste delegatie (advies): `{delegate}`")
    return "\n".join(lines)


def _noul_yes(block: Any) -> bool:
    return _answer_value(block).lower() in ("true", "yes", "1")


def _suggest_delegate(answers: dict[str, Any]) -> str | None:
    poc = _answer_value(answers.get("primary_poc", {}))
    wf = _answer_value(answers.get("workflow", {}))
    if _noul_yes(answers.get("needs_intake")) or wf in ("full_chain", "norm_chain_only"):
        return "intake"
    if wf in ("execute_demo", "geo_and_critic", "full_chain", "compare_layers"):
        return "utrecht"
    if poc in ("breda", "rijnland", "utrecht", "crosstrack", "minigim", "eindhoven"):
        return poc
    if wf == "inventory":
        return "orchestrator (list_recipes/get_recipe)"
    return None


def _get_router() -> Any | None:
    global _router, _router_failed
    if _router_failed or not laya_available():
        return None
    with _router_lock:
        if _router is not None:
            return _router
        if _router_failed:
            return None
        try:
            from laya_mlx import Router

            max_loaded = int(os.environ.get("LAYA_MAX_LOADED", "1"))
            preload = os.environ.get("LAYA_PRELOAD", "").strip().lower() in ("1", "true", "yes")
            _router = Router(max_loaded=max_loaded, preload=preload, default="english")
            return _router
        except Exception as exc:
            _router_failed = True
            journal.append("laya", "router", f"Laya niet beschikbaar: {type(exc).__name__}: {exc}")
            return None


def predict_routing(request: str) -> dict[str, Any] | None:
    """Run Laya on the user request; return full payload or None if disabled/failed."""
    router = _get_router()
    if router is None:
        return None
    state = {"request": request}
    questions = nldt_orchestrator_questions()
    lang = "nl" if any(w in request.lower() for w in ("de ", "het ", "een ", "voor ", "gebied")) else None
    try:
        return router.predict(state, questions, lang=lang)
    except Exception as exc:
        journal.append("laya", "router", f"predict mislukt: {type(exc).__name__}: {exc}")
        return None


def advise_and_journal(request: str) -> str | None:
    """Run Laya, journal structured step, return hint text for the orchestrator."""
    if not laya_enabled():
        return None
    if not laya_available():
        journal.append(
            "laya",
            "router",
            "overgeslagen — installeer laya-mlx (pip) op Apple Silicon of zet DEEP_AGENT_LAYA=0",
        )
        return None
    result = predict_routing(request)
    if not result:
        return None
    hint = format_routing_hint(result)
    min_conf, per_q = routing_confidence(result)
    threshold = confidence_threshold()
    if not passes_confidence_gate(result):
        summary = (
            f"hint onderdrukt — min conf {min_conf:.2f} < drempel {threshold:.2f} "
            f"({', '.join(f'{k}={v:.2f}' for k, v in per_q.items())})"
        )
        journal.append(
            "laya",
            "router",
            summary,
            detail=hint,
            laya=result,
            laya_suppressed=True,
            laya_min_conf=min_conf,
            laya_threshold=threshold,
        )
        print(f"[laya] {summary}", file=sys.stderr)
        return None
    summary = hint.split("\n")[0][:200] if hint else "routing"
    journal.append(
        "laya",
        "router",
        summary,
        detail=hint,
        laya=result,
        laya_min_conf=min_conf,
        laya_threshold=threshold,
    )
    print(f"[laya] {summary}", file=sys.stderr)
    return hint


def augment_user_message(question: str) -> str:
    """Prepend Laya advisory block when a hint was produced."""
    hint = advise_and_journal(question)
    if not hint:
        return question
    return (
        f"{question.strip()}\n\n"
        "---\n"
        "[Laya routing hint — lokaal MLX, alleen advies; bevestig met recipes/tools/delegatie]\n"
        f"{hint}\n"
        "---"
    )
