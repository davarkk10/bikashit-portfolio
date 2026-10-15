# ProcureAI Power BI: build scripts for pages 09–11

The report in `../ProcureAI_FMCG/` was finished in Power BI Desktop (pages 00–08). These scripts added the October 2026 model results to it as pages 09–11, then the project was opened, refreshed and saved in Desktop.

| Script | What it does |
|---|---|
| `build_pbi_data.py` | Turns the model outputs into scored invoice/PO rows and results tables |
| `make_data.py` | Writes those into `model_results/` with date keys that join to `Date` |
| `add_model.py` | Adds 6 tables, 28 measures, 5 relationships and the `pModelFolder` parameter to the TMDL model |
| `bg_render.py` | Renders page backgrounds and the 12-item side menu (needs Manrope and JetBrains Mono in `fonts/` or `$PROCUREAI_FONTS`) |
| `build_pages.py` | Builds pages 09–11, re-skins the side menu on pages 00–08, wires the menu buttons |
| `polish.py` | Column widths, word wrap, sort order, hidden auto titles |
| `patch_brief.py` | Updates the Briefing page's model counts |
| `check_real.py` | Confirms every DAX and visual field reference resolves (auto date tables are flagged and can be ignored) |

## Rebuild

```bash
# from evidence/procureai
python invoice_anomaly_v2/invoice_anomaly_v2.py data/raw data/ground_truth out_inv pbi_data
python ml_delay_rebuild/enrich_delivery_drivers.py data/raw data/v3
python ml_delay_rebuild/supplier_delay_v3.py data/raw data/v3 out_v3 pbi_data
python contract_assistant_v2/evaluate.py documents contract_assistant_v2/questions/heldout.jsonl heldout_first_run.json
python powerbi/build/build_pbi_data.py data/raw pbi_data out_inv/invoice_v2_results.json out_v3/delay_v3_results.json heldout_first_run.json
python powerbi/build/make_data.py pbi_data powerbi/ProcureAI_FMCG/model_results
python powerbi/build/check_real.py powerbi/ProcureAI_FMCG
```

`add_model.py`, `build_pages.py` and `polish.py` have already been applied to `../ProcureAI_FMCG`; run them only on a copy of the report from before pages 09–11.
