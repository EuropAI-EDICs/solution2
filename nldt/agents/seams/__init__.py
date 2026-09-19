"""Governed GenAI seams that sit *beside* LangGraph nodes.

Each seam may call an LLM or Deep Agent harness, but only returns
schema-validated proposals. Deterministic engines dispose elsewhere.
"""

from agents.seams.deep_research import propose_research_brief

__all__ = ["propose_research_brief"]
