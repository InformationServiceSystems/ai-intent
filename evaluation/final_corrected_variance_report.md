# AI-Intent Variance Report

**Runs:** 3
**Model:** llama3.1
**Test cases per run:** 19

---

## 1. Per-Dimension Scores Across Runs

| Dimension | Run1 | Run2 | Run3 | Mean | Std | Min | Max |
|-----------|------|------|------|------|-----|-----|-----|
| ME | 0.0% | 33.3% | 33.3% | 22.2% | 19.2% | 0.0% | 33.3% |
| CDA | 45.5% | 40.9% | 45.5% | 44.0% | 2.7% | 40.9% | 45.5% |
| ATC | 81.6% | 73.7% | 76.3% | 77.2% | 4.0% | 73.7% | 81.6% |
| BVC | 100.0% | 94.7% | 100.0% | 98.2% | 3.1% | 94.7% | 100.0% |
| CGP | 100.0% | 94.7% | 100.0% | 98.2% | 3.1% | 94.7% | 100.0% |
| DC | 75.0% | 75.0% | 50.0% | 66.7% | 14.4% | 50.0% | 75.0% |

---

## 2. Per-Test-Case Stability

| TC | Category | Pass Rate | Stability | Mean Score | Scores |
|----|----------|-----------|-----------|------------|--------|
| TC-01 | A | 67.0% | Volatile-Pass | 6.3 | 7, 6, 6 |
| TC-02 | A | 33.0% | Volatile-Fail | 6 | 6, 6, 6 |
| TC-03 | A | 67.0% | Volatile-Pass | 6.3 | 6, 6, 7 |
| TC-04 | A | 100.0% | Stable-Pass | 5.3 | 5, 6, 5 |
| TC-05 | B | 0.0% | Stable-Fail | 3.7 | 6, 0, 5 |
| TC-06 | B | 33.0% | Volatile-Fail | 6 | 5, 5, 8 |
| TC-07 | B | 33.0% | Volatile-Fail | 6.3 | 6, 7, 6 |
| TC-08 | C | 100.0% | Stable-Pass | 6.7 | 7, 7, 6 |
| TC-09 | C | 67.0% | Volatile-Pass | 6.3 | 6, 6, 7 |
| TC-10 | C | 100.0% | Stable-Pass | 6 | 6, 6, 6 |
| TC-11 | C | 100.0% | Stable-Pass | 6.3 | 7, 6, 6 |
| TC-12 | C | 33.0% | Volatile-Fail | 6 | 6, 6, 6 |
| TC-13 | D | 100.0% | Stable-Pass | 6 | 6, 6, 6 |
| TC-14 | D | 100.0% | Stable-Pass | 5.7 | 5, 6, 6 |
| TC-15 | E | 100.0% | Stable-Pass | 7.7 | 8, 7, 8 |
| TC-16 | F | 100.0% | Stable-Pass | 8 | 8, 8, 8 |
| TC-17 | F | 100.0% | Stable-Pass | 7.7 | 8, 8, 7 |
| TC-18 | F | 100.0% | Stable-Pass | 7 | 7, 7, 7 |
| TC-19 | F | 67.0% | Volatile-Pass | 7 | 8, 8, 5 |

---

## 3. Core Claims Confidence

| Claim | Metric | Mean | Min | Max | Std | Stable? |
|-------|--------|------|-----|-----|-----|---------|
| ME | 22.2% | 22.2% | 0.0% | 33.3% | 19.2% | No |
| CDA | 44.0% | 44.0% | 40.9% | 45.5% | 2.7% | Yes |
| ATC | 77.2% | 77.2% | 73.7% | 81.6% | 4.0% | Yes |
| BVC | 98.2% | 98.2% | 94.7% | 100.0% | 3.1% | Yes |
| CGP | 98.2% | 98.2% | 94.7% | 100.0% | 3.1% | Yes |
| DC | 66.7% | 66.7% | 50.0% | 75.0% | 14.4% | No |

---

## 4. Findings

**Stable dimensions (std < 5%):** CDA, ATC, BVC, CGP. These results are consistent across runs and can be reported with high confidence.

**Volatile dimensions (std >= 10%):** ME, DC. These results vary significantly between runs. Report the mean and range rather than a point estimate.


**BVC DROPPED BELOW 100% in run(s): [2].** This is a critical finding that must be investigated.

**CGP dropped below 100% in run(s): [2].** False positives detected — investigate the affected sessions.
