from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
GT = ROOT / "data" / "ground_truth"
VALID = ROOT / "validation"
DOC = ROOT / "documentation"
DB = ROOT / "database"


def load(name, parse_dates=None):
    return pd.read_csv(RAW / name, parse_dates=parse_dates or [])


results = []


def check(area, test, actual, expected, passed, severity="ERROR", note=""):
    results.append({"area": area, "test": test, "actual": actual, "expected": expected, "status": "PASS" if passed else "FAIL", "severity": severity, "note": note})


def unique_key(df, col, name):
    dup = int(df[col].duplicated().sum())
    check("Keys", f"{name}.{col} unique", dup, 0, dup == 0)


def fk(child, child_col, parent, parent_col, name, allow_null=True):
    s = child[child_col]
    if allow_null:
        s = s.dropna()
    orphan = int((~s.isin(parent[parent_col])).sum())
    check("Foreign keys", name, orphan, 0, orphan == 0)


def sql_type(series):
    name = series.name.lower()
    # Identifier columns must remain textual even when an early sample is all
    # null (for example duplicate_of_invoice_id) or happens to look numeric.
    if name.endswith("_id"): return "TEXT"
    if "timestamp" in name: return "TIMESTAMP"
    if name.endswith("_date") or name in {"order_date", "due_date", "receipt_date", "event_date", "valid_until"}: return "DATE"
    if pd.api.types.is_bool_dtype(series): return "BOOLEAN"
    if pd.api.types.is_integer_dtype(series): return "BIGINT"
    if pd.api.types.is_float_dtype(series): return "NUMERIC(18,4)"
    return "TEXT"


DESCRIPTIONS = {
    "supplier_id": "Stable synthetic supplier identifier", "material_id": "Stable material or service identifier",
    "po_id": "Purchase order identifier", "po_line_id": "Purchase order line identifier",
    "grn_id": "Goods receipt identifier", "grn_line_id": "Goods receipt line identifier",
    "invoice_id": "Invoice identifier", "invoice_line_id": "Invoice line identifier",
    "contract_id": "Supplier contract identifier", "contract_item_id": "Contracted material line identifier",
    "ordered_quantity": "Quantity ordered in the stated unit", "received_quantity": "Quantity physically received",
    "accepted_quantity": "Received quantity accepted after inspection", "rejected_quantity": "Received quantity rejected",
    "unit_price": "Purchase order unit price in INR", "invoice_unit_price": "Invoice unit price in INR",
    "line_net_amount": "Quantity multiplied by unit price before tax", "line_tax_amount": "Calculated tax amount",
    "line_gross_amount": "Net amount plus tax", "contract_valid_at_order_flag": "Whether the linked contract covers the PO date",
    "original_promised_date": "Original supplier promise date retained for service measurement",
    "bank_detail_change_flag": "Synthetic indicator that bank details changed near invoice submission",
    "duplicate_of_invoice_id": "Original invoice copied by a deliberately injected probable duplicate",
    "document_path": "Relative path to the supporting synthetic PDF when generated",
}


def build_data_dictionary(csv_files):
    rows = []
    for p in csv_files:
        df = pd.read_csv(p, nrows=200)
        for col in df.columns:
            s = df[col]
            rows.append({
                "table": p.stem,
                "column": col,
                "inferred_type": sql_type(s),
                "nullable_in_sample": bool(s.isna().any()),
                "description": DESCRIPTIONS.get(col, col.replace("_", " ").capitalize()),
                "source": "Deterministic synthetic generator",
            })
    out = pd.DataFrame(rows)
    out.to_csv(DOC / "data_dictionary.csv", index=False)
    return out


