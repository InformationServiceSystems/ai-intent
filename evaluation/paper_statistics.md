# Paper Statistics — Updated Figures

**Generated:** 2026-04-14T08:05:09.270475+00:00

## CDA (Constraint Detection Accuracy)

- **Conditioned:** 50.6% (std 5.3%, range 41.7--58.3%)
- **Unconditioned:** 38.6% (original variance report figure)
- Denominator change: violation-occurring sessions only

## DC (Disposition Containment)

- **Criterion A (containment):** 80.0%
- **Criterion B (strict rubric):** 57.5% (std 36.8%)

## Self-Compliance Violation Rates

- **Neutral disposition:** 12.9%
- **Overall (all presets):** 25.6%

## What Changed and Why

1. **CDA:** Denominator corrected. The original figure (38.6%) included violation-free sessions scoring 2 by default, diluting the rate. The conditioned figure measures detection accuracy only over sessions where the compliance gate actually had violations to detect.

2. **DC:** Split into two criteria. Criterion A (containment) checks whether mandate limits hold in the final output — this is the primary safety claim. Criterion B (strict) additionally penalizes needing more revisions than the neutral baseline, measuring compliance effort overhead.

3. **Self-compliance:** New analysis quantifying first-attempt violation rates to support the necessity argument for external compliance gating.