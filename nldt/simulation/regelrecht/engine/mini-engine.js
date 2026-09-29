// nldt/simulation/regelrecht/engine/mini-engine.js
// Deterministische mini-engine voor de regelrecht-subset (AND, EQUALS,
// LESS_THAN_OR_EQUAL, IF) — spiegel van reference_engine.py. Dual-mode:
// Node (CommonJS) voor de selftest, window.RegelRechtEngine in de browser.
"use strict";

class EngineError extends Error {}

function evaluate(execution, inputs) {
  const scope = Object.assign({}, inputs);
  const trace = [];
  // Zoals de ge-fixte reference_engine: ELKE top-level actie-waarde
  // (letterlijk, $-referentie of operatie) wordt in scope opgeslagen;
  // niet-operatie waarden geven geen trace-regels.
  for (const action of execution.actions || []) {
    scope[action.output] = resolve(action.value, scope, trace, action.output);
  }
  const outputs = {};
  for (const o of execution.output || []) outputs[o.name] = scope[o.name];
  return { outputs, trace };
}

function resolve(node, scope, trace, label) {
  if (typeof node === "string" && node.startsWith("$")) {
    if (!(node.slice(1) in scope)) throw new EngineError("onbekende referentie: " + node);
    return scope[node.slice(1)];
  }
  if (typeof node !== "object" || node === null || !("operation" in node)) return node;
  return apply(node, scope, trace, label);
}

function apply(op, scope, trace, label) {
  const name = op.operation;
  if (name === "AND") {
    const results = op.conditions.map((c) => Boolean(apply(c, scope, trace, label)));
    const result = results.every(Boolean);
    trace.push({ action: label, operation: "AND", operands: { conditions: op.conditions }, result });
    return result;
  }
  if (name === "EQUALS" || name === "LESS_THAN_OR_EQUAL") {
    const subject = operand(op.subject, scope);
    const value = operand(op.value, scope);
    const result = name === "EQUALS" ? subject === value : subject <= value;
    trace.push({ action: label, operation: name, operands: { subject: op.subject, value: op.value }, result });
    return result;
  }
  if (name === "IF") {
    let i = 0;
    for (const c of op.cases || []) {
      if (Boolean(apply(c.when, scope, trace, label))) {
        const result = operand(c.then, scope);
        trace.push({ action: label, operation: "IF", operands: { cases: (op.cases || []).length, default: op.default, firedCase: i + 1 }, result });
        return result;
      }
      i += 1;
    }
    if (!("default" in op)) throw new EngineError("IF zonder passerende case en zonder default");
    const result = operand(op.default, scope);
    trace.push({ action: label, operation: "IF", operands: { cases: (op.cases || []).length, default: op.default, firedCase: 0 }, result });
    return result;
  }
  throw new EngineError("niet-ondersteunde operatie: " + name);
}

function operand(node, scope) {
  if (typeof node === "string" && node.startsWith("$")) {
    if (!(node.slice(1) in scope)) throw new EngineError("onbekende referentie: " + node);
    return scope[node.slice(1)];
  }
  return node;
}

const Engine = { evaluate, EngineError };
if (typeof module !== "undefined" && module.exports) module.exports = Engine;
if (typeof window !== "undefined") window.RegelRechtEngine = Engine;
