# Invoice anomaly v2: conditions rules miss (October 2026)

**Why:** in the first release every injected anomaly (price +8–25%, quantity +5–18%, missing PO, bank change, exact duplicate) was caught by simple rules, so the model tied refined rules at PR-AUC 1.000 and showed no value.

**What changed:** the original invoices and anomalies are kept. Three conditions that single-invoice rules miss are added, each with a legitimate look-alike so they can't be separated trivially.

| Condition | What happens | Legitimate look-alike |
|---|---|---|
| Split below approval | A large bill split into 2–3 invoices under the INR 10 lakh senior-approval limit, within a week | Staged deliveries billed per truckload, some sized just under the limit |
| Price creep | 8 suppliers bill +0.5–1.9% over PO price for months, inside the 2% tolerance | Approved freight surcharges of +0.5–1.8% from 10 other suppliers |
| Near-duplicate | An earlier invoice resubmitted weeks later with an altered number and a slightly changed amount | Corrected re-issues of rejected invoices (status not always updated) |

Plus in-tolerance price noise on 18% of clean invoices and legitimate two-part billing on 6% of POs.

## Results (test: 14,570 invoices after 30 Jun 2025, 1,546 with a condition)

Review capacity = 1,546 invoices, the number of true conditions.

| Method | PR-AUC | Precision at capacity |
|---|---|---|
| Policy rules as written | 0.196 | 23.4% |
| Best hand-written rules (tolerance-aware match, near-duplicate, over-billing, split and creep checks) | 0.812 | 77.8% |
| **Gradient-boosted model** | **0.980** | **92.6%** |

Model minus best rules: +0.17 PR-AUC, 95% bootstrap CI [+0.15, +0.18].

**On the three new conditions only:** best rules 0.188 PR-AUC, model **0.858**.

| Condition | Best rules catch | Model catches (at capacity) |
|---|---|---|
| Price creep | 30% | 69% |
| Split below approval | 46% | 88% |
| Near-duplicate | 100% | 98% |
| First-release conditions | 100% | 100% |

## Honest reading

- The overall 0.980 is lifted by the first-release conditions, which are still easy. The 0.858 on the new conditions is the number that matters.
- The model's edge is on patterns that need history: a supplier's price variance over months, and several invoices on one PO near the limit. Rules still win narrowly on near-duplicates.
- I designed the new conditions and their look-alikes. Real fraud is rarer and more varied, so real-world scores would be lower.

## Reproduce

```bash
python src/generate_procureai_data.py
python invoice_anomaly_v2/invoice_anomaly_v2.py data/raw data/ground_truth out_inv
```
