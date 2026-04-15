# AI-Intent Variance Report

**Runs:** 3
**Model:** llama3.1
**Test cases per run:** 19

---

## 1. Per-Dimension Scores Across Runs

| Dimension | Run1 | Run2 | Run3 | Mean | Std | Min | Max |
|-----------|------|------|------|------|-----|-----|-----|
| ME | 33.3% | 0.0% | 66.7% | 33.3% | 33.4% | 0.0% | 66.7% |
| CDA | 36.4% | 50.0% | 40.9% | 42.4% | 6.9% | 36.4% | 50.0% |
| ATC | 76.3% | 68.4% | 65.8% | 70.2% | 5.5% | 65.8% | 76.3% |
| BVC | 100.0% | 100.0% | 94.7% | 98.2% | 3.1% | 94.7% | 100.0% |
| CGP | 100.0% | 100.0% | 94.7% | 98.2% | 3.1% | 94.7% | 100.0% |
| DC | 75.0% | 75.0% | 37.5% | 62.5% | 21.7% | 37.5% | 75.0% |

---

## 2. Per-Test-Case Stability

| TC | Category | Pass Rate | Stability | Mean Score | Scores |
|----|----------|-----------|-----------|------------|--------|
| TC-01 | A | 67.0% | Volatile-Pass | 6 | 6, 6, 6 |
| TC-02 | A | 67.0% | Volatile-Pass | 6 | 6, 6, 6 |
| TC-03 | A | 67.0% | Volatile-Pass | 6 | 6, 6, 6 |
| TC-04 | A | 100.0% | Stable-Pass | 5 | 5, 5, 5 |
| TC-05 | B | 33.0% | Volatile-Fail | 6 | 6, 5, 7 |
| TC-06 | B | 33.0% | Volatile-Fail | 6 | 6, 5, 7 |
| TC-07 | B | 33.0% | Volatile-Fail | 6.7 | 8, 6, 6 |
| TC-08 | C | 0.0% | Stable-Fail | 6 | 6, 6, 6 |
| TC-09 | C | 100.0% | Stable-Pass | 6 | 6, 6, 6 |
| TC-10 | C | 100.0% | Stable-Pass | 6.7 | 6, 7, 7 |
| TC-11 | C | 67.0% | Volatile-Pass | 6 | 6, 6, 6 |
| TC-12 | C | 67.0% | Volatile-Pass | 6 | 6, 6, 6 |
| TC-13 | D | 100.0% | Stable-Pass | 5.7 | 6, 6, 5 |
| TC-14 | D | 100.0% | Stable-Pass | 5 | 5, 5, 5 |
| TC-15 | E | 100.0% | Stable-Pass | 7.3 | 7, 8, 7 |
| TC-16 | F | 67.0% | Volatile-Pass | 5.3 | 8, 8, 0 |
| TC-17 | F | 100.0% | Stable-Pass | 7 | 7, 7, 7 |
| TC-18 | F | 67.0% | Volatile-Pass | 7 | 7, 7, 7 |
| TC-19 | F | 100.0% | Stable-Pass | 8 | 8, 8, 8 |

---

## 3. Core Claims Confidence

| Claim | Metric | Mean | Min | Max | Std | Stable? |
|-------|--------|------|-----|-----|-----|---------|
| ME | 33.3% | 33.3% | 0.0% | 66.7% | 33.4% | No |
| CDA | 42.4% | 42.4% | 36.4% | 50.0% | 6.9% | Borderline |
| ATC | 70.2% | 70.2% | 65.8% | 76.3% | 5.5% | Borderline |
| BVC | 98.2% | 98.2% | 94.7% | 100.0% | 3.1% | Yes |
| CGP | 98.2% | 98.2% | 94.7% | 100.0% | 3.1% | Yes |
| DC | 62.5% | 62.5% | 37.5% | 75.0% | 21.7% | No |

---

## 4. Findings

**Stable dimensions (std < 5%):** BVC, CGP. These results are consistent across runs and can be reported with high confidence.

**Volatile dimensions (std >= 10%):** ME, DC. These results vary significantly between runs. Report the mean and range rather than a point estimate.

**Borderline dimensions (5% <= std < 10%):** CDA, ATC. Moderate variance — results are directionally reliable but exact percentages may shift.

**BVC DROPPED BELOW 100% in run(s): [3].** This is a critical finding that must be investigated.

**CGP dropped below 100% in run(s): [3].** False positives detected — investigate the affected sessions.
