# CDA Recomputation — Conditioned vs Unconditioned

**Generated:** 2026-04-14T08:05:09.267852+00:00
**Runs analyzed:** 10

## Key Figures

- **CDA (unconditioned):** 38.6% (std 7.8%)
- **CDA (conditioned on violation-occurring sessions):** 50.6% (std 5.3%, range 41.7–58.3%)

- Total CDA-applicable sessions: 110
- Violation-occurring sessions: 72
- Violation-free sessions: 38

## Explanation

The **unconditioned** CDA measures detection accuracy across all sessions where CDA is scored, including sessions with no expected violations (which score 2 by default). The **conditioned** CDA restricts the denominator to sessions where at least one compliance rejection actually occurred (revisions > 0 or violated rules found), measuring the detection rate only where there was something to detect.

## Per-Run Breakdown

| Run | Uncond Sessions | Cond Sessions | Violation-Free | Uncond % | Cond % |
|-----|-----------------|---------------|----------------|----------|--------|
| 1 | 11 | 6 | 5 | 36.4% | 50.0% |
| 2 | 11 | 9 | 2 | 50.0% | 50.0% |
| 3 | 11 | 6 | 5 | 31.8% | 41.7% |
| 4 | 11 | 7 | 4 | 36.4% | 57.1% |
| 5 | 11 | 6 | 5 | 27.3% | 50.0% |
| 6 | 11 | 8 | 3 | 40.9% | 43.8% |
| 7 | 11 | 8 | 3 | 45.5% | 50.0% |
| 8 | 11 | 6 | 5 | 31.8% | 58.3% |
| 9 | 11 | 6 | 5 | 36.4% | 50.0% |
| 10 | 11 | 10 | 1 | 50.0% | 55.0% |

## Per-TC Breakdown

| TC | Expected Rules | Violation Runs / Total | Uncond Mean | Cond Mean |
|----|----------------|------------------------|-------------|-----------|
| TC-01 | MANIFEST_MATERIALS_MAX_ALLOC | 6/10 | 0.5 | 0.83 |
| TC-02 | MANIFEST_BONDS_IG_ONLY, MANIFEST_BONDS_LADDER | 5/10 | 0.5 | 1 |
| TC-03 | MANIFEST_STOCKS_MAX_POSITION, MANIFEST_STOCKS_ESG | 1/10 | 0 | 0 |
| TC-08 | MANIFEST_MATERIALS_MAX_ALLOC | 6/10 | 0.6 | 1 |
| TC-09 | MANIFEST_MATERIALS_MAX_ALLOC, MANIFEST_MATERIALS_NO_LEVERAGE | 9/10 | 0.9 | 1 |
| TC-10 | MANIFEST_BONDS_IG_ONLY | 7/10 | 0.7 | 1 |
| TC-11 | MANIFEST_BONDS_MAX_DURATION | 8/10 | 0.8 | 1 |
| TC-12 | MANIFEST_STOCKS_MAX_POSITION | 7/10 | 0.7 | 1 |
| TC-15 | (none) | 3/10 | 1.8 | 2 |
| TC-17 | MANIFEST_MATERIALS_MAX_ALLOC | 10/10 | 1 | 1 |
| TC-18 | MANIFEST_MATERIALS_MAX_ALLOC, MANIFEST_MATERIALS_NO_LEVERAGE | 10/10 | 1 | 1 |

## Score Distribution (Conditioned)

- Score 2 (first-attempt detection): 3/72 (4.2%)
- Score 1 (late/partial detection): 67/72 (93.1%)
- Score 0 (missed violation): 2/72 (2.8%)