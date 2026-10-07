# Second full campaign (7 October 2026, prefix `ufo_hpc2`)

Same setup as the first campaign (`e2-e3-notes.md`): 19 test cases, 10 runs, 190 executions, llama3.1:8b on one A100 40 GB node (HTCondor job 65792), ten parallel workers through an SSH tunnel. Differences from the first campaign: the two registry and parser fixes of commit 46d9d68 and the strict manifestation threshold of commit cf56e91 were in place. Full numbers in `e2-e3-results-run2.md`.

## Outcome

| Measure | Campaign 1 | Campaign 2 |
|---|---|---|
| Executions | 190 | 190 |
| Executions that crashed | 1 | 0 |
| Forced pass messages | 0 | 0 |
| BVC mean (std) | 99.5% (1.7) | 100.0% (0.0) |
| CGP mean (std) | 99.5% (1.7) | 100.0% (0.0) |
| Q1 to Q7 | 100% | 100% |
| Q8 | 99.5% (one routing block) | 100% |
| Attributions under neutral preset | 4 (conformist at 0.5) | 0 |
| Attributions, aggressive broker | 95 | 66 |
| Attributions, reckless portfolio | 130 | 77 |
| Attributions, groupthink | 5 | 2 |
| ATC / CDA / ME / DC mean | 73.7 / 42.3 / 40.0 / 53.8 | 74.2 / 40.9 / 43.3 / 47.5 |

All eight invariants hold on all 190 sessions. The second campaign is the data basis of the paper; the first is kept as the record of the two Q8 findings.

## Reading

- The two framework-level dimensions and all eight invariants are at 100 percent with zero variance across ten runs. Nothing a blocked agent produced was delivered, every breach has an answerable chain to the Principal, and every rule the gate named is a rule the agent had committed to.
- Under the neutral preset there is now no attribution at all, as the strict threshold intends. Under the two adversarial presets, attributions remain dominated by risk-seeking and overconfident kinds; the lower counts than in campaign 1 reflect run-to-run variation in how many rejections the model provoked, not a change in attribution logic.
- ME has a standard deviation of 27.5 points with a range from 0 to 100 percent. This is the known routing effect: whether an out-of-scope request ever reaches the agent that should decline it depends on the orchestrator's routing decision, which the model makes non-deterministically. The third campaign with deterministic routing for the evaluation (ROADMAP item 4) addresses this after the paper draft.
- DC fell from 53.8 to 47.5 percent. The rubric scores 1 whenever a revision occurred, and the reckless preset provoked more revisions in this campaign (81 against 59). Under the restated definition of Section 4 the relevant fact is unchanged: no manifestation reached delivery.
