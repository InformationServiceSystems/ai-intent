# Final campaign: three domains, three models, current code (10 October 2026)

Nine campaigns, prefix `fin_`, each ten independent runs of a domain's full suite with deterministic routing: finance (21 cases), procurement (12 cases) and medication review (12 cases, illustrative) with `llama3.1:8b`, `llama3.3:70b` and `qwen2.5:72b`. One GPU node per job (RTX PRO 6000 Blackwell for the first eight campaigns, A100 40 GB for the re-run of the 8B procurement campaign), Ollama 0.40.2, context capped at 8192 tokens, ten runner processes through an SSH tunnel (`scripts/hpc/run_on_gpu.sh`, `scripts/hpc/campaign.sh`). The code state is commit `73229ab` plus the scorer and gate corrections listed below, which were applied to the persisted sessions by `evaluation/rescore.py` or, for the gate, verified by re-evaluation. 1350 sessions in total. `python evaluation/campaign_summary.py fin_m8_finance ... --markdown evaluation/fin_summary.md`.

| Campaign | Model | Domain | Runs | ME | CDA | ATC | BVC | CGP | DC | SP | EX | AM | CDA given exposure |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fin_m8_finance | llama3.1:8b | finance | 10 | 84.3 ± 8.9 | 62.9 ± 10.6 | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 | 63.8 ± 4.0 | 97.5 ± 7.9 | — | — | 84.5 ± 9.7 |
| fin_m70_finance | llama3.3:70b | finance | 10 | 100.0 ± 0.0 | 57.5 ± 6.8 | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 | 61.2 ± 7.1 | 85.7 ± 24.4 | — | — | 73.3 ± 7.9 |
| fin_q72_finance | qwen2.5:72b | finance | 10 | 100.0 ± 0.0 | 48.6 ± 4.9 | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 | 72.5 ± 5.3 | 96.9 ± 8.8 | — | — | 73.3 ± 3.5 |
| fin_m8_procurement | llama3.1:8b | procurement | 10 | 100.0 ± 0.0 | 65.1 ± 19.4 | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 | 50.0 ± 0.0 | 100.0 ± 0.0 | — | — | 90.3 ± 12.8 |
| fin_m70_procurement | llama3.3:70b | procurement | 10 | 100.0 ± 0.0 | 77.5 ± 5.2 | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 | 50.0 ± 0.0 | 80.0 ± 25.8 | — | — | 88.0 ± 8.1 |
| fin_q72_procurement | qwen2.5:72b | procurement | 10 | 100.0 ± 0.0 | 67.8 ± 11.9 | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 | 50.0 ± 0.0 | 88.9 ± 22.0 | — | — | 79.3 ± 8.8 |
| fin_m8_clinical | llama3.1:8b | clinical | 10 | 96.7 ± 10.5 | 66.3 ± 20.8 | 98.3 ± 2.2 | 100.0 ± 0.0 | 100.0 ± 0.0 | — | 60.0 ± 21.1 | 82.5 ± 12.1 | 100.0 ± 0.0 | 100.0 ± 0.0 |
| fin_m70_clinical | llama3.3:70b | clinical | 10 | 100.0 ± 0.0 | 43.3 ± 8.6 | 99.6 ± 1.3 | 100.0 ± 0.0 | 100.0 ± 0.0 | — | 50.0 ± 0.0 | 95.0 ± 10.5 | 100.0 ± 0.0 | 100.0 ± 0.0 |
| fin_q72_clinical | qwen2.5:72b | clinical | 10 | 100.0 ± 0.0 | 35.0 ± 20.4 | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 | — | 55.0 ± 15.8 | 91.2 ± 11.9 | 100.0 ± 0.0 | 100.0 ± 0.0 |

| Campaign | Sessions | Infrastructure errors | Cases passed | Integrity ok | Forced blocks | Exceptions | CDA exposure | Mean s/case |
|---|---|---|---|---|---|---|---|---|
| fin_m8_finance | 210 | 0 | 183 | 210 | 25 | 0 | 52 of 124 (41.9 %), 50 on attempt 1 | 23.2 |
| fin_m70_finance | 210 | 0 | 192 | 210 | 8 | 0 | 35 of 87 (40.2 %), 34 on attempt 1 | 45.1 |
| fin_q72_finance | 210 | 0 | 188 | 210 | 5 | 0 | 22 of 84 (26.2 %), 20 on attempt 1 | 43.8 |
| fin_m8_procurement | 120 | 0 | 115 | 120 | 3 | 0 | 22 of 39 (56.4 %), 20 on attempt 1 | 23.3 |
| fin_m70_procurement | 120 | 0 | 118 | 120 | 15 | 0 | 50 of 72 (69.4 %), 48 on attempt 1 | 45.9 |
| fin_q72_procurement | 120 | 0 | 117 | 120 | 9 | 0 | 34 of 58 (58.6 %), 30 on attempt 1 | 56.8 |
| fin_m8_clinical | 120 | 0 | 103 | 120 | 9 | 0 | 18 of 29 (62.1 %), 18 on attempt 1 | 6.9 |
| fin_m70_clinical | 120 | 0 | 105 | 120 | 8 | 0 | 9 of 30 (30.0 %), 9 on attempt 1 | 25.3 |
| fin_q72_clinical | 120 | 0 | 100 | 120 | 6 | 0 | 7 of 32 (21.9 %), 7 on attempt 1 | 27.9 |

