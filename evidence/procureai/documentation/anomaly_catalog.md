# Invoice Anomaly Catalog

Ground truth records deliberately injected test conditions. These labels support model evaluation and workflow demonstrations; none is proof of fraud or wrongdoing.

| Code | Meaning | Investigation evidence | Recommended routing |
|---|---|---|---|
| DUPLICATE_INVOICE | Probable duplicate of another invoice | Supplier, amount, date, normalized invoice number, and `duplicate_of_invoice_id` | AP review; hold recommendation only |
| PRICE_VARIANCE | Invoice unit price exceeds PO/contract tolerance | Invoice line, PO line, contract item, variance amount and percentage | Buyer/AP review |
| QUANTITY_VARIANCE | Invoiced quantity exceeds accepted receipt quantity | Invoice line, cumulative GRN accepted quantity, timing | Warehouse/AP review |
| MISSING_PO | Invoice or line lacks a valid PO reference | Invoice header/line and match trace | AP policy review |
| BANK_CHANGE | Bank-detail-change flag near submission | Invoice header flag and supplier context | Supplier master verification |
| TAX_VARIANCE | Tax amount or rate is inconsistent with expected calculation | Category tax baseline and invoice arithmetic | Tax/AP review |
| WEEKEND_SUBMISSION | Submission timing is unusual | Invoice/approval timestamp and illustrative calendar | Low-priority contextual review |

## Scoring requirements

- Preserve one row per invoice in the scored output.
- Return probability or normalized risk score, calibrated risk band, top reason codes, and evidence fields.
- Split train/validation/test chronologically; never use future outcomes or `duplicate_of_invoice_id` as a training feature.
- Report precision at review capacity, recall, PR-AUC, calibration, and confusion matrices by risk band.
- Compare against deterministic rules and a simple baseline. A complex model must earn its complexity.
- Evaluate cohorts by supplier tier, category, business unit, and invoice amount band.
- Route false-positive analysis into rule/feature refinement; do not silently relabel ground truth.

