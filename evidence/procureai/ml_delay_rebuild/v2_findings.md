# Supplier delay model v2: findings

**Question:** at the moment a PO is placed, will its goods arrive after the promised date?

## Why v1 tied its baseline

The generator (`src/generate_procureai_data.py`, lines 313–315) decides lateness with one formula:

```
late_prob = min(0.62, (1 - supplier_reliability) * 1.5 + 0.12 if promised month in {Apr, Oct, Nov, Dec})
```

Nothing else drives delay. So the best any model can do is learn (a) each supplier's reliability and (b) the four-month seasonal bump. Everything beyond that is a coin flip. Supplier history alone already captures (a), which is why v1 tied it.

## What v2 does

- Point-in-time supplier late rate (all history + last 90 days), smoothed toward the training average for new suppliers
- Promised-delivery month (the model is not told which months matter)
- Lead time, and lead time versus the supplier's usual
- Chronological split: train to 31 Mar 2025 (matured labels only, 1,410 censored POs excluded), validate to 30 Jun 2025, test after
- Model chosen on validation only; test read once
- Perturbation test: flipping outcomes after 1 Jan 2025 leaves every earlier feature unchanged (pass)

## Results on test (13,484 POs, 41% late)

| Model | PR-AUC | ROC-AUC | ECE | Precision @ capacity | Recall @ capacity |
|---|---|---|---|---|---|
| Baseline: supplier history | 0.565 | 0.682 | 0.033 | 0.612 | 0.370 |
| **v2: logistic + seasonality (chosen)** | **0.574** | **0.691** | **0.024** | **0.619** | **0.374** |
| v2: gradient boosting | 0.569 | 0.688 | 0.025 | 0.616 | 0.372 |
| Ceiling: generator's true probability | 0.576 | 0.696 | 0.010 | 0.627 | 0.378 |

Capacity = the same 3,371 reviews (25% of test POs) for every model, so recall is compared fairly.

- PR-AUC lift over baseline: +0.009, 95% bootstrap CI [+0.003, +0.017]. Small but real.
- v2 closes **84% of the gap** between the baseline and the theoretical ceiling.
- The model found the seasonal months on its own: Apr, Oct, Nov and Dec are the only positive month coefficients.
- Boosting did not beat logistic regression, as expected when the true signal is additive.

## The honest conclusion

v2 is now within 0.002 PR-AUC of the best score this dataset allows. Further tuning cannot add meaningful lift; the remaining error is randomness built into the generator. To show a bigger modelling win, the generator itself needs richer delay drivers (lane distance, order size against capacity, supplier load, festival or monsoon disruption).

## Reproduce

```bash
python src/generate_procureai_data.py          # seed 20260927
python supplier_delay_v2.py data/raw out/      # writes out/delay_v2_results.json
```

Data regenerated with seed 20260927 matches the published row counts (91,139 inspections, 5,578 incidents). Unit here is the non-cancelled PO, so figures differ slightly from v1's published 0.560 / 0.563.
