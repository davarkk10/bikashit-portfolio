# ProcureAI FMCG Business Rules

## Reporting scope

- Company records are synthetic and cover 2024-01-01 through 2025-12-31.
- INR is the reporting currency. No foreign-exchange conversion is required in the supplied baseline.
- Posted invoices drive realized spend. Purchase orders drive committed spend.
- Cancelled purchase orders are excluded from supplier delivery-service denominators.
- Retain original promised dates for delivery measurement; later revised dates must not overwrite the baseline.

## Spend and compliance

- Realized net spend is the sum of `invoice_lines.line_net_amount` for posted invoice headers.
- Realized gross spend is the sum of `invoice_headers.invoice_gross_amount` for posted invoices.
- Contracted spend is invoice-line net spend whose linked PO header has `contract_valid_at_order_flag = true`.
- Off-contract spend is invoice-line net spend whose linked PO is absent, lacks a valid contract at order date, or cannot be matched to a contract line.
- Purchase price variance is `(actual unit price - baseline unit price) * quantity`; show price and volume effects separately where possible.
- Savings are not automatically inferred from lower price. A savings claim requires an explicit approved baseline and methodology.

## Three-way match

- Match at invoice line to PO line, then compare invoiced quantity with cumulative accepted receipt quantity.
- A missing PO-line link is an exception, not a zero-valued match.
- Default price tolerance is the applicable contract-item tolerance; use 2% only where no explicit tolerance exists.
- Quantity exception: invoiced quantity exceeds cumulative accepted quantity at the as-of timestamp.
- Price exception: absolute invoice/PO unit-price variance exceeds the applicable tolerance.
- Duplicate indicators are investigative leads, never confirmed fraud.

## Supplier delivery and quality

- On-time: final receipt date is on or before the original promised date.
- In-full: cumulative accepted quantity is at least ordered quantity.
- OTIF: both on-time and in-full are true.
- Defect rate is rejected inspection quantity divided by inspected quantity; protect all zero denominators.
- Supplier metrics must expose eligible record counts and suppress or flag very small samples.

## Payment and working capital

- On-time payment compares `payment_date` with invoice `due_date`.
- Early-payment discount opportunity is reported only when the invoice and payment term qualify and the payment date can still meet the discount window.
- A paid invoice must reconcile to a payment unless explicitly documented as a partial-payment scenario; the supplied baseline contains no partial payments.

## Contract operations

- A contract is active for a date only when the date falls inclusively between start and end dates and status permits use.
- Expiry buckets are 0-30, 31-60, 61-90, and over 90 days.
- Auto-renewal and termination-notice clauses are surfaced as review obligations, not legal conclusions.
- All generated contract answers must cite document filename and page; unsupported answers must abstain.

## Workflow controls

- Every invoice has three approval events in chronological order in the supplied baseline.
- Automated systems may classify, summarize, rank, and draft recommendations.
- A named human must approve any consequential action.
- Payment release, contract amendment, and supplier-bank/master changes are prohibited autonomous actions.

