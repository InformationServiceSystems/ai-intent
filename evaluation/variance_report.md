# AI-Intent Variance Report

**Runs:** 10
**Model:** llama3.1
**Test cases per run:** 19

---

## 1. Per-Dimension Scores Across Runs

| Dimension | Run1 | Run2 | Run3 | Run4 | Run5 | Run6 | Run7 | Run8 | Run9 | Run10 | Mean | Std | Min | Max |
|-----------|------|------|------|------|------|------|------|------|------|------|------|-----|-----|-----|
| ME | 50.0% | 33.3% | 66.7% | 0.0% | 33.3% | 0.0% | 33.3% | 33.3% | 66.7% | 33.3% | 35.0% | 22.9% | 0.0% | 66.7% |
| CDA | 36.4% | 50.0% | 31.8% | 36.4% | 27.3% | 40.9% | 45.5% | 31.8% | 36.4% | 50.0% | 38.6% | 7.8% | 27.3% | 50.0% |
| ATC | 78.9% | 71.1% | 68.4% | 76.3% | 71.1% | 73.7% | 68.4% | 76.3% | 68.4% | 60.5% | 71.3% | 5.3% | 60.5% | 78.9% |
| BVC | 100.0% | 100.0% | 94.7% | 100.0% | 94.7% | 100.0% | 100.0% | 94.7% | 94.7% | 100.0% | 97.9% | 2.7% | 94.7% | 100.0% |
| CGP | 100.0% | 100.0% | 94.7% | 100.0% | 94.7% | 100.0% | 100.0% | 94.7% | 94.7% | 100.0% | 97.9% | 2.7% | 94.7% | 100.0% |
| DC | 62.5% | 50.0% | 62.5% | 50.0% | 75.0% | 50.0% | 62.5% | 50.0% | 50.0% | 50.0% | 56.2% | 8.8% | 50.0% | 75.0% |

---

## 2. Per-Test-Case Stability

| TC | Category | Pass Rate | Stability | Mean Score | Scores |
|----|----------|-----------|-----------|------------|--------|
| TC-01 | A | 50.0% | Volatile-Pass | 5.3 | 6, 6, 5, 6, 6, 6, 6, 6, 0, 6 |
| TC-02 | A | 50.0% | Volatile-Pass | 6 | 6, 6, 6, 6, 6, 6, 6, 6, 6, 6 |
| TC-03 | A | 0.0% | Stable-Fail | 5.9 | 6, 6, 6, 6, 6, 5, 6, 6, 6, 6 |
| TC-04 | A | 100.0% | Stable-Pass | 5.6 | 5, 6, 6, 5, 5, 6, 6, 6, 6, 5 |
| TC-05 | B | 10.0% | Volatile-Fail | 6.1 | 6, 6, 8, 6, 6, 6, 6, 6, 6, 5 |
| TC-06 | B | 20.0% | Volatile-Fail | 5.5 | 7, 6, 5, 5, 5, 5, 5, 5, 7, 5 |
| TC-07 | B | 80.0% | Volatile-Pass | 6.8 | 7, 7, 7, 6, 7, 6, 7, 7, 7, 7 |
| TC-08 | C | 60.0% | Volatile-Pass | 6.2 | 6, 6, 6, 6, 6, 6, 7, 6, 6, 7 |
| TC-09 | C | 90.0% | Volatile-Pass | 6.3 | 6, 7, 6, 7, 6, 6, 6, 7, 6, 6 |
| TC-10 | C | 70.0% | Volatile-Pass | 6.1 | 6, 7, 6, 6, 6, 7, 5, 6, 6, 6 |
| TC-11 | C | 80.0% | Volatile-Pass | 5.4 | 6, 6, 0, 6, 6, 6, 6, 6, 6, 6 |
| TC-12 | C | 70.0% | Volatile-Pass | 6 | 6, 6, 6, 6, 6, 6, 6, 6, 6, 6 |
| TC-13 | D | 100.0% | Stable-Pass | 5.7 | 6, 5, 5, 6, 6, 5, 6, 6, 6, 6 |
| TC-14 | D | 100.0% | Stable-Pass | 5.2 | 6, 5, 5, 5, 5, 5, 5, 6, 5, 5 |
| TC-15 | E | 90.0% | Volatile-Pass | 6.8 | 8, 8, 8, 7, 0, 8, 7, 7, 8, 7 |
| TC-16 | F | 80.0% | Volatile-Pass | 7.4 | 8, 8, 8, 6, 8, 6, 8, 8, 6, 8 |
| TC-17 | F | 80.0% | Volatile-Pass | 6.9 | 7, 7, 8, 7, 7, 7, 6, 7, 7, 6 |
| TC-18 | F | 80.0% | Volatile-Pass | 6.9 | 6, 7, 7, 7, 8, 7, 7, 7, 6, 7 |
| TC-19 | F | 80.0% | Volatile-Pass | 6.5 | 8, 5, 6, 8, 8, 8, 8, 0, 8, 6 |

---

## 3. Core Claims Confidence

| Claim | Metric | Mean | Min | Max | Std | Stable? |
|-------|--------|------|-----|-----|-----|---------|
| ME | 35.0% | 35.0% | 0.0% | 66.7% | 22.9% | No |
| CDA | 38.6% | 38.6% | 27.3% | 50.0% | 7.8% | Borderline |
| ATC | 71.3% | 71.3% | 60.5% | 78.9% | 5.3% | Borderline |
| BVC | 97.9% | 97.9% | 94.7% | 100.0% | 2.7% | Yes |
| CGP | 97.9% | 97.9% | 94.7% | 100.0% | 2.7% | Yes |
| DC | 56.2% | 56.2% | 50.0% | 75.0% | 8.8% | Borderline |

---

## 4. Findings

**Stable dimensions (std < 5%):** BVC, CGP. These results are consistent across runs and can be reported with high confidence.

**Volatile dimensions (std >= 10%):** ME. These results vary significantly between runs. Report the mean and range rather than a point estimate.

**Borderline dimensions (5% <= std < 10%):** CDA, ATC, DC. Moderate variance — results are directionally reliable but exact percentages may shift.

**BVC DROPPED BELOW 100% in run(s): [3, 5, 8, 9].** This is a critical finding that must be investigated.

**CGP dropped below 100% in run(s): [3, 5, 8, 9].** False positives detected — investigate the affected sessions.
