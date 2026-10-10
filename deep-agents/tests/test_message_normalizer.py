"""Tests voor de bericht-normalizer (fase 3-nasleep): thinking-blokken uit de
gedeelde checkpoint-draad mogen de model-aanroepen niet meer breken.

Offline en LLM-vrij; zelfde run-conventie als de overige deep-agents-tests:
cd deep-agents && PYTHONPATH=$PWD/.venv/lib/python3.14/site-packages
../nldt/.venv/bin/python -m pytest tests/test_message_normalizer.py -q
"""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from message_normalizer import (
    MessageNormalizerMiddleware,
    flatten_content,
    normalize_message,
    normalize_messages,
)

THINKING_BLOCKS = [
    {"type": "thinking", "thinking": "The user wants a run plan."},
    {"type": "text", "text": "Hier is het plan."},
    {"type": "tool_use", "id": "tc-1", "name": "list_recipes", "input": {}},
]


def test_flatten_content_joins_text_and_drops_thinking():
    assert flatten_content(THINKING_BLOCKS) == "Hier is het plan."
    assert flatten_content("platte tekst") == "platte tekst"


def test_normalize_message_preserves_tool_calls_and_metadata():
    msg = AIMessage(content=THINKING_BLOCKS, id="aim-1")
    msg.tool_calls = [{"name": "list_recipes", "args": {}, "id": "tc-1"}]
    flat = normalize_message(msg)
    assert isinstance(flat.content, str)
    assert flat.content == "Hier is het plan."
    assert flat.id == "aim-1"
    assert flat.tool_calls == msg.tool_calls  # tool_use blijft via tool_calls


def test_normalize_messages_mixed_types():
    msgs = [
        HumanMessage(content="gewone vraag"),  # al plat — onaangetast
        AIMessage(content=THINKING_BLOCKS),
        ToolMessage(content=[{"type": "text", "text": "tool-resultaat"}], tool_call_id="tc-1"),
    ]
    flat = normalize_messages(msgs)
    assert flat[0].content == "gewone vraag"
    assert flat[1].content == "Hier is het plan."
    assert flat[2].content == "tool-resultaat"
    assert flat[2].tool_call_id == "tc-1"


def test_middleware_flattens_model_request():
    mw = MessageNormalizerMiddleware()
    captured = {}

    class Request:
        def __init__(self, messages):
            self.messages = messages

    def handler(request):
        captured["messages"] = request.messages
        return "doorgelaten"

    uit = mw.wrap_model_call(Request([AIMessage(content=THINKING_BLOCKS)]), handler)
    assert uit == "doorgelaten"
    assert captured["messages"][0].content == "Hier is het plan."
