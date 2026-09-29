#!/usr/bin/env python3
"""Build and validate the ProcureAI Release 1 analytical warehouse.

This executable reference implementation mirrors the PostgreSQL warehouse at
the documented business grains.  It is deliberately dependency-light so that
the transformation and reconciliation logic can be proved even where a
PostgreSQL service is unavailable.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
GROUND = ROOT / "data" / "ground_truth"
OUT = ROOT / "artifacts" / "release1"
MART = OUT / "marts"
CORE = OUT / "core"


def load(name: str, dates: tuple[str, ...] = ()) -> pd.DataFrame:
    frame = pd.read_csv(RAW / f"{name}.csv", low_memory=False)
    for column in dates:
        frame[column] = pd.to_datetime(frame[column], errors="raise")
    return frame


def write(frame: pd.DataFrame, folder: Path, name: str) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.csv"
    frame.to_csv(path, index=False, date_format="%Y-%m-%d")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"artifact": str(path.relative_to(ROOT)), "rows": int(len(frame)), "sha256": digest}


def assert_test(results: list[dict], area: str, name: str, actual, expected, passed: bool) -> None:
    results.append({
        "area": area,
        "test": name,
        "actual": actual,
        "expected": expected,
        "status": "PASS" if passed else "FAIL",
    })


def build() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    categories = load("categories")
    business_units = load("business_units")
    buyers = load("buyers")
    payment_terms = load("payment_terms")
    suppliers = load("suppliers")
    warehouses = load("warehouses")
    materials = load("materials")
    contracts = load("contracts", ("start_date", "end_date"))
    po_h = load("purchase_order_headers", ("order_date", "promised_delivery_date"))
    po_l = load("purchase_order_lines", ("original_promised_date",))
    grn_l = load("goods_receipt_lines", ("receipt_date",))
    inv_h = load("invoice_headers", ("invoice_date", "due_date"))
    inv_l = load("invoice_lines")
    approvals = load("invoice_approvals", ("event_timestamp",))
    payments = load("payments", ("payment_date",))
    quality = load("quality_inspections", ("inspection_date",))
    incidents = load("supplier_incidents", ("incident_date",))

    artifacts: list[dict] = []

    # Conformed dimensions. Source identifiers remain durable business keys.
    dimensions = {
        "dim_category": categories,
        "dim_business_unit": business_units,
        "dim_buyer": buyers,
        "dim_payment_term": payment_terms,
        "dim_supplier": suppliers,
        "dim_warehouse": warehouses,
        "dim_material": materials,
        "dim_contract": contracts,
    }
    dates = pd.date_range("2023-01-01", "2027-12-31", freq="D")
    dim_date = pd.DataFrame({"full_date": dates})
    dim_date["date_key"] = dim_date["full_date"].dt.strftime("%Y%m%d").astype(int)
    dim_date["year"] = dim_date["full_date"].dt.year
    dim_date["quarter"] = "Q" + dim_date["full_date"].dt.quarter.astype(str)
    dim_date["month_number"] = dim_date["full_date"].dt.month
    dim_date["month_name"] = dim_date["full_date"].dt.month_name()
    dim_date["year_month"] = dim_date["full_date"].dt.strftime("%Y-%m")
    dim_date["week_number"] = dim_date["full_date"].dt.isocalendar().week.astype(int)
    dim_date["day_of_week"] = dim_date["full_date"].dt.day_name()
    dim_date["is_weekend"] = dim_date["full_date"].dt.dayofweek.ge(5)
    dimensions["dim_date"] = dim_date
    dimensions["dim_invoice"] = inv_h
    dimensions["dim_purchase_order"] = po_h
    for name, frame in dimensions.items():
        artifacts.append(write(frame, CORE, name))

    # Facts preserve transaction grain and enrich only with deterministic keys.
    fct_po = po_l.merge(
        po_h[["po_id", "order_date", "supplier_id", "warehouse_id", "buyer_id",
              "business_unit_id", "contract_id", "contract_valid_at_order_flag",
              "po_status", "currency"]],
        on="po_id", how="left", validate="many_to_one",
    )
    fct_po["order_date_key"] = fct_po["order_date"].dt.strftime("%Y%m%d").astype(int)
    artifacts.append(write(fct_po, CORE, "fct_purchase_order_line"))

    grn_agg = grn_l.groupby("po_line_id", as_index=False).agg(
        received_quantity=("received_quantity", "sum"),
        accepted_quantity=("accepted_quantity", "sum"),
        rejected_quantity=("rejected_quantity", "sum"),
        first_receipt_date=("receipt_date", "min"),
        final_receipt_date=("receipt_date", "max"),
        receipt_count=("grn_id", "nunique"),
    )
    fct_receipt = grn_l.merge(
        po_l[["po_line_id", "po_id", "ordered_quantity", "original_promised_date"]],
        on="po_line_id", how="left", validate="many_to_one",
    ).merge(po_h[["po_id", "supplier_id", "warehouse_id"]], on="po_id", how="left", validate="many_to_one")
    fct_receipt["receipt_date_key"] = fct_receipt["receipt_date"].dt.strftime("%Y%m%d").astype(int)
    artifacts.append(write(fct_receipt, CORE, "fct_goods_receipt_line"))

    fct_invoice = inv_l.merge(
        inv_h[["invoice_id", "supplier_id", "po_id", "invoice_date", "due_date", "invoice_status",
               "bank_detail_change_flag", "duplicate_of_invoice_id", "currency"]],
        on="invoice_id", how="left", validate="many_to_one",
    ).merge(
        po_l[["po_line_id", "unit_price", "ordered_quantity", "contract_item_id"]].rename(
            columns={"unit_price": "po_unit_price"}),
        on="po_line_id", how="left", validate="many_to_one",
    ).merge(
        po_h[["po_id", "business_unit_id", "warehouse_id", "buyer_id", "contract_id", "contract_valid_at_order_flag"]],
        on="po_id", how="left", validate="many_to_one",
    )
    fct_invoice["invoice_date_key"] = fct_invoice["invoice_date"].dt.strftime("%Y%m%d").astype(int)
    artifacts.append(write(fct_invoice, CORE, "fct_invoice_line"))
    artifacts.append(write(approvals, CORE, "fct_invoice_approval"))
    artifacts.append(write(payments, CORE, "fct_payment"))
    artifacts.append(write(quality, CORE, "fct_quality_inspection"))
    artifacts.append(write(incidents, CORE, "fct_supplier_incident"))

    # Invoice-grain three-way match. Receipt quantities are aggregated before
    # the join to prevent fan-out and financial overstatement.
    match_lines = inv_l.merge(
        po_l[["po_line_id", "unit_price", "ordered_quantity"]].rename(columns={"unit_price": "po_unit_price"}),
        on="po_line_id", how="left", validate="many_to_one",
    ).merge(grn_agg, on="po_line_id", how="left", validate="many_to_one")
    for column in ["received_quantity", "accepted_quantity", "rejected_quantity", "receipt_count"]:
        match_lines[column] = match_lines[column].fillna(0)
    match_lines["missing_po_reference_flag"] = match_lines["po_line_id"].isna() | match_lines["po_unit_price"].isna()
    match_lines["price_variance_amount"] = (match_lines["invoice_unit_price"] - match_lines["po_unit_price"]) * match_lines["invoiced_quantity"]
    match_lines["price_variance_pct"] = np.where(
        match_lines["po_unit_price"].gt(0),
        (match_lines["invoice_unit_price"] - match_lines["po_unit_price"]) / match_lines["po_unit_price"],
        np.nan,
    )
    match_lines["price_exception_flag"] = match_lines["price_variance_pct"].abs().gt(0.02)
    match_lines["quantity_exception_flag"] = match_lines["invoiced_quantity"].gt(match_lines["accepted_quantity"])
    match = match_lines.groupby("invoice_id", as_index=False).agg(
        invoiced_quantity=("invoiced_quantity", "sum"),
        accepted_quantity=("accepted_quantity", "sum"),
        line_net_amount=("line_net_amount", "sum"),
        price_variance_amount=("price_variance_amount", "sum"),
        missing_po_reference_flag=("missing_po_reference_flag", "max"),
        price_exception_flag=("price_exception_flag", "max"),
        quantity_exception_flag=("quantity_exception_flag", "max"),
    ).merge(
        inv_h[["invoice_id", "supplier_id", "po_id", "invoice_date", "due_date", "invoice_gross_amount",
               "invoice_status", "bank_detail_change_flag", "duplicate_of_invoice_id"]],
        on="invoice_id", how="left", validate="one_to_one",
    )
    match["probable_duplicate_flag"] = match["duplicate_of_invoice_id"].notna()
    flag_cols = ["missing_po_reference_flag", "price_exception_flag", "quantity_exception_flag",
                 "probable_duplicate_flag", "bank_detail_change_flag"]
    match["exception_count"] = match[flag_cols].astype(int).sum(axis=1)
    match["exception_status"] = np.where(match["exception_count"].gt(0), "Exception", "Matched")
    artifacts.append(write(match, MART, "invoice_three_way_match"))

    # PO-line service outcomes and supplier roll-up.
    service_lines = po_l[["po_line_id", "po_id", "ordered_quantity", "original_promised_date"]].merge(
        po_h[["po_id", "supplier_id", "po_status", "order_date"]], on="po_id", how="left", validate="many_to_one"
    ).merge(grn_agg, on="po_line_id", how="left", validate="one_to_one")
    for column in ["received_quantity", "accepted_quantity", "rejected_quantity", "receipt_count"]:
        service_lines[column] = service_lines[column].fillna(0)
    service_lines["days_late"] = (service_lines["final_receipt_date"] - service_lines["original_promised_date"]).dt.days
    eligible = service_lines[service_lines["po_status"].ne("Cancelled")].copy()
    eligible["on_time_flag"] = eligible["final_receipt_date"].notna() & eligible["days_late"].le(0)
    eligible["in_full_flag"] = eligible["accepted_quantity"].ge(eligible["ordered_quantity"])
    eligible["otif_flag"] = eligible["on_time_flag"] & eligible["in_full_flag"]
    eligible["rejection_rate"] = np.where(eligible["received_quantity"].gt(0), eligible["rejected_quantity"] / eligible["received_quantity"], 0)
    supplier_service = eligible.groupby("supplier_id", as_index=False).agg(
        eligible_po_lines=("po_line_id", "nunique"),
        on_time_rate=("on_time_flag", "mean"),
        in_full_rate=("in_full_flag", "mean"),
        otif_rate=("otif_flag", "mean"),
        average_days_late=("days_late", "mean"),
        rejection_rate=("rejection_rate", "mean"),
    ).merge(suppliers[["supplier_id", "supplier_name", "risk_tier"]], on="supplier_id", how="left", validate="one_to_one")
    artifacts.append(write(eligible, MART, "po_line_service_outcome"))
    artifacts.append(write(supplier_service, MART, "supplier_performance"))

    # Spend and contract compliance at month/category/supplier/BU grain.
    spend_lines = inv_l.merge(
        inv_h[["invoice_id", "invoice_date", "invoice_status", "supplier_id"]],
        on="invoice_id", how="left", validate="many_to_one",
    ).merge(
        po_l[["po_line_id", "po_id"]], on="po_line_id", how="left", validate="many_to_one",
    ).merge(
        po_h[["po_id", "business_unit_id", "contract_id", "contract_valid_at_order_flag"]],
        on="po_id", how="left", validate="many_to_one",
    ).merge(materials[["material_id", "category_id"]], on="material_id", how="left", validate="many_to_one")
    spend_lines = spend_lines[spend_lines["invoice_status"].eq("Posted")].copy()
    spend_lines["spend_month"] = spend_lines["invoice_date"].dt.to_period("M").astype(str)
    valid_contract = spend_lines["contract_valid_at_order_flag"].astype("boolean").fillna(False).to_numpy(dtype=bool)
    spend_lines["contracted_spend"] = np.where(valid_contract, spend_lines["line_net_amount"], 0.0)
    spend_lines["off_contract_spend"] = spend_lines["line_net_amount"] - spend_lines["contracted_spend"]
    spend = spend_lines.groupby(
        ["spend_month", "business_unit_id", "supplier_id", "category_id"], dropna=False, as_index=False
    ).agg(
        net_spend=("line_net_amount", "sum"),
        tax_amount=("line_tax_amount", "sum"),
        gross_spend=("line_gross_amount", "sum"),
        contracted_spend=("contracted_spend", "sum"),
        off_contract_spend=("off_contract_spend", "sum"),
        invoice_count=("invoice_id", "nunique"),
    )
    spend["off_contract_spend_pct"] = np.where(spend["net_spend"].ne(0), spend["off_contract_spend"] / spend["net_spend"], 0)
    artifacts.append(write(spend, MART, "spend_contract_compliance"))

    # Approval cycle and payment-timing marts.
    approvals = approvals.sort_values(["invoice_id", "event_timestamp", "approval_event_id"])
    approval = approvals.groupby("invoice_id", as_index=False).agg(
        submitted_at=("event_timestamp", "min"),
        completed_at=("event_timestamp", "max"),
        approval_event_count=("approval_event_id", "count"),
        final_approval_status=("approval_status", "last"),
    )
    approval["approval_cycle_hours"] = (approval["completed_at"] - approval["submitted_at"]).dt.total_seconds() / 3600
    approval = approval.merge(inv_h[["invoice_id", "supplier_id", "invoice_date", "invoice_gross_amount"]], on="invoice_id", how="left", validate="one_to_one")
    artifacts.append(write(approval, MART, "invoice_approval_cycle"))

    payment = payments.groupby("invoice_id", as_index=False).agg(
        payment_date=("payment_date", "max"),
        paid_amount=("payment_amount", "sum"),
        payment_count=("payment_id", "count"),
    ).merge(inv_h[["invoice_id", "supplier_id", "invoice_date", "due_date", "invoice_gross_amount", "invoice_status"]], on="invoice_id", how="right", validate="one_to_one")
    payment["days_to_pay"] = (payment["payment_date"] - payment["invoice_date"]).dt.days
    payment["days_vs_due"] = (payment["payment_date"] - payment["due_date"]).dt.days
    payment["payment_timing"] = np.select(
        [payment["payment_date"].isna(), payment["days_vs_due"].lt(0), payment["days_vs_due"].eq(0)],
        ["Unpaid", "Early", "On due date"], default="Late")
    payment["outstanding_amount"] = payment["invoice_gross_amount"] - payment["paid_amount"].fillna(0)
    artifacts.append(write(payment, MART, "payment_performance"))

    # Contract portfolio with deterministic as-of date (dataset cutoff).
    as_of = pd.Timestamp("2025-12-31")
    contract_portfolio = contracts.copy()
    contract_portfolio["days_to_expiry"] = (contract_portfolio["end_date"] - as_of).dt.days
    contract_portfolio["expiry_band"] = pd.cut(
        contract_portfolio["days_to_expiry"],
        bins=[-10**9, -1, 30, 60, 90, 180, 10**9],
        labels=["Expired", "0-30 days", "31-60 days", "61-90 days", "91-180 days", ">180 days"],
    ).astype(str)
    contract_portfolio = contract_portfolio.merge(suppliers[["supplier_id", "supplier_name", "risk_tier"]], on="supplier_id", how="left", validate="many_to_one")
    artifacts.append(write(contract_portfolio, MART, "contract_portfolio"))

    tests: list[dict] = []
    assert_test(tests, "Core", "PO fact row count", len(fct_po), len(po_l), len(fct_po) == len(po_l))
    assert_test(tests, "Core", "Invoice fact row count", len(fct_invoice), len(inv_l), len(fct_invoice) == len(inv_l))
    assert_test(tests, "Core", "Receipt fact row count", len(fct_receipt), len(grn_l), len(fct_receipt) == len(grn_l))
    assert_test(tests, "Core", "Invoice IDs unique in match mart", int(match["invoice_id"].duplicated().sum()), 0, not match["invoice_id"].duplicated().any())
    assert_test(tests, "Core", "All invoice headers represented", len(match), len(inv_h), len(match) == len(inv_h))
    assert_test(tests, "Finance", "Invoice fact net reconciles", round(float(fct_invoice["line_net_amount"].sum()), 2), round(float(inv_l["line_net_amount"].sum()), 2), abs(fct_invoice["line_net_amount"].sum() - inv_l["line_net_amount"].sum()) < 0.01)
    posted_source = spend_lines["line_net_amount"].sum()
    assert_test(tests, "Finance", "Spend mart reconciles to posted invoice lines", round(float(spend["net_spend"].sum()), 2), round(float(posted_source), 2), abs(spend["net_spend"].sum() - posted_source) < 0.01)
    assert_test(tests, "Finance", "Contract split reconciles", round(float((spend["contracted_spend"] + spend["off_contract_spend"] - spend["net_spend"]).abs().max()), 2), 0, (spend["contracted_spend"] + spend["off_contract_spend"] - spend["net_spend"]).abs().max() < 0.01)
    assert_test(tests, "Receiving", "Accepted plus rejected equals received", int((grn_l["accepted_quantity"] + grn_l["rejected_quantity"] - grn_l["received_quantity"]).abs().max()), 0, (grn_l["accepted_quantity"] + grn_l["rejected_quantity"] == grn_l["received_quantity"]).all())
    assert_test(tests, "Service", "OTIF bounded 0 to 1", f"{supplier_service.otif_rate.min():.4f}..{supplier_service.otif_rate.max():.4f}", "0..1", supplier_service.otif_rate.between(0, 1).all())
    assert_test(tests, "Workflow", "Approval mart covers invoices", len(approval), len(inv_h), len(approval) == len(inv_h))
    assert_test(tests, "Workflow", "Approval cycle non-negative", int((approval["approval_cycle_hours"] < 0).sum()), 0, approval["approval_cycle_hours"].ge(0).all())
    assert_test(tests, "Payments", "Paid amounts reconcile", round(float(payment["paid_amount"].fillna(0).sum()), 2), round(float(payments["payment_amount"].sum()), 2), abs(payment["paid_amount"].fillna(0).sum() - payments["payment_amount"].sum()) < 0.01)
    assert_test(tests, "Dimensions", "All suppliers represented", len(dimensions["dim_supplier"]), suppliers["supplier_id"].nunique(), len(dimensions["dim_supplier"]) == suppliers["supplier_id"].nunique())
    assert_test(tests, "Dimensions", "All materials represented", len(dimensions["dim_material"]), materials["material_id"].nunique(), len(dimensions["dim_material"]) == materials["material_id"].nunique())
    assert_test(tests, "Quality", "No orphan supplier in spend mart", int(spend["supplier_id"].isna().sum()), 0, spend["supplier_id"].notna().all())
    assert_test(tests, "Quality", "No negative gross spend", int((spend["gross_spend"] < 0).sum()), 0, spend["gross_spend"].ge(0).all())

    # Every injected anomaly must be observable by its corresponding
    # deterministic rule. Additional rule exceptions are legitimate and are
    # not treated as labelled anomalies or proven fraud.
    anomaly_truth = pd.read_csv(GROUND / "invoice_anomaly_ground_truth.csv")
    anomaly_map = {
        "MISSING_PO_REFERENCE": "missing_po_reference_flag",
        "PRICE_MISMATCH": "price_exception_flag",
        "QUANTITY_MISMATCH": "quantity_exception_flag",
        "PROBABLE_DUPLICATE": "probable_duplicate_flag",
        "BANK_DETAIL_CHANGE": "bank_detail_change_flag",
    }
    for anomaly_type, flag in anomaly_map.items():
        expected_ids = set(anomaly_truth.loc[anomaly_truth["anomaly_type"].eq(anomaly_type), "invoice_id"])
        detected_ids = set(match.loc[match[flag].astype(bool), "invoice_id"])
        missed = len(expected_ids - detected_ids)
        assert_test(tests, "Ground truth", f"Injected {anomaly_type} detected", missed, 0, missed == 0)

    test_frame = pd.DataFrame(tests)
    test_path = OUT / "release1_test_results.csv"
    test_frame.to_csv(test_path, index=False)
    failures = test_frame[test_frame["status"].eq("FAIL")]

    manifest_path = OUT / "artifact_manifest.json"
    manifest_path.write_text(json.dumps({
        "release": "Release 1 - Analytical Foundation",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_type": "deterministic synthetic FMCG procurement corpus",
        "artifacts": artifacts,
    }, indent=2), encoding="utf-8")

    summary = {
        "status": "PASS" if failures.empty else "FAIL",
        "tests": int(len(test_frame)),
        "passed": int((test_frame.status == "PASS").sum()),
        "failed": int((test_frame.status == "FAIL").sum()),
        "core_artifacts": len(list(CORE.glob("*.csv"))),
        "mart_artifacts": len(list(MART.glob("*.csv"))),
        "posted_net_spend": round(float(spend.net_spend.sum()), 2),
        "overall_otif_rate": round(float(eligible.otif_flag.mean()), 6),
        "invoice_exception_count": int(match.exception_status.eq("Exception").sum()),
    }
    (OUT / "release1_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# Release 1 Acceptance Report",
        "",
        f"Overall status: **{summary['status']}**",
        "",
        "This report covers the executable analytical reference build. PostgreSQL remains the production deployment target; the same grains and definitions are specified in `database/`.",
        "",
        "## Evidence",
        "",
        f"- {summary['core_artifacts']} conformed core outputs",
        f"- {summary['mart_artifacts']} analytical marts",
        f"- {summary['tests']} tests: {summary['passed']} passed, {summary['failed']} failed",
        f"- Posted net spend reconciled: INR {summary['posted_net_spend']:,.2f}",
        f"- Overall PO-line OTIF: {summary['overall_otif_rate']:.2%}",
        f"- Invoices with at least one deterministic exception: {summary['invoice_exception_count']:,}",
        "",
        "## Test results",
        "",
        "| Area | Test | Actual | Expected | Status |",
        "|---|---|---:|---:|---|",
    ]
    for row in tests:
        lines.append(f"| {row['area']} | {row['test']} | {row['actual']} | {row['expected']} | {row['status']} |")
    lines += [
        "",
        "## Claim boundary",
        "",
        "All records and measured results are synthetic. This release proves transformation correctness and reconciliation; it does not establish production business impact.",
    ]
    (OUT / "RELEASE1_ACCEPTANCE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if failures.empty else 1


if __name__ == "__main__":
    sys.exit(build())
