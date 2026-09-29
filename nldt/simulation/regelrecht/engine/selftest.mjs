// nldt/simulation/regelrecht/engine/selftest.mjs
// Draait de golden set (gegenereerd door build_runs.py via reference_engine)
// door de JS-mini-engine. Exit 0 alleen bij 16/16 exacte overeenkomst
// (outputs én volledige trace).
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";

const require = createRequire(import.meta.url);
const { evaluate } = require("./mini-engine.js");
const cases = JSON.parse(readFileSync(new URL("./engine-cases.json", import.meta.url), "utf8"));

let failed = 0;
for (const c of cases) {
  const got = evaluate(c.execution, c.inputs);
  const ok =
    JSON.stringify(got.outputs) === JSON.stringify(c.expectedOutputs) &&
    JSON.stringify(got.trace) === JSON.stringify(c.trace);
  if (!ok) {
    failed += 1;
    console.error(`FAIL ${c.id}\n  verwacht: ${JSON.stringify(c.expectedOutputs)}\n  gekregen: ${JSON.stringify(got.outputs)}`);
  }
}
console.log(`${cases.length - failed}/${cases.length}`);
process.exit(failed ? 1 : 0);
