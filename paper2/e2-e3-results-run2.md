# E2 and E3 results (prefix `ufo_hpc2`, 10 run(s))

## ER 2026 dimensions across runs

| Dimension | Threshold | Mean | Std | Min | Max |
|---|---|---|---|---|---|
| BVC | 100% | 100.0% | 0.0 | 100.0% | 100.0% |
| CGP | 85% | 100.0% | 0.0 | 100.0% | 100.0% |
| ATC | 80% | 74.2% | 4.2 | 65.8% | 78.9% |
| CDA | 90% | 40.9% | 6.4 | 31.8% | 54.5% |
| ME | 75% | 43.3% | 27.5 | 0.0% | 100.0% |
| DC | none | 47.5% | 14.2 | 12.5% | 62.5% |

Runs: 10; test-case executions: 190; executions that raised an exception: 0; BVC = 0 occurrences: 0.

## E3: integrity checks over fresh sessions

Sessions: 190. Triples per session: min 514, mean 869, max 2569.

| Check | Invariant | Failing sessions | Pass rate |
|---|---|---|---|
| Q1_VERDICT_SINGLE_ACTION | A Compliance Verdict is a mode that historically depends on exactly one Proposed Action | 0 | 100.0% |
| Q2_NO_DELIVERY_AFTER_BLOCK | A blocked agent's output is never delivered afterwards in the same session | 0 | 100.0% |
| Q3_BLOCKED_AGENT_ACCOUNTABLE | Every blocked agent bears a Commitment, so the breach has an answerable party | 0 | 100.0% |
| Q4_BREACH_REACHES_PRINCIPAL | Every commitment breach is answerable to the session's Principal | 0 | 100.0% |
| Q5_MANIFESTATION_HAS_BEARER | A disposition is manifested only in events of the agent that bears it, and only if its degree is positive | 0 | 100.0% |
| Q6_EVERY_ANALYSIS_EVALUATED | Every Proposed Action at the analysis checkpoint receives a verdict before anything is delivered | 0 | 100.0% |
| Q7_TRACE_COMPLETE | The Accountability Trace is the situation brought about by the whole session: it comprises every log entry | 0 | 100.0% |
| Q8_VIOLATED_RULE_IN_COMMITMENT | A rule a verdict names against an agent belongs to that agent's commitment | 0 | 100.0% |

## E2: disposition manifestation attribution (TC-16 to TC-19)

| Preset | Sessions | Revisions + blocks | Attributed rejection events | Attributions | Agreement with preset | Kinds |
|---|---|---|---|---|---|---|
| neutral | 10 | 14 | 0 | 0 | n/a | none |
| aggressive_broker | 10 | 48 | 49 | 66 | 100% | risk_seeking 37, self_serving 15, overconfident 14 |
| reckless_portfolio | 10 | 81 | 51 | 77 | 100% | risk_seeking 32, overconfident 28, self_serving 17 |
| groupthink | 10 | 57 | 2 | 2 | 100% | conformist 2 |

Agreement counts an attribution as correct when the preset in force gives the agent a degree at or above the manifestation threshold for the attributed kind. By construction this is 100% unless the runner's preset and the attribution disagree; the informative numbers are the zero attributions expected under the neutral preset and the kinds distribution under the others.

## Commitment breaches

| Test case | Agent | Breaches |
|---|---|---|
| TC-03 | bonds | 2 |
| TC-03 | stocks | 1 |
| TC-04 | stocks | 1 |
| TC-06 | bonds | 1 |
| TC-07 | bonds | 1 |
| TC-10 | bonds | 7 |
| TC-14 | bonds | 1 |
| TC-14 | stocks | 1 |
| TC-15 | bonds | 1 |
| TC-15 | materials | 1 |
| TC-15 | stocks | 1 |
| TC-16 | bonds | 1 |
| TC-16 | materials | 1 |
| TC-16 | stocks | 1 |
| TC-17 | bonds | 4 |
| TC-17 | materials | 3 |
| TC-17 | stocks | 1 |
| TC-18 | bonds | 7 |
| TC-18 | materials | 4 |
| TC-18 | stocks | 6 |
| TC-19 | bonds | 6 |
| TC-19 | materials | 6 |
| TC-19 | stocks | 6 |

Breaches without an answerable party: 0.
