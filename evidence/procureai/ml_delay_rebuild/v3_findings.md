# Supplier delay model v3: richer delivery drivers

**Question (unchanged):** will this PO be received after its promised date?
**What changed:** the data. v2 had already reached the ceiling of the original corpus (PR-AUC 0.574 vs 0.576), so the only way up was information that actually explains delays.

## Important disclosure

The original corpus decides lateness from supplier reliability and month alone. For v3, every master record, contract and PO from seed 20260927 is kept, new driver tables are added, and **delivery outcomes are re-simulated** so they depend on those drivers plus noise nobody can observe. I chose the effect sizes and kept them moderate on purpose. Larger effects would give higher scores, so the score is partly a design choice. Say this on the case-study page.

## New data, and why each matters in Assam

| Table | What it holds | Known when |
|---|---|---|
| `supplier_lanes.csv` | Road distance per supplier-warehouse lane, route (local NE or via the Siliguri corridor), quoted lead time | Order date |
| `supplier_capacity.csv` | POs a supplier can handle per 30 days; load = orders placed in the last 30 days ÷ capacity | Order date |
| `region_flood_risk.csv` | Monthly flood or landslide probability for upper and lower Brahmaputra, Barak valley and the Siliguri corridor | Order date (published history) |
| `festival_calendar.csv` | Bohag Bihu, Durga Puja and Diwali freight slowdowns | Order date |
| Order size | PO quantity against the supplier's past median | Order date |
| `asn_dispatch.csv` | Planned vs actual dispatch date from the supplier's shipping notice | Before delivery |
| `disruption_advisories.csv` | Flood, bandh and NH closure warnings, issued 2–7 days ahead; 20% of events unannounced, some false alarms | Before delivery |

## Results on test (13,484 POs, 37% late)

| Model | When it scores | PR-AUC | Precision @25% | Recall @25% |
|---|---|---|---|---|
| v2 features only | Order date | 0.563 | 58.9% | 39.9% |
| **v3: + new drivers** | **Order date** | **0.612** | **63.6%** | **43.1%** |
| Order-time ceiling | Order date | 0.630 | 64.8% | 43.9% |
| **v3 pre-arrival: + dispatch notice and advisories** | **3 days before promised date** | **0.651** | **66.7%** | **45.2%** |
| Pre-arrival upper bound | 3 days before | 0.714 | 72.9% | 49.4% |

- v3 lift over v2 features: **+0.049 PR-AUC**, 95% bootstrap CI [+0.040, +0.057]
- v3 order-time closes 73% of the gap to its ceiling
- Pre-arrival, the top 10% of flagged POs are **79% truly late** (vs 74% at order time)
- Calibration stays good (ECE 0.020 order-time, 0.032 pre-arrival)
- Leakage test passes; model chosen on validation; test read once

## Which drivers mattered (drop in validation PR-AUC when removed)

1. Supplier load: 0.038 (by far the biggest)
2. Promised vs quoted lead time: 0.007
3. Festival calendar: 0.003
4. Order size and distance: 0.002 each
5. Flood climatology: no gain. Knowing a month is risky doesn't say which week floods; the advisories carry that signal at the pre-arrival checkpoint instead

## What this means for the business

- At order time, the biggest win is **not overloading suppliers**. Load is something buyers control.
- Some delays cannot be known when the PO is raised. A second check three days before delivery, using the supplier's dispatch notice and flood or bandh warnings, catches more of them.
- Order-time score: decide whether to split the order or pick another supplier. Pre-arrival score: warn the warehouse and adjust stock plans.

## Reproduce

```bash
python src/generate_procureai_data.py                       # original corpus, seed 20260927
python enrich_delivery_drivers.py data/raw data/v3          # new tables + re-simulated receipts (seed 20261014)
python supplier_delay_v3.py data/raw data/v3 out/           # writes out/delay_v3_results.json
```
