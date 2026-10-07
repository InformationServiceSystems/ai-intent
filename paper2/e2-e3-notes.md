# Notes on the first full E2/E3 run (7 October 2026)

Setup: 19 test cases, 10 independent runs, 190 test-case executions, llama3.1:8b served by Ollama on one A100 40 GB node of the UdS HPC cluster (HTCondor job 65792), ten runner processes in parallel through an SSH tunnel. Wall-clock time for all ten runs: about 50 minutes (the same workload took about seven hours sequentially on the workstation). Numbers are in `e2-e3-results.md`, produced by `python evaluation/paper2_analysis.py --prefix ufo_hpc`.

## Headline results

- **Zero forced pass.** None of the 189 persisted sessions contains a `forced_pass` message. The single BVC score of 0 is the crashed execution (below), which the runner scores 0 on every dimension; it is not a delivery after rejection.
- **Q2 holds in 189 of 189 sessions.** No output of a blocked agent was delivered afterwards. This is the ER 2026 containment claim restated as a SPARQL invariant over the trace and confirmed without reference to the scorer.
- **Q3 and Q4 hold in 189 of 189 sessions.** Every one of the 48 commitment breaches (forced blocks) resolves to a chain of answerable parties that ends at the Principal. Before this work, a forced block was a verdict and a sentence in the accountability note.
- **Q8 found a second registry gap.** One routing block named `MIFID2_ART24_SCOPE` against the orchestrator although the registry listed the rule for the three specialists only, so no commitment covered it. The rule now applies to the orchestrator as well (commit 46d9d68). Together with the five unregistered disposition-integrity rules found before the run, Q8 has now twice exposed a rule the gate enforced without anyone having committed to it.
- **Attribution behaves as designed under pressure.** Under the aggressive and reckless presets, 95 and 130 attributions were made, dominated by risk-seeking and overconfident kinds; under groupthink, only conformist attributions appear. Under the neutral preset, four conformist attributions occurred because the neutral preset sets conformist to 0.5, exactly the manifestation threshold. Whether the threshold should be strict, or the neutral preset's conformist degree lower, is a modelling decision to settle before the final run.

## Comparison with the ER 2026 numbers

| Dimension | ER 2026 mean | This run mean | Note |
|---|---|---|---|
| BVC | 97.9% | 99.5% | one crash counted as 0 |
| CGP | 97.9% | 99.5% | same event as BVC |
| ATC | 71.3% | 73.7% | unchanged in kind |
| CDA | 38.6% / 50.6% | 42.3% | detection latency, model-bound |
| ME | 35.0% | 40.0% | routing-dependent, high variance |
| DC | 57.5% | 53.8% | strict rubric |

The framework-level dimensions are stable across the two campaigns; the model-bound dimensions remain where they were. This is the expected picture: the new constructs add provenance and accountability to the trace, they do not change the model's instruction following.

## Incidents

- **One crash (worker 1, TC-06).** The model returned a JSON-encoded string for the routing decision; the parser returned a string and the log entry failed validation. Fixed in commit 46d9d68 (parser unwraps one level and rejects non-objects; routing falls back to all agents). The execution stays in the data as an exception with zero scores.
- **Archived ER 2026 sessions were not available.** The runner now persists every session as JSON and Turtle under `evaluation/sessions/`, so this campaign is reproducible from files alone.

## Recommended before the final campaign

1. Decide the manifestation threshold rule (strict versus inclusive) and re-run.
2. Re-run with the two fixes in place so that Q8 passes on 100% and no execution crashes.
3. Consider the deterministic routing override from ROADMAP item 4, so that ME is measured on every out-of-scope case.