def build_sql(csv_files):
    ddl = ["CREATE SCHEMA IF NOT EXISTS raw;", "CREATE SCHEMA IF NOT EXISTS mart;", ""]
    loads = []
    for p in csv_files:
        df = pd.read_csv(p, nrows=300)
        cols = []
        for col in df.columns:
            cols.append(f'    "{col}" {sql_type(df[col])}')
        ddl.append(f'CREATE TABLE IF NOT EXISTS raw."{p.stem}" (\n' + ",\n".join(cols) + "\n);\n")
        loads.append(f"\\copy raw.\"{p.stem}\" FROM 'data/raw/{p.name}' WITH (FORMAT csv, HEADER true, NULL '');")
    (DB / "01_raw_schema.sql").write_text("\n".join(ddl), encoding="utf-8")
    (DB / "02_load_raw.sql").write_text("\n".join(loads) + "\n", encoding="utf-8")
    marts = r'''CREATE OR REPLACE VIEW mart.v_invoice_three_way_match AS
SELECT ih.invoice_id,
       ih.supplier_id,
       ih.po_id,
       ih.invoice_date,
       ih.invoice_gross_amount,
       SUM(il.invoiced_quantity) AS invoiced_quantity,
       SUM(COALESCE(gr.accepted_quantity,0)) AS accepted_quantity,
       MAX(CASE WHEN il.po_line_id IS NULL THEN 1 ELSE 0 END) AS missing_po_reference_flag,
       MAX(CASE WHEN ABS(il.invoice_unit_price - pol.unit_price) > pol.unit_price * 0.02 THEN 1 ELSE 0 END) AS price_exception_flag,
       MAX(CASE WHEN il.invoiced_quantity > COALESCE(gr.accepted_quantity,0) THEN 1 ELSE 0 END) AS quantity_exception_flag,
       MAX(CASE WHEN ih.duplicate_of_invoice_id IS NOT NULL THEN 1 ELSE 0 END) AS probable_duplicate_flag,
       MAX(CASE WHEN ih.bank_detail_change_flag THEN 1 ELSE 0 END) AS bank_change_flag
FROM raw.invoice_headers ih
JOIN raw.invoice_lines il ON il.invoice_id = ih.invoice_id
LEFT JOIN raw.purchase_order_lines pol ON pol.po_line_id = il.po_line_id
LEFT JOIN (
  SELECT po_line_id, SUM(accepted_quantity) accepted_quantity
  FROM raw.goods_receipt_lines GROUP BY po_line_id
) gr ON gr.po_line_id = il.po_line_id
GROUP BY ih.invoice_id, ih.supplier_id, ih.po_id, ih.invoice_date, ih.invoice_gross_amount;

CREATE OR REPLACE VIEW mart.v_supplier_service AS
SELECT poh.supplier_id,
       COUNT(*) FILTER (WHERE poh.po_status <> 'Cancelled') AS eligible_po_lines,
       AVG(CASE WHEN gr.accepted_quantity >= pol.ordered_quantity THEN 1.0 ELSE 0.0 END) AS in_full_rate,
       AVG(CASE WHEN gr.receipt_date <= pol.original_promised_date THEN 1.0 ELSE 0.0 END) AS on_time_rate,
       AVG(CASE WHEN gr.accepted_quantity >= pol.ordered_quantity AND gr.receipt_date <= pol.original_promised_date THEN 1.0 ELSE 0.0 END) AS otif_rate
FROM raw.purchase_order_headers poh
JOIN raw.purchase_order_lines pol ON pol.po_id = poh.po_id
LEFT JOIN (
  SELECT po_line_id, SUM(accepted_quantity) accepted_quantity, MAX(receipt_date) receipt_date
  FROM raw.goods_receipt_lines GROUP BY po_line_id
) gr ON gr.po_line_id = pol.po_line_id
WHERE poh.po_status <> 'Cancelled'
GROUP BY poh.supplier_id;

CREATE OR REPLACE VIEW mart.v_spend_contract_compliance AS
SELECT poh.business_unit_id,
       poh.supplier_id,
       pol.material_id,
       DATE_TRUNC('month', ih.invoice_date) AS spend_month,
       SUM(il.line_net_amount) AS net_spend,
       SUM(CASE WHEN poh.contract_valid_at_order_flag THEN il.line_net_amount ELSE 0 END) AS contracted_spend,
       SUM(CASE WHEN NOT poh.contract_valid_at_order_flag THEN il.line_net_amount ELSE 0 END) AS off_contract_spend
FROM raw.invoice_headers ih
JOIN raw.invoice_lines il ON il.invoice_id = ih.invoice_id
LEFT JOIN raw.purchase_order_lines pol ON pol.po_line_id = il.po_line_id
LEFT JOIN raw.purchase_order_headers poh ON poh.po_id = pol.po_id
WHERE ih.invoice_status = 'Posted'
GROUP BY poh.business_unit_id, poh.supplier_id, pol.material_id, DATE_TRUNC('month', ih.invoice_date);
'''
    (DB / "03_mart_views.sql").write_text(marts, encoding="utf-8")