## What holds across every campaign

BVC and CGP are 100 % in all 90 runs, every one of the 1350 sessions satisfies the trace invariants, no forced pass occurred, and the gUFO export and the integrity queries ran on every session. Where the Mandate carries an amendment (CL-11), the committee's amendment was admitted before the delegation in every run (AM 100 %). Where the Mandate carries exceptions, the exceptions applied (EX 82 % to 95 %; the residual is the warfarin case, where the agent declines what the exception permits, see `clinical-notes.md`). ME is 100 % for both large models in every domain; for the 8B model it is 84.3 % in finance and 96.7 % in the clinical domain, where an out-of-scope request is sometimes answered in scope. CDA under the ER 2026 rubric is between 35 % and 78 % and falls with model capability, because a more capable model proposes fewer of the violations a case expects; conditional on exposure it is between 73 % and 100 %, and of the expected violations actually proposed, between 88 % and 100 % were rejected on the first attempt.

## What this campaign added

1. **Serving-layer errors must be excluded before scoring.** The first 8B procurement campaign had 22 of 120 sessions with connection errors from the Ollama server. An error result is a rejected message, so the forced-block path turned these into plausible scores: BVC and CGP stayed at 100 %, and only SP (0 % instead of 100 %) and the forced-block count (28 instead of 3) hinted at it. `evaluation/session_health.py` reads the log of every session for model or connection errors; the campaign summary reports the count per campaign, and a campaign with any such session is re-run (as this one was, on a second GPU job) rather than scored. The eight other campaigns have no such session.
2. **Scorers are a projection of the session, like the accountability note.** Two scorer defects were found in the clinical ATC figures (93 % to 94 % for all three models): the quantified-guidance pattern for morphine milligram equivalents was case-sensitive and never matched "MME", and the scorer counted a delivered "hold" without orders as something the synthesis must quantify, which the gate (since CL-08) does not. The gate's verdicts were not affected (no synthesis was rejected on the actionable-output rule in any clinical session). Both fixed; the gate and the scorer now share one reading (`quantifiable_contributors`). `evaluation/rescore.py` recomputed every score from the persisted sessions (changed cells: 3 in 8B finance, 41 in the three clinical campaigns, none elsewhere), which is possible because the scorers read the session and the log only.
3. **The oracle found two more gate defects and one of its own.** On the logged verdicts of the nine campaigns (8217 response-rule pairs from 1347 sessions) the oracle disagreed in 12 pairs: two 8B responses proposed positions with a market capitalisation of exactly $10 billion, which the gate admitted although the Mandate says "must exceed"; the same inclusive reading applied to "remain below 10 years". Thresholds now carry a `strict` flag, and consistency check C5 reads the wording of every threshold text (`spec-consistency.md`). The oracle's own leverage shape did not match the bare word "leverage" and so passed "unleveraged ETF, potentially with leverage", which the gate had rightly rejected (one pair, a reckless-preset session). The remaining ten pairs are the committee-amendment case: the logged gate evaluated the 21-day course against the cap the committee had raised to 21 days, the oracle against the registered 14-day cap; the oracle does not read session-scoped amendments, a limitation to state. After the fixes the current gate agrees with the oracle on all 8217 pairs of this campaign and on all 17 113 pairs of every archived campaign with typed outputs (2875 sessions).

## Reading the dimensions, as before

DC is 50.0 ± 0.0 in procurement for every model: the single preset case (PC-11) was contained after at least one revision in every run, which the rubric scores 1; it never scored 0. SP has one or two applicable cases per run, so a run in which the agent proposed no allocation moves the percentage by 25 to 50 points; the state predicates never failed to fire when an allocation was proposed. CDA should be reported conditional on exposure, with the exposure rate, next to the ER 2026 figure.
