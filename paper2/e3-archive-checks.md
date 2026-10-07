# E3 preview: integrity checks over archived sessions

Date: 7 October 2026. Command: `python evaluation/sparql_checks.py --all`, aggregated over every session in `data/sessions.db` that contains a user query (21 sessions; the 190 sessions of the ER 2026 evaluation live in `evaluation/*.json`, not in the database, and will be imported for the full E3).

| Check | Invariant | Failing sessions | Pass rate |
|---|---|---|---|
| Q1 | A verdict depends on exactly one Proposed Action | 0 | 100% |
| Q2 | No delivery after a block | 0 | 100% |
| Q3 | A blocked agent bears a commitment | 10 | 52.4% |
| Q4 | A breach is answerable to the Principal | 0 | 100% |
| Q5 | A manifestation has a bearer with positive degree | 0 | 100% |
| Q6 | Every analysis-checkpoint action receives a verdict | 2 | 90.5% |
| Q7 | The trace comprises every log entry | 0 | 100% |
| Q8 | A violated rule belongs to the agent's commitment | 1 | 95.2% |

Graph size per session: 132 to 2312 triples, mean 1100. Export and all eight queries: 0.10 s per session on average.

## Reading

- **Q2 at 100% on every archived session** is the gUFO restatement of the ER 2026 result: no output of a blocked agent was ever delivered. The query reads only the log.
- **Q3 fails in exactly the ten sessions that contain a block.** Those sessions predate the delegation hooks, so no commitment was logged; the breach has no answerable party in the trace. This is a finding about trace completeness before this work, not a failure of the gate. Sessions run after the hooks pass Q3 (verified on one live session under the reckless preset).
- **Q6 fails in two sessions.** One is a test session; the other predates the Compliance Agent entirely and has no verdicts at all. Both are correctly reported as traces in which Proposed Actions were never evaluated.
- **Q8 exposed a real gap.** The gate applied five disposition-integrity rules (`DISPOSITION_*`) that were defined in `agents/compliance.py` but never registered in `agents/regulatory_rules.py`. A verdict could therefore name a rule that the agent's commitment did not cover. The five rules are now registered and apply to the three sub-agents, so new commitments cover them. The one failing session was run before the registration and keeps its original commitment in the log, as it should.

## Confirmation on a fresh session

After the registration, one further live session under the `reckless_portfolio` preset (session `55941fc8`, three sub-agents consulted, four revisions, no block) passed all eight checks, Q8 included. Eleven manifestations were attributed across the three agents; two of them name the newly registered rules `DISPOSITION_OVERCONFIDENT_FLAGS` and `DISPOSITION_RISK_BOUNDARY`, which the agents' commitments now cover.

## Two export corrections the checks forced

1. Verdicts at the routing and synthesis checkpoints are logged as `compliance.block.routing` and `compliance.block.synthesis`. The export now maps both to the central agent; before, they inhered in a non-existent agent and Q1 and Q3 reported them.
2. Order comparisons in SPARQL use a per-entry sequence number rather than `xsd:dateTimeStamp`, which the query engine does not order.
