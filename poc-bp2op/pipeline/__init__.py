"""poc-bp2op pipeline package — bestemmingsplan/tijdelijk-deel -> omgevingsplan conversion PoC.

Agents (one process, deterministic, no LLM at runtime):
  parsers        MC-4  automatisch inlezen + opknippen (official publications -> rule records)
  knowledgebank  MC-5  kennisbank seeds + scored match suggestions
  analyser       MC-8  bulk coverage / conversie-gereedheid
  critic         MC-6  V0 syntactic, V1 completeness, V2 grounding, V3 semantic re-execution,
                 V4 human checkpoint (always pending)
  explainer      MC-3  omzettabel exports + PROV
  report         MC-7  single-file HTML report with both sides in context
"""

__version__ = "poc-bp2op.1.0"