def main():
    VALID.mkdir(parents=True, exist_ok=True); DOC.mkdir(parents=True, exist_ok=True); DB.mkdir(parents=True, exist_ok=True)
    suppliers = load("suppliers.csv")
    materials = load("materials.csv")
    warehouses = load("warehouses.csv")
    buyers = load("buyers.csv")
    contracts = load("contracts.csv", ["start_date", "end_date"])
    contract_items = load("contract_items.csv")
    po_h = load("purchase_order_headers.csv", ["order_date", "promised_delivery_date"])
    po_l = load("purchase_order_lines.csv", ["original_promised_date"])
    gr_h = load("goods_receipt_headers.csv", ["receipt_date"])
    gr_l = load("goods_receipt_lines.csv", ["receipt_date"])
    inv_h = load("invoice_headers.csv", ["invoice_date", "due_date"])
    inv_l = load("invoice_lines.csv")
    approvals = load("invoice_approvals.csv", ["event_timestamp"])
    payments = load("payments.csv", ["payment_date"])

    check("Scale", "supplier count", len(suppliers), "150 to 200", 150 <= len(suppliers) <= 200)
    check("Scale", "material count", len(materials), "1500 to 2000", 1500 <= len(materials) <= 2000)
    check("Scale", "purchase order count", len(po_h), "50000 to 60000", 50000 <= len(po_h) <= 60000)
    check("Scale", "purchase order line count", len(po_l), "200000 to 250000", 200000 <= len(po_l) <= 250000)
    check("Scale", "invoice count", len(inv_h), "45000 to 55000", 45000 <= len(inv_h) <= 55000)
    check("Scale", "supporting PDF count", len(list((ROOT / "documents").rglob("*.pdf"))), "400 to 600", 400 <= len(list((ROOT / "documents").rglob("*.pdf"))) <= 600)

    for df, col, name in [(suppliers,"supplier_id","suppliers"),(materials,"material_id","materials"),(contracts,"contract_id","contracts"),(contract_items,"contract_item_id","contract_items"),(po_h,"po_id","purchase_order_headers"),(po_l,"po_line_id","purchase_order_lines"),(gr_h,"grn_id","goods_receipt_headers"),(gr_l,"grn_line_id","goods_receipt_lines"),(inv_h,"invoice_id","invoice_headers"),(inv_l,"invoice_line_id","invoice_lines"),(approvals,"approval_event_id","invoice_approvals"),(payments,"payment_id","payments")]:
        unique_key(df, col, name)

    fk(po_h,"supplier_id",suppliers,"supplier_id","PO header supplier")
    fk(po_h,"warehouse_id",warehouses,"warehouse_id","PO header warehouse")
    fk(po_h,"buyer_id",buyers,"buyer_id","PO header buyer")
    fk(po_h,"contract_id",contracts,"contract_id","PO header contract",True)
    fk(po_l,"po_id",po_h,"po_id","PO line header")
    fk(po_l,"material_id",materials,"material_id","PO line material")
    fk(gr_h,"po_id",po_h,"po_id","GRN header PO")
    fk(gr_l,"grn_id",gr_h,"grn_id","GRN line header")
    fk(gr_l,"po_line_id",po_l,"po_line_id","GRN line PO line")
    fk(inv_h,"supplier_id",suppliers,"supplier_id","invoice supplier")
    fk(inv_h,"po_id",po_h,"po_id","invoice PO",True)
    fk(inv_l,"invoice_id",inv_h,"invoice_id","invoice line header")
    fk(inv_l,"po_line_id",po_l,"po_line_id","invoice line PO line",True)
    fk(approvals,"invoice_id",inv_h,"invoice_id","approval invoice")
    fk(payments,"invoice_id",inv_h,"invoice_id","payment invoice")

    po_net_err = (po_l.line_net_amount - po_l.ordered_quantity * po_l.unit_price).abs().max()
    po_gross_err = (po_l.line_gross_amount - po_l.line_net_amount - po_l.line_tax_amount).abs().max()
    check("Finance", "PO line net arithmetic max error", round(float(po_net_err),2), "<= 0.01", po_net_err <= 0.011)
    check("Finance", "PO line gross arithmetic max error", round(float(po_gross_err),2), "<= 0.01", po_gross_err <= 0.011)
    inv_net_err = (inv_l.line_net_amount - inv_l.invoiced_quantity * inv_l.invoice_unit_price).abs().max()
    check("Finance", "invoice line net arithmetic max error", round(float(inv_net_err),2), "<= 0.01", inv_net_err <= 0.011)
    inv_sums = inv_l.groupby("invoice_id")[["line_net_amount","line_tax_amount","line_gross_amount"]].sum().round(2)
    merged = inv_h.set_index("invoice_id").join(inv_sums)
    header_err = (merged.invoice_gross_amount - merged.line_gross_amount).abs().max()
    check("Finance", "invoice header to line gross max error", round(float(header_err),2), "<= 0.01", header_err <= 0.011)
    qty_err = (gr_l.received_quantity - gr_l.accepted_quantity - gr_l.rejected_quantity).abs().max()
    check("Receiving", "receipt accepted plus rejected", int(qty_err), 0, qty_err == 0)
    pay_merge = payments.merge(inv_h[["invoice_id","invoice_gross_amount"]], on="invoice_id", how="left")
    pay_err = (pay_merge.payment_amount - pay_merge.invoice_gross_amount).abs().max()
    check("Finance", "payment equals approved invoice gross", round(float(pay_err),2), "<= 0.01", pay_err <= 0.011)
    approval_counts = approvals.groupby("invoice_id").size()
    check("Workflow", "three approval events per invoice", int((approval_counts != 3).sum()), 0, (approval_counts != 3).sum() == 0)
    lifecycle_bad = 0
    for _, g in approvals.sort_values("event_timestamp").groupby("invoice_id"):
        if list(g.approval_status)[:2] != ["Submitted", "In review"]:
            lifecycle_bad += 1
    check("Workflow", "approval lifecycle order", lifecycle_bad, 0, lifecycle_bad == 0)

    gt = pd.read_csv(GT / "invoice_anomaly_ground_truth.csv")
    check("Ground truth", "anomaly IDs exist", int((~gt.invoice_id.isin(inv_h.invoice_id)).sum()), 0, gt.invoice_id.isin(inv_h.invoice_id).all())
    dup_count = int(inv_h.duplicate_of_invoice_id.notna().sum())
    check("Ground truth", "probable duplicate invoices", dup_count, 500, dup_count == 500)
    check("Ground truth", "duplicate source IDs exist", int((~inv_h.duplicate_of_invoice_id.dropna().isin(inv_h.invoice_id)).sum()), 0, inv_h.duplicate_of_invoice_id.dropna().isin(inv_h.invoice_id).all())

    pdfs = list((ROOT / "documents").rglob("*.pdf"))
    pdf_fail = 0; empty_text = 0
    for p in pdfs:
        try:
            reader = PdfReader(str(p))
            txt = "".join((page.extract_text() or "") for page in reader.pages)
            if len(txt.strip()) < 40: empty_text += 1
        except Exception:
            pdf_fail += 1
    check("Documents", "PDF files readable", pdf_fail, 0, pdf_fail == 0)
    check("Documents", "PDF files contain extractable text", empty_text, 0, empty_text == 0)

    res = pd.DataFrame(results)
    res.to_csv(VALID / "validation_results.csv", index=False)
    passed = int((res.status == "PASS").sum()); failed = int((res.status == "FAIL").sum())
    summary = {"tests": len(res), "passed": passed, "failed": failed, "status": "PASS" if failed == 0 else "FAIL"}
    (VALID / "validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    md = ["# ProcureAI Dataset Validation Report", "", f"Overall status: **{summary['status']}**", "", f"Tests: {len(res)}  |  Passed: {passed}  |  Failed: {failed}", "", "## Test results", "", "| Area | Test | Actual | Expected | Status |", "|---|---|---:|---:|---|"]
    for x in res.itertuples(index=False):
        md.append(f"| {x.area} | {x.test} | {x.actual} | {x.expected} | {x.status} |")
    md.extend(["", "## Limitations", "", "- Records and documents are synthetic and do not represent a real company.", "- Anomaly ground truth records injected conditions, not confirmed fraud.", "- Public benchmarks, if added later, must remain separate from company tables.", "- Native Power BI and Power Automate artefacts require assembly in their respective desktop or cloud environments."])
    (VALID / "validation_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    csv_files = sorted(RAW.glob("*.csv"))
    build_data_dictionary(csv_files)
    build_sql(csv_files)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
