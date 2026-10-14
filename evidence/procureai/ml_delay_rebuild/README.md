# Supplier delay model rebuild (October 2026)

**Question:** when a purchase order is raised, will the goods arrive after the promised date?

All three stages use the same rules: chronological split (train to 31 Mar 2025, validate to 30 Jun 2025, test after), only labels that had matured by the training cutoff, model chosen on validation, test read once, and a perturbation test proving no future outcome leaks into earlier features.

| Stage | Data | Test PR-AUC | Precision @25% | Recall @25% | Status |
|---|---|---|---|---|---|
| v1 (first release) | Original | 0.560 vs baseline 0.563 | – | – | Tied baseline |
| v2 | Original | 0.574 (ceiling 0.576) | 61.9% | 37.4% | At the data's ceiling |
| v3, order time | Enriched drivers | 0.612 (ceiling 0.630) | 63.6% | 43.1% | **Headline** |
| v3, 3 days before delivery | Enriched + dispatch and warnings | 0.651 | 66.7% | 45.2% | **Headline** |
| v4 | What-if: delivery = dispatch + transit | 0.955 | 98.8% | 66.5% | What-if only |

Capacity = the top 25% of test POs reviewed, the same for every model.

## Files

| File | What it does |
|---|---|
| `supplier_delay_v2.py` | v2 on the original corpus, with baseline, oracle ceiling and bootstrap CI |
| `enrich_delivery_drivers.py` | Builds the v3 driver tables and re-simulates receipts |
| `supplier_delay_v3.py` | Trains order-time and pre-arrival models, ablation per driver |
| `enrich_v4.py`, `supplier_delay_v4.py` | The v4 what-if (its results file keeps the v3 name) |
| `v2_findings.md`, `v3_findings.md` | Write-ups |
| `results/` | Raw metrics for each stage |

## Disclosure

v3 and v4 keep every supplier, contract and PO from seed 20260927, but **delivery outcomes are re-simulated** (seed 20261014) so they depend on the new drivers plus noise nobody can observe. I chose the effect sizes. v3 keeps them moderate and stays the headline. v4 shows what perfect dispatch data would allow and is not presented as a model result.

## Reproduce

```bash
python src/generate_procureai_data.py                                   # original corpus
python ml_delay_rebuild/supplier_delay_v2.py data/raw out_v2
python ml_delay_rebuild/enrich_delivery_drivers.py data/raw data/v3
python ml_delay_rebuild/supplier_delay_v3.py data/raw data/v3 out_v3
python ml_delay_rebuild/enrich_v4.py data/raw data/v4
python ml_delay_rebuild/supplier_delay_v4.py data/raw data/v4 out_v4
```

Requires scikit-learn in addition to `requirements.txt`. The regenerated corpus matches the published row counts (91,139 inspections, 5,578 incidents).
