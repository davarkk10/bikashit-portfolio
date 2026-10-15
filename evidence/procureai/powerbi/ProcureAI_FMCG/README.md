# ProcureAI FMCG: Power BI report (PBIP)

The full 12-page report as a Power BI Project. Open `ProcureAI_FMCG.pbip` in Power BI Desktop.

| Page | What it shows |
|---|---|
| 00 Briefing | Four findings, each linked to its evidence page |
| 01 Executive cockpit | Spend, off-contract share, OTIF, exception value |
| 02 Spend & category | Spend and price variance by category, top suppliers |
| 03 Supplier 360 | OTIF, defect rate, composite supplier risk |
| 04 Invoice exceptions | Exception reasons and the review queue |
| 05 Contract intelligence | Expiries, off-contract buying |
| 06 Cash & approvals | Payment timing, discounts, approval cycle |
| 07 Data quality | Monitoring snapshot, reconciled KPIs |
| 08 Record drill-through | One record end to end |
| 09 Invoice risk model | Model vs hand-written rules: PR-AUC 0.86 on hard cases, 92.6% precision at review capacity |
| 10 Late-delivery model | PR-AUC 0.61 at order time, 0.65 three days before arrival; drivers and watch list |
| 11 Contract assistant | 64/68 on a locked question set, 0 wrong answers, 6/6 correct refusals |

Pages 09–11 use the October 2026 model rebuild (`../../ml_delay_rebuild`, `../../invoice_anomaly_v2`, `../../contract_assistant_v2`).

## Data

Three parameters (Transform data → Edit parameters):

- `pSourceMode`: `PostgreSQL` (warehouse at `pServer`/`pDatabase`) or `CsvFolder`.
- `pCsvFolder`: folder of exported warehouse tables, used when `pSourceMode = CsvFolder`.
- `pModelFolder`: the `model_results` folder next to this file. Set it to its full path on your machine, then refresh.

`model_results/expected_values.json` lists the numbers pages 09–11 should show after a refresh.

## Model

29 tables (6 for model results), 60 business measures plus 14 presentation helpers, 49 relationships, none bidirectional, 5 row-level security roles. The build scripts that added pages 09–11 are in `../build`.
