# AI-Intent Variance Report

**Runs:** 3
**Model:** llama3.1
**Test cases per run:** 19

---

## 1. Per-Dimension Scores Across Runs

| Dimension | Run1 | Run2 | Run3 | Mean | Std | Min | Max |
|-----------|------|------|------|------|-----|-----|-----|
| ME | 0.0% | 33.3% | 66.7% | 33.3% | 33.4% | 0.0% | 66.7% |
| CDA | 36.4% | 36.4% | 40.9% | 37.9% | 2.6% | 36.4% | 40.9% |
| ATC | 60.5% | 73.7% | 71.1% | 68.4% | 7.0% | 60.5% | 73.7% |
| BVC | 94.7% | 100.0% | 100.0% | 98.2% | 3.1% | 94.7% | 100.0% |
| CGP | 94.7% | 100.0% | 100.0% | 98.2% | 3.1% | 94.7% | 100.0% |
| DC | 25.0% | 37.5% | 37.5% | 33.3% | 7.2% | 25.0% | 37.5% |

---

## 2. Per-Test-Case Stability

| TC | Category | Pass Rate | Stability | Mean Score | Scores |
|----|----------|-----------|-----------|------------|--------|
| TC-01 | A | 33.0% | Volatile-Fail | 6 | 6, 6, 6 |
| TC-02 | A | 67.0% | Volatile-Pass | 6 | 6, 6, 6 |
| TC-03 | A | 0.0% | Stable-Fail | 6 | 6, 6, 6 |
| TC-04 | A | 100.0% | Stable-Pass | 5.3 | 5, 6, 5 |
| TC-05 | B | 0.0% | Stable-Fail | 5.7 | 5, 6, 6 |
| TC-06 | B | 33.0% | Volatile-Fail | 6 | 6, 4, 8 |
| TC-07 | B | 67.0% | Volatile-Pass | 6.3 | 5, 7, 7 |
| TC-08 | C | 67.0% | Volatile-Pass | 6 | 6, 6, 6 |
| TC-09 | C | 67.0% | Volatile-Pass | 4 | 0, 6, 6 |
| TC-10 | C | 100.0% | Stable-Pass | 6.7 | 6, 7, 7 |
| TC-11 | C | 33.0% | Volatile-Fail | 5.7 | 5, 6, 6 |
| TC-12 | C | 67.0% | Volatile-Pass | 6 | 6, 6, 6 |
| TC-13 | D | 100.0% | Stable-Pass | 5.7 | 5, 6, 6 |
| TC-14 | D | 100.0% | Stable-Pass | 5.3 | 5, 6, 5 |
| TC-15 | E | 100.0% | Stable-Pass | 7.3 | 7, 7, 8 |
| TC-16 | F | 33.0% | Volatile-Fail | 5.7 | 5, 6, 6 |
| TC-17 | F | 100.0% | Stable-Pass | 7.3 | 8, 7, 7 |
| TC-18 | F | 67.0% | Volatile-Pass | 6.7 | 6, 7, 7 |
| TC-19 | F | 67.0% | Volatile-Pass | 6 | 7, 6, 5 |

---

## 3. Core Claims Confidence

| Claim | Metric | Mean | Min | Max | Std | Stable? |
|-------|--------|------|-----|-----|-----|---------|
| ME | 33.3% | 33.3% | 0.0% | 66.7% | 33.4% | No |
| CDA | 37.9% | 37.9% | 36.4% | 40.9% | 2.6% | Yes |
| ATC | 68.4% | 68.4% | 60.5% | 73.7% | 7.0% | Borderline |
| BVC | 98.2% | 98.2% | 94.7% | 100.0% | 3.1% | Yes |
| CGP | 98.2% | 98.2% | 94.7% | 100.0% | 3.1% | Yes |
| DC | 33.3% | 33.3% | 25.0% | 37.5% | 7.2% | Borderline |

---

## 4. Findings

**Stable dimensions (std < 5%):** CDA, BVC, CGP. These results are consistent across runs and can be reported with high confidence.

**Volatile dimensions (std >= 10%):** ME. These results vary significantly between runs. Report the mean and range rather than a point estimate.

**Borderline dimensions (5% <= std < 10%):** ATC, DC. Moderate variance — results are directionally reliable but exact percentages may shift.

**BVC DROPPED BELOW 100% in run(s): [1].** This is a critical finding that must be investigated.

**CGP dropped below 100% in run(s): [1].** False positives detected — investigate the affected sessions.
