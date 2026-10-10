"""Bericht-normalizer voor de live-runners (fase 3-nasleep).

Reasoning-modellen (gemma4-familie) antwoorden met inhoudsblokken —
``[thinking, tool_use, text]`` i.p.v. platte tekst. Die blokken belanden in
de gedeelde checkpoint-draad (``thread_id='nldt-live'``), en langchain-ollama
weigert bij het opnieuw afspelen van die geschiedenis elke inhoud die niet
``text`` of ``image_url`` is: ``ValueError: Unsupported message content
type`` — elke volgende run op de draard, met welk model dan ook.

``MessageNormalizerMiddleware`` plattert de berichtinhoud vóór élke
model-aanroep: ``text``-blokken samengevoegd, ``thinking``-blokken gestript
(de reasoning is interieur en wordt door het model opnieuw opgebouwd),
``tool_use`` blijft via ``AIMessage.tool_calls``. Zo blijft het draad-geheugen
bruikbaar mét thinking-modellen.
"""

from __future__ import annotations

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import BaseMessage


def flatten_content(content) -> str:
    """Blok-lijst → platte tekst: ``text``-blokken samengevoegd; ``thinking``-
    en ``tool_use``-blokken vervallen uit de tekst (tool_use leeft in
    ``AIMessage.tool_calls``)."""
    if not isinstance(content, list):
        return content
    parts = [b.get("text", "") for b in content
             if isinstance(b, dict) and b.get("type") == "text" and b.get("text")]
    return "\n".join(parts)


def normalize_message(message: BaseMessage) -> BaseMessage:
    """Zelfde boodschap met platte tekst-inhoud; alle overige velden
    (tool_calls, tool_call_id, naam, id) blijven staan."""
    if not isinstance(message.content, list):
        return message
    return message.model_copy(update={"content": flatten_content(message.content)})


def normalize_messages(messages) -> list:
    return [normalize_message(m) for m in messages]


class MessageNormalizerMiddleware(AgentMiddleware):
    """Plattert de berichten in het model-verzoek vóór uitvoering."""

    def wrap_model_call(self, request, handler):
        request.messages = normalize_messages(request.messages)
        return handler(request)
