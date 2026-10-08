# Q9: consistency of the session graphs with the gUFO axioms

Date: 7 to 8 October 2026. Check: `python evaluation/gufo_consistency.py --prefix <campaign>`; each persisted session graph is merged with `evaluation/ontology/gufo.ttl`, closed under OWL RL with `owlrl`, and scanned for individuals that the closure places in two disjoint gUFO classes (35 disjoint pairs from `owl:disjointWith` and two `owl:AllDisjointClasses` axioms, among them Endurant, Event and Situation) or in `owl:Nothing`.

| Campaign | Graphs | Inconsistent | Inferred triples per graph (mean) | Seconds per graph (mean / max) |
|---|---|---|---|---|
| 1, model routing (`ufo_hpc`) | 189 | 0 | 4192 | 3.3 / 38 |
| 2, model routing, fixes (`ufo_hpc2`) | 190 | 0 | 6096 | 9.8 / 175 |
| 3, deterministic routing (`ufo_hpc3`) | pending | | | |

## What the check establishes

The export of Section 5 of the paper uses gUFO names; Q9 establishes that it also respects gUFO's axioms. Domain and range axioms let the reasoner infer the UFO category of every individual from the properties it participates in (an `inheresIn` subject must be an Aspect, a `participatedIn` subject an Object, a `broughtAbout` object a Situation), and the disjointness axioms then expose any individual that the export has placed in two incompatible categories. The tests in `tests/test_gufo_consistency.py` show that the check is not vacuous: a verdict additionally typed as an event, and an event used as the subject of `inheresIn`, are both reported.

The result also bears on the first correction in Section 8 of the paper. The ER 2026 grounding typed the Compliance Verdict as a mode dependent on the Proposed Action. Rendered literally, with the verdict inhering in the action event, that reading is exactly the error the second test injects, and Q9 rejects it. The corrected reading, the verdict as a mode of the agent that historically depends on the action, passes on all 379 graphs checked so far.

## Cost

Reasoning is two orders of magnitude more expensive than the eight queries (seconds rather than tens of milliseconds) and grows with session size; the longest sessions of campaign two took up to 175 s. This is acceptable for a per-session or nightly audit and is now part of the runner's per-session persistence step, which lengthens a test case by a few seconds.
