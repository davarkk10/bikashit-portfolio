from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import shutil
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
GT = ROOT / "data" / "ground_truth"
REF = ROOT / "data" / "reference"
DOCS = ROOT / "documents"
CONTRACT_DOCS = DOCS / "contracts"
INVOICE_DOCS = DOCS / "invoices"
QUOTE_DOCS = DOCS / "quotations"
POLICY_DOCS = DOCS / "policies"
VALIDATION = ROOT / "validation"
DOCUMENTATION = ROOT / "documentation"

SEED = 20260927
START = pd.Timestamp("2024-01-01")
END = pd.Timestamp("2025-12-31")
N_SUPPLIERS = 175
N_MATERIALS = 1800
N_CONTRACTS = 280
N_PO = 55000
N_PO_LINES = 220000
N_BASE_INVOICES = 47500
N_DUPLICATES = 500

rng = np.random.default_rng(SEED)
py_rng = random.Random(SEED)

FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
pdfmetrics.registerFont(TTFont("DV", FONT_REGULAR))
pdfmetrics.registerFont(TTFont("DV-Bold", FONT_BOLD))


def ensure_dirs():
    for p in [RAW, GT, REF, CONTRACT_DOCS, INVOICE_DOCS, QUOTE_DOCS, POLICY_DOCS, VALIDATION, DOCUMENTATION]:
        p.mkdir(parents=True, exist_ok=True)


def write_csv(df: pd.DataFrame, name: str):
    path = RAW / name
    df.to_csv(path, index=False, date_format="%Y-%m-%d %H:%M:%S")
    return path


def ids(prefix: str, n: int, width: int = 6):
    return [f"{prefix}{i:0{width}d}" for i in range(1, n + 1)]


def random_dates(n, start=START, end=END):
    span = (end - start).days
    return start + pd.to_timedelta(rng.integers(0, span + 1, n), unit="D")


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def money(x):
    return np.round(x.astype(float), 2)


def build_masters():
    categories = pd.DataFrame([
        ("CAT001", "Tea and beverages", "Direct material", 18, 0.04),
        ("CAT002", "Packaged foods", "Finished goods", 12, 0.03),
        ("CAT003", "Personal care", "Finished goods", 18, 0.02),
        ("CAT004", "Home care", "Finished goods", 18, 0.025),
        ("CAT005", "Packaging", "Direct material", 18, 0.05),
        ("CAT006", "Logistics", "Service", 18, 0.045),
        ("CAT007", "Warehousing", "Service", 18, 0.035),
        ("CAT008", "Marketing services", "Service", 18, 0.06),
        ("CAT009", "Office and indirect", "Indirect", 18, 0.025),
        ("CAT010", "Maintenance and utilities", "Indirect", 18, 0.04),
    ], columns=["category_id", "category_name", "category_group", "default_tax_rate_pct", "annual_inflation_rate"])

    warehouses = pd.DataFrame([
        ("WH001", "Guwahati DC", "Guwahati", "Assam", 26.1445, 91.7362, 22000),
        ("WH002", "Tinsukia DC", "Tinsukia", "Assam", 27.4922, 95.3468, 11000),
        ("WH003", "Dibrugarh DC", "Dibrugarh", "Assam", 27.4728, 94.9120, 12000),
        ("WH004", "Jorhat DC", "Jorhat", "Assam", 26.7509, 94.2037, 10000),
        ("WH005", "Silchar DC", "Silchar", "Assam", 24.8333, 92.7789, 9000),
        ("WH006", "Tezpur DC", "Tezpur", "Assam", 26.6528, 92.7926, 8000),
    ], columns=["warehouse_id", "warehouse_name", "city", "state", "latitude", "longitude", "capacity_pallets"])

    business_units = pd.DataFrame([
        ("BU001", "Private Label Beverages", "Direct"),
        ("BU002", "FMCG Distribution", "Trading"),
        ("BU003", "Operations and Logistics", "Service"),
        ("BU004", "Corporate Services", "Indirect"),
    ], columns=["business_unit_id", "business_unit_name", "spend_scope"])

    payment_terms = pd.DataFrame([
        ("PT001", "Immediate", 0, 0.0, 0),
        ("PT002", "Net 15", 15, 0.0, 0),
        ("PT003", "Net 30", 30, 0.0, 0),
        ("PT004", "Net 45", 45, 0.0, 0),
        ("PT005", "Net 60", 60, 0.0, 0),
        ("PT006", "2 percent 10 Net 30", 30, 2.0, 10),
    ], columns=["payment_term_id", "payment_term_name", "net_days", "discount_pct", "discount_days"])

    first = ["Aarav", "Ananya", "Arjun", "Bikram", "Deepa", "Ishita", "Kabir", "Manisha", "Neha", "Rohan", "Sanjay", "Tania"]
    last = ["Baruah", "Bora", "Das", "Dutta", "Gogoi", "Kalita", "Sarma", "Saikia", "Sharma", "Singh"]
    buyers = []
    for i, bid in enumerate(ids("BYR", 30, 3)):
        buyers.append((bid, f"{first[i % len(first)]} {last[(i * 3) % len(last)]}", categories.iloc[i % len(categories)].category_id, business_units.iloc[i % 4].business_unit_id, "Active"))
    buyers = pd.DataFrame(buyers, columns=["buyer_id", "buyer_name", "primary_category_id", "business_unit_id", "status"])

    supplier_cities = ["Guwahati", "Kolkata", "Siliguri", "Dibrugarh", "Jorhat", "Delhi", "Mumbai", "Bengaluru", "Hyderabad", "Ahmedabad", "Jaipur", "Chennai"]
    company_words = ["Evergreen", "Brahmaputra", "Eastern", "Pragati", "Horizon", "Unity", "Summit", "Riverine", "Pioneer", "Sterling", "Nexus", "NorthStar"]
    company_types = ["Foods", "Packaging", "Trading", "Logistics", "Industries", "Consumer Products", "Services", "Supplies"]
    suppliers = []
    for i, sid in enumerate(ids("SUP", N_SUPPLIERS, 4)):
        quality = float(np.clip(rng.beta(8, 2), 0.55, 0.99))
        reliability = float(np.clip(rng.beta(7, 2.4), 0.48, 0.99))
        risk = "High" if reliability < 0.68 or quality < 0.72 else "Medium" if reliability < 0.82 or quality < 0.85 else "Low"
        city = supplier_cities[i % len(supplier_cities)]
        suppliers.append((sid, f"{company_words[i % len(company_words)]} {company_types[(i * 5) % len(company_types)]} {i+1}", city, "India", categories.iloc[i % len(categories)].category_id, payment_terms.iloc[i % len(payment_terms)].payment_term_id, round(reliability, 4), round(quality, 4), risk, "Active"))
    suppliers = pd.DataFrame(suppliers, columns=["supplier_id", "supplier_name", "city", "country", "primary_category_id", "payment_term_id", "base_reliability", "base_quality_rate", "risk_tier", "status"])
    supplier_sites = suppliers[["supplier_id", "city", "country"]].copy()
    supplier_sites.insert(0, "supplier_site_id", ids("SITE", N_SUPPLIERS, 4))
    supplier_sites["state"] = np.where(supplier_sites.city.isin(["Guwahati", "Dibrugarh", "Jorhat"]), "Assam", "Other")
    supplier_sites["postal_code"] = [f"{700000 + (i * 137) % 99999:06d}" for i in range(N_SUPPLIERS)]

    adjectives = ["Classic", "Premium", "Fresh", "Daily", "Pure", "Select", "Value", "Natural", "Pro", "Essential"]
    nouns = ["Tea", "Beverage", "Snack", "Soap", "Cleaner", "Pouch", "Carton", "Bottle", "Transport", "Storage", "Campaign", "Supply"]
    materials = []
    products = []
    for i, mid in enumerate(ids("MAT", N_MATERIALS, 5)):
        cat = categories.iloc[i % len(categories)]
        base = round(float(rng.lognormal(mean=4.2 if cat.category_group != "Service" else 6.1, sigma=0.7)), 2)
        uom = "SERVICE" if cat.category_group == "Service" else ("KG" if cat.category_id in ["CAT001", "CAT005"] else "EA")
        active = "Active" if rng.random() > 0.015 else "Inactive"
        name = f"{adjectives[i % len(adjectives)]} {nouns[(i * 7) % len(nouns)]} {i+1}"
        materials.append((mid, name, cat.category_id, uom, base, cat.default_tax_rate_pct, active))
        if cat.category_group in ["Finished goods", "Direct material"]:
            products.append((f"SKU{i+1:05d}", mid, name, f"Brand {(i % 18)+1}", "Private Label" if i % 5 == 0 else "Distributed"))
    materials = pd.DataFrame(materials, columns=["material_id", "material_name", "category_id", "uom", "baseline_unit_price", "tax_rate_pct", "status"])
    products = pd.DataFrame(products, columns=["product_id", "material_id", "product_name", "brand", "ownership_type"])

    for name, df in {
        "categories.csv": categories, "warehouses.csv": warehouses, "business_units.csv": business_units,
        "payment_terms.csv": payment_terms, "buyers.csv": buyers, "suppliers.csv": suppliers,
        "supplier_sites.csv": supplier_sites, "materials.csv": materials, "products.csv": products,
    }.items():
        write_csv(df, name)
    return categories, warehouses, business_units, payment_terms, buyers, suppliers, materials


def build_contracts(suppliers, materials, payment_terms):
    contracts = []
    contract_items = []
    contract_events = []
    supplier_to_contracts = defaultdict(list)
    material_by_cat = {c: g.material_id.tolist() for c, g in materials.groupby("category_id")}
    for i, cid in enumerate(ids("CTR", N_CONTRACTS, 5)):
        sup = suppliers.iloc[i % len(suppliers)]
        start = pd.Timestamp("2023-07-01") + pd.to_timedelta(int(rng.integers(0, 550)), unit="D")
        term_months = int(rng.choice([12, 18, 24, 30], p=[0.25, 0.25, 0.4, 0.1]))
        end = start + pd.DateOffset(months=term_months) - pd.Timedelta(days=1)
        status = "Active" if end >= END else "Expired"
        pt = payment_terms.iloc[int(rng.integers(0, len(payment_terms)))]
        escalation = round(float(rng.choice([0, 3, 5, 7, 9])), 1)
        termination = int(rng.choice([30, 45, 60, 90]))
        auto_renew = bool(rng.random() < 0.35)
        governing = rng.choice(["Assam", "West Bengal", "Delhi", "Maharashtra"])
        value = round(float(rng.lognormal(16.2, 0.75)), 2)
        contracts.append((cid, sup.supplier_id, f"FMCG Supply Agreement {cid}", "Supply" if i % 5 else "Service", start.date(), end.date(), status, value, pt.payment_term_id, escalation, termination, auto_renew, governing, f"documents/contracts/{cid}.pdf"))
        supplier_to_contracts[sup.supplier_id].append(cid)
        eligible = material_by_cat[sup.primary_category_id]
        chosen = rng.choice(eligible, size=min(len(eligible), int(rng.integers(18, 55))), replace=False)
        for j, mid in enumerate(chosen, 1):
            base = float(materials.loc[materials.material_id == mid, "baseline_unit_price"].iloc[0])
            contracted = round(base * float(rng.uniform(0.91, 1.04)), 2)
            contract_items.append((f"CTI{len(contract_items)+1:07d}", cid, mid, contracted, int(rng.integers(50, 5000)), round(float(rng.choice([1.0, 2.0, 3.0])), 1)))
        contract_events.append((f"CEV{len(contract_events)+1:06d}", cid, start.date(), "Created", "Initial contract execution"))
        if rng.random() < 0.35:
            d = min(end, start + pd.to_timedelta(int(rng.integers(90, max(91, (end-start).days))), unit="D"))
            contract_events.append((f"CEV{len(contract_events)+1:06d}", cid, d.date(), "Amendment", "Commercial term amendment"))
    contracts = pd.DataFrame(contracts, columns=["contract_id", "supplier_id", "contract_title", "contract_type", "start_date", "end_date", "contract_status", "contract_value", "payment_term_id", "price_escalation_cap_pct", "termination_notice_days", "auto_renewal_flag", "governing_law_state", "document_path"])
    contract_items = pd.DataFrame(contract_items, columns=["contract_item_id", "contract_id", "material_id", "contract_unit_price", "minimum_order_qty", "price_tolerance_pct"])
    contract_events = pd.DataFrame(contract_events, columns=["contract_event_id", "contract_id", "event_date", "event_type", "event_description"])
    write_csv(contracts, "contracts.csv")
    write_csv(contract_items, "contract_items.csv")
    write_csv(contract_events, "contract_events.csv")
    return contracts, contract_items, contract_events, supplier_to_contracts


def build_quotes(suppliers, materials):
    rows = []
    for i in range(24000):
        sup = suppliers.iloc[int(rng.integers(0, len(suppliers)))]
        eligible = materials[materials.category_id == sup.primary_category_id]
        mat = eligible.iloc[int(rng.integers(0, len(eligible)))]
        qdate = random_dates(1)[0]
        price = round(mat.baseline_unit_price * float(rng.uniform(0.88, 1.18)) * (1 + 0.03 * (qdate.year - 2024)), 2)
        rows.append((f"QTL{i+1:07d}", f"RFQ{(i//3)+1:06d}", sup.supplier_id, mat.material_id, qdate.date(), (qdate + pd.Timedelta(days=30)).date(), int(rng.integers(20, 5000)), price, int(rng.integers(3, 28)), "Selected" if i % 3 == 0 else "Not selected"))
    df = pd.DataFrame(rows, columns=["quote_line_id", "rfq_id", "supplier_id", "material_id", "quote_date", "valid_until", "quoted_quantity", "quoted_unit_price", "quoted_lead_time_days", "selection_status"])
    write_csv(df, "supplier_quotes.csv")
    return df


def allocate_line_counts(n_headers, n_lines):
    counts = np.full(n_headers, 2, dtype=int)
    remaining = n_lines - counts.sum()
    for _ in range(remaining):
        counts[int(rng.integers(0, n_headers))] += 1
    return counts


def build_purchase_orders(suppliers, warehouses, buyers, materials, contracts, contract_items, supplier_to_contracts):
    po_ids = ids("PO", N_PO, 7)
    order_dates = pd.Series(random_dates(N_PO)).sort_values().reset_index(drop=True)
    supplier_weights = np.linspace(2.8, 0.5, N_SUPPLIERS); supplier_weights /= supplier_weights.sum()
    supplier_idxs = rng.choice(N_SUPPLIERS, size=N_PO, p=supplier_weights)
    headers = []
    line_counts = allocate_line_counts(N_PO, N_PO_LINES)
    lines = []
    po_line_id_num = 1
    valid_contract_items = defaultdict(list)
    for row in contract_items.itertuples(index=False):
        valid_contract_items[row.contract_id].append(row)

    for i, po_id in enumerate(po_ids):
        sup = suppliers.iloc[supplier_idxs[i]]
        od = order_dates.iloc[i]
        lead_base = int(np.clip(rng.normal(12 + (1 - sup.base_reliability) * 22, 4), 3, 45))
        promised = od + pd.Timedelta(days=lead_base)
        wh = warehouses.iloc[int(rng.integers(0, len(warehouses)))]
        buyer_pool = buyers[buyers.primary_category_id == sup.primary_category_id]
        buyer = buyer_pool.iloc[int(rng.integers(0, len(buyer_pool)))] if len(buyer_pool) else buyers.iloc[int(rng.integers(0, len(buyers)))]
        cid = None
        contract_valid = False
        possible = supplier_to_contracts.get(sup.supplier_id, [])
        if possible and rng.random() < 0.72:
            valid = contracts[(contracts.contract_id.isin(possible)) & (pd.to_datetime(contracts.start_date) <= od) & (pd.to_datetime(contracts.end_date) >= od)]
            if len(valid):
                cid = valid.iloc[int(rng.integers(0, len(valid)))].contract_id
                contract_valid = True
        if cid is None and possible and rng.random() < 0.07:
            cid = py_rng.choice(possible)
        status = "Cancelled" if rng.random() < 0.012 else "Closed"
        headers.append((po_id, od.date(), sup.supplier_id, wh.warehouse_id, buyer.buyer_id, buyer.business_unit_id, cid, contract_valid, promised.date(), status, "INR", "ERP"))

        if cid and valid_contract_items[cid]:
            pool = valid_contract_items[cid]
            selected = [pool[int(rng.integers(0, len(pool)))] for _ in range(line_counts[i])]
        else:
            eligible = materials[materials.category_id == sup.primary_category_id]
            selected = [eligible.iloc[int(rng.integers(0, len(eligible)))] for _ in range(line_counts[i])]
        for line_no, x in enumerate(selected, 1):
            mid = x.material_id
            mat = materials.loc[materials.material_id == mid].iloc[0]
            qty = int(rng.integers(10, 1500 if mat.uom != "SERVICE" else 40))
            if hasattr(x, "contract_unit_price"):
                unit = float(x.contract_unit_price)
                contract_item_id = x.contract_item_id
            else:
                unit = float(mat.baseline_unit_price) * float(rng.uniform(0.92, 1.18))
                contract_item_id = None
            unit *= 1 + float(mat.category_id[-1] != "0") * 0.025 * (od.year - 2024)
            unit = round(unit, 2)
            net = round(qty * unit, 2)
            tax = round(net * float(mat.tax_rate_pct) / 100, 2)
            gross = round(net + tax, 2)
            lines.append((f"POL{po_line_id_num:08d}", po_id, line_no, mid, contract_item_id, qty, mat.uom, unit, float(mat.tax_rate_pct), net, tax, gross, promised.date()))
            po_line_id_num += 1
    headers = pd.DataFrame(headers, columns=["po_id", "order_date", "supplier_id", "warehouse_id", "buyer_id", "business_unit_id", "contract_id", "contract_valid_at_order_flag", "promised_delivery_date", "po_status", "currency", "source_system"])
    lines = pd.DataFrame(lines, columns=["po_line_id", "po_id", "line_number", "material_id", "contract_item_id", "ordered_quantity", "uom", "unit_price", "tax_rate_pct", "line_net_amount", "line_tax_amount", "line_gross_amount", "original_promised_date"])
    write_csv(headers, "purchase_order_headers.csv")
    write_csv(lines, "purchase_order_lines.csv")
    return headers, lines


def build_receipts_and_quality(po_headers, po_lines, suppliers, materials):
    sup_rel = suppliers.set_index("supplier_id").base_reliability.to_dict()
    header_map = po_headers.set_index("po_id")
    receipt_headers = []
    receipt_lines = []
    inspections = []
    incidents = []
    gt_delays = []
    for i, (po_id, grp) in enumerate(po_lines.groupby("po_id", sort=False), 1):
        ph = header_map.loc[po_id]
        promised = pd.Timestamp(ph.promised_delivery_date)
        reliability = sup_rel[ph.supplier_id]
        seasonal = 0.12 if promised.month in [4, 10, 11, 12] else 0
        late_prob = min(0.62, (1 - reliability) * 1.5 + seasonal)
        late = bool(rng.random() < late_prob)
        variance_days = int(rng.integers(1, 18)) if late else -int(rng.integers(0, 5))
        receipt_date = promised + pd.Timedelta(days=variance_days)
        receipt_date = min(receipt_date, END + pd.Timedelta(days=45))
        grn_id = f"GRN{i:07d}"
        receipt_headers.append((grn_id, po_id, receipt_date.date(), ph.warehouse_id, ph.supplier_id, "Posted" if ph.po_status != "Cancelled" else "Cancelled"))
        if late:
            gt_delays.append((po_id, grn_id, ph.supplier_id, promised.date(), receipt_date.date(), variance_days, "Seasonal or reliability-driven delay"))
        for j, row in enumerate(grp.itertuples(index=False), 1):
            if ph.po_status == "Cancelled":
                received = accepted = rejected = 0
            else:
                short = rng.random() < 0.075
                received = int(row.ordered_quantity * float(rng.uniform(0.72, 0.98))) if short else int(row.ordered_quantity)
                reject_rate = float(rng.uniform(0.01, 0.08)) if rng.random() < 0.045 else 0.0
                rejected = int(round(received * reject_rate))
                accepted = max(0, received - rejected)
            grn_line_id = f"GRL{len(receipt_lines)+1:08d}"
            receipt_lines.append((grn_line_id, grn_id, row.po_line_id, row.material_id, received, accepted, rejected, row.uom, receipt_date.date(), "Accepted" if rejected == 0 else "Partially rejected"))
            if rng.random() < 0.42 and received > 0:
                result = "Fail" if rejected > 0 else "Pass"
                inspections.append((f"QIN{len(inspections)+1:08d}", grn_line_id, receipt_date.date(), int(min(received, rng.integers(1, max(2, received + 1)))), rejected, result, "Packaging damage" if result == "Fail" else "Within specification"))
                if result == "Fail":
                    incidents.append((f"INC{len(incidents)+1:06d}", ph.supplier_id, po_id, receipt_date.date(), "Quality", "Medium" if rejected < received * 0.05 else "High", "Open" if rng.random() < 0.2 else "Closed"))
    receipt_headers = pd.DataFrame(receipt_headers, columns=["grn_id", "po_id", "receipt_date", "warehouse_id", "supplier_id", "grn_status"])
    receipt_lines = pd.DataFrame(receipt_lines, columns=["grn_line_id", "grn_id", "po_line_id", "material_id", "received_quantity", "accepted_quantity", "rejected_quantity", "uom", "receipt_date", "receipt_disposition"])
    inspections = pd.DataFrame(inspections, columns=["inspection_id", "grn_line_id", "inspection_date", "sample_quantity", "rejected_quantity", "inspection_result", "reason"])
    # Add service and commercial incidents.
    for _ in range(1800):
        ph = po_headers.iloc[int(rng.integers(0, len(po_headers)))]
        incidents.append((f"INC{len(incidents)+1:06d}", ph.supplier_id, ph.po_id, ph.order_date, rng.choice(["Service", "Commercial", "Compliance"]), rng.choice(["Low", "Medium", "High"], p=[0.5, 0.38, 0.12]), rng.choice(["Open", "Closed"], p=[0.18, 0.82])))
    incidents = pd.DataFrame(incidents, columns=["incident_id", "supplier_id", "po_id", "incident_date", "incident_type", "severity", "incident_status"])
    write_csv(receipt_headers, "goods_receipt_headers.csv")
    write_csv(receipt_lines, "goods_receipt_lines.csv")
    write_csv(inspections, "quality_inspections.csv")
    write_csv(incidents, "supplier_incidents.csv")
    pd.DataFrame(gt_delays, columns=["po_id", "grn_id", "supplier_id", "promised_date", "receipt_date", "delay_days", "injection_reason"]).to_csv(GT / "supplier_delay_ground_truth.csv", index=False)
    return receipt_headers, receipt_lines, inspections, incidents


def build_invoices(po_headers, po_lines, receipt_headers, receipt_lines, suppliers, payment_terms):
    eligible_po = po_headers[po_headers.po_status != "Cancelled"].sample(n=N_BASE_INVOICES, random_state=SEED).sort_values("order_date")
    po_groups = {k: v for k, v in po_lines.groupby("po_id", sort=False)}
    receipt_date_map = receipt_headers.set_index("po_id").receipt_date.to_dict()
    sup_terms = suppliers.set_index("supplier_id").payment_term_id.to_dict()
    term_days = payment_terms.set_index("payment_term_id").net_days.to_dict()
    headers = []
    lines = []
    anomaly_rows = []
    invoice_to_lines = defaultdict(list)
    for i, ph in enumerate(eligible_po.itertuples(index=False), 1):
        inv_id = f"INV{i:07d}"
        invoice_date = pd.Timestamp(receipt_date_map[ph.po_id]) + pd.Timedelta(days=int(rng.integers(0, 8)))
        due_date = invoice_date + pd.Timedelta(days=int(term_days[sup_terms[ph.supplier_id]]))
        anomaly = None
        rv = rng.random()
        if rv < 0.025: anomaly = "PRICE_MISMATCH"
        elif rv < 0.045: anomaly = "QUANTITY_MISMATCH"
        elif rv < 0.058: anomaly = "BANK_DETAIL_CHANGE"
        elif rv < 0.068: anomaly = "MISSING_PO_REFERENCE"
        bank_change = anomaly == "BANK_DETAIL_CHANGE"
        gross_total = 0.0; net_total = 0.0; tax_total = 0.0
        grp = po_groups[ph.po_id]
        for line_no, pol in enumerate(grp.itertuples(index=False), 1):
            invoiced_qty = pol.ordered_quantity
            unit = pol.unit_price
            if anomaly == "PRICE_MISMATCH" and line_no == 1:
                unit = round(unit * float(rng.uniform(1.08, 1.25)), 2)
            if anomaly == "QUANTITY_MISMATCH" and line_no == 1:
                invoiced_qty = int(math.ceil(invoiced_qty * float(rng.uniform(1.05, 1.18))))
            net = round(invoiced_qty * unit, 2)
            tax = round(net * pol.tax_rate_pct / 100, 2)
            gross = round(net + tax, 2)
            line_id = f"INL{len(lines)+1:08d}"
            row = (line_id, inv_id, line_no, pol.po_line_id if anomaly != "MISSING_PO_REFERENCE" else None, pol.material_id, invoiced_qty, pol.uom, unit, pol.tax_rate_pct, net, tax, gross)
            lines.append(row); invoice_to_lines[inv_id].append(row)
            net_total += net; tax_total += tax; gross_total += gross
        supplier_invoice_number = f"{ph.supplier_id[-4:]}/{invoice_date.year}/{i:06d}"
        headers.append((inv_id, supplier_invoice_number, ph.supplier_id, ph.po_id if anomaly != "MISSING_PO_REFERENCE" else None, invoice_date.date(), due_date.date(), round(net_total, 2), round(tax_total, 2), round(gross_total, 2), "INR", "Posted", bank_change, None, f"documents/invoices/{inv_id}.pdf" if i <= 80 else None))
        if anomaly:
            anomaly_rows.append((inv_id, anomaly, "High" if anomaly in ["BANK_DETAIL_CHANGE", "MISSING_PO_REFERENCE"] else "Medium", ph.po_id, "Synthetic injected condition"))

    # Add true duplicate-like invoices with copied lines and supplier invoice number.
    base_df = pd.DataFrame(headers, columns=["invoice_id", "supplier_invoice_number", "supplier_id", "po_id", "invoice_date", "due_date", "invoice_net_amount", "invoice_tax_amount", "invoice_gross_amount", "currency", "invoice_status", "bank_detail_change_flag", "duplicate_of_invoice_id", "document_path"])
    dup_sources = base_df.sample(n=N_DUPLICATES, random_state=SEED + 4).reset_index(drop=True)
    for j, src in dup_sources.iterrows():
        inv_id = f"INV{N_BASE_INVOICES+j+1:07d}"
        inv_date = pd.Timestamp(src.invoice_date) + pd.Timedelta(days=int(rng.integers(1, 6)))
        headers.append((inv_id, src.supplier_invoice_number, src.supplier_id, src.po_id, inv_date.date(), src.due_date, src.invoice_net_amount, src.invoice_tax_amount, src.invoice_gross_amount, "INR", "Posted", False, src.invoice_id, None))
        for old in invoice_to_lines[src.invoice_id]:
            row = (f"INL{len(lines)+1:08d}", inv_id, old[2], old[3], old[4], old[5], old[6], old[7], old[8], old[9], old[10], old[11])
            lines.append(row)
        anomaly_rows.append((inv_id, "PROBABLE_DUPLICATE", "High", src.po_id, f"Copies {src.invoice_id}"))

    headers = pd.DataFrame(headers, columns=base_df.columns)
    lines = pd.DataFrame(lines, columns=["invoice_line_id", "invoice_id", "line_number", "po_line_id", "material_id", "invoiced_quantity", "uom", "invoice_unit_price", "tax_rate_pct", "line_net_amount", "line_tax_amount", "line_gross_amount"])
    write_csv(headers, "invoice_headers.csv")
    write_csv(lines, "invoice_lines.csv")
    pd.DataFrame(anomaly_rows, columns=["invoice_id", "anomaly_type", "severity", "related_po_id", "injection_reason"]).to_csv(GT / "invoice_anomaly_ground_truth.csv", index=False)

    # Approval events: submitted, reviewed and final decision, with controlled bottlenecks.
    approvals = []
    anomaly_ids = set(x[0] for x in anomaly_rows)
    for h in headers.itertuples(index=False):
        start = pd.Timestamp(h.invoice_date) + pd.Timedelta(hours=int(rng.integers(8, 30)))
        delay_hours = int(rng.integers(4, 60)) + (96 if rng.random() < 0.07 else 0)
        decision = "Request information" if h.invoice_id in anomaly_ids and rng.random() < 0.65 else "Approved"
        approvals.extend([
            (f"APR{len(approvals)+1:09d}", h.invoice_id, start, "Submitted", "AP Intake", "Invoice submitted"),
            (f"APR{len(approvals)+2:09d}", h.invoice_id, start + pd.Timedelta(hours=delay_hours//2), "In review", "AP Analyst", "Three-way match review"),
            (f"APR{len(approvals)+3:09d}", h.invoice_id, start + pd.Timedelta(hours=delay_hours), decision, "Procurement Approver", "Evidence reviewed"),
        ])
    approvals = pd.DataFrame(approvals, columns=["approval_event_id", "invoice_id", "event_timestamp", "approval_status", "actor_role", "decision_comment"])
    write_csv(approvals, "invoice_approvals.csv")

    payments = []
    final_approval = approvals[approvals.approval_status == "Approved"].set_index("invoice_id").event_timestamp.to_dict()
    for h in headers.itertuples(index=False):
        if h.invoice_id not in final_approval or rng.random() < 0.035:
            continue
        pay_date = pd.Timestamp(final_approval[h.invoice_id]) + pd.Timedelta(days=int(rng.integers(1, 20)))
        payments.append((f"PAY{len(payments)+1:07d}", h.invoice_id, pay_date.date(), h.invoice_gross_amount, "Bank transfer", "Paid"))
    payments = pd.DataFrame(payments, columns=["payment_id", "invoice_id", "payment_date", "payment_amount", "payment_method", "payment_status"])
    write_csv(payments, "payments.csv")
    return headers, lines, approvals, payments


def draw_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("DV", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(18 * mm, 12 * mm, "Synthetic portfolio document")
    canvas.drawRightString(198 * mm, 12 * mm, f"Page {doc.page}")
    canvas.restoreState()


def pdf_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="DocTitle2", parent=styles["Title"], fontName="DV-Bold", fontSize=18, leading=22, textColor=colors.black, alignment=TA_LEFT, spaceAfter=14))
    styles.add(ParagraphStyle(name="H2x", parent=styles["Heading2"], fontName="DV-Bold", fontSize=11, leading=14, textColor=colors.black, spaceBefore=8, spaceAfter=5))
    styles.add(ParagraphStyle(name="Bodyx", parent=styles["BodyText"], fontName="DV", fontSize=9, leading=12, textColor=colors.black, spaceAfter=6))
    return styles


def build_contract_pdf(row, supplier_name):
    path = CONTRACT_DOCS / f"{row.contract_id}.pdf"
    styles = pdf_styles()
    doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=18*mm, leftMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
    clauses = [
        ("1 Parties and scope", f"This synthetic agreement is between NorthEast Consumer Products Pvt. Ltd. and {supplier_name}. It covers approved FMCG goods or services under contract {row.contract_id}."),
        ("2 Term", f"The agreement starts on {row.start_date} and ends on {row.end_date}. Auto renewal is {'enabled' if row.auto_renewal_flag else 'not enabled'}."),
        ("3 Commercial value", f"The indicative contract value is INR {row.contract_value:,.2f}. Approved purchase orders remain the controlling commitment documents."),
        ("4 Price adjustment", f"Annual price escalation must not exceed {row.price_escalation_cap_pct:.1f} percent without a signed amendment."),
        ("5 Delivery and service", "The supplier must meet original purchase-order promise dates and deliver accepted quantity in full. Exceptions require documented buyer approval."),
        ("6 Quality", "Goods may be inspected at receipt. Rejected quantities do not count as accepted supply and may be replaced or credited after review."),
        ("7 Invoicing", "Invoices must reference the purchase order and applicable receipt. Price and quantity differences outside approved tolerance require investigation."),
        ("8 Payment", f"Payment follows term {row.payment_term_id} after complete evidence and approval. No payment is due solely because an automated recommendation exists."),
        ("9 Termination", f"Either party may terminate with {row.termination_notice_days} days written notice, subject to open obligations."),
        ("10 Governing law", f"This synthetic agreement uses {row.governing_law_state} as the illustrative governing-law state."),
        ("11 Data and audit", "Transactions, approvals and evidence must remain auditable. Automated systems may recommend actions but cannot modify this agreement."),
        ("12 Synthetic-use notice", "This document is fictional and was generated solely for an analytics portfolio proof of concept."),
    ]
    story = [Paragraph(row.contract_title, styles["DocTitle2"]), Paragraph(f"Contract ID {row.contract_id}", styles["Bodyx"]), Spacer(1, 6)]
    for h, b in clauses:
        story.extend([Paragraph(h, styles["H2x"]), Paragraph(b, styles["Bodyx"])])
    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)


def build_invoice_pdf(h, line_df, supplier_name):
    path = INVOICE_DOCS / f"{h.invoice_id}.pdf"
    styles = pdf_styles()
    doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=16*mm, leftMargin=16*mm, topMargin=16*mm, bottomMargin=18*mm)
    story = [Paragraph("Supplier Invoice", styles["DocTitle2"]), Paragraph(f"Invoice ID {h.invoice_id}  |  Supplier reference {h.supplier_invoice_number}", styles["Bodyx"]), Paragraph(f"Supplier {supplier_name}  |  Invoice date {h.invoice_date}  |  Due date {h.due_date}", styles["Bodyx"]), Paragraph(f"Purchase order {h.po_id or 'Not supplied'}", styles["Bodyx"]), Spacer(1, 8)]
    data = [["Line", "Material", "Quantity", "Unit price", "Net", "Tax", "Gross"]]
    for x in line_df.itertuples(index=False):
        data.append([x.line_number, x.material_id, f"{x.invoiced_quantity:,.0f}", f"{x.invoice_unit_price:,.2f}", f"{x.line_net_amount:,.2f}", f"{x.line_tax_amount:,.2f}", f"{x.line_gross_amount:,.2f}"])
    t = Table(data, colWidths=[12*mm, 24*mm, 22*mm, 24*mm, 25*mm, 23*mm, 25*mm], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#17365D")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("FONTNAME", (0,0), (-1,0), "DV-Bold"), ("FONTNAME", (0,1), (-1,-1), "DV"), ("FONTSIZE", (0,0), (-1,-1), 7.5), ("ALIGN", (2,1), (-1,-1), "RIGHT"), ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#D9D9D9")), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F3F6F9")]), ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5)]))
    story.extend([t, Spacer(1, 10), Paragraph(f"Net INR {h.invoice_net_amount:,.2f}  |  Tax INR {h.invoice_tax_amount:,.2f}  |  Gross INR {h.invoice_gross_amount:,.2f}", styles["H2x"]), Paragraph("Synthetic document for portfolio testing. Bank and tax identifiers are intentionally omitted.", styles["Bodyx"])])
    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)


def build_quote_pdf(group, supplier_name, quote_no):
    path = QUOTE_DOCS / f"QUOTE{quote_no:04d}.pdf"
    styles = pdf_styles()
    doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=18*mm, leftMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
    story = [Paragraph("Supplier Quotation", styles["DocTitle2"]), Paragraph(f"Supplier {supplier_name}  |  RFQ {group.iloc[0].rfq_id}  |  Date {group.iloc[0].quote_date}", styles["Bodyx"]), Spacer(1, 8)]
    data = [["Material", "Quantity", "Unit price", "Lead days", "Valid until"]]
    for x in group.head(12).itertuples(index=False):
        data.append([x.material_id, f"{x.quoted_quantity:,.0f}", f"{x.quoted_unit_price:,.2f}", x.quoted_lead_time_days, str(x.valid_until)])
    t = Table(data, colWidths=[32*mm, 28*mm, 30*mm, 25*mm, 35*mm], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#17365D")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("FONTNAME", (0,0), (-1,0), "DV-Bold"), ("FONTNAME", (0,1), (-1,-1), "DV"), ("FONTSIZE", (0,0), (-1,-1), 8), ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#D9D9D9")), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F3F6F9")]), ("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5)]))
    story.extend([t, Spacer(1, 10), Paragraph("This quotation is synthetic and does not create a commercial commitment.", styles["Bodyx"])])
    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)


def build_policy_pdfs():
    styles = pdf_styles()
    policies = {
        "procurement_policy.pdf": [
            ("1 Purpose", "Define controlled sourcing, purchase-order, contract and approval practices for the synthetic company."),
            ("2 Competition", "Purchases above INR 500,000 normally require at least three comparable quotations unless a documented exception is approved."),
            ("3 Contract use", "Buyers should use a valid contract when one covers the supplier, material and purchase date."),
            ("4 Human approval", "No AI recommendation can create a binding purchase, supplier change, contract change or payment release."),
            ("5 Evidence", "Approvers must receive the transaction facts, relevant contract evidence, reason codes and financial exposure."),
        ],
        "invoice_approval_policy.pdf": [
            ("1 Three-way match", "Invoices must be compared with purchase orders and accepted goods receipts."),
            ("2 Tolerances", "Price differences above two percent or quantity differences above zero require documented review unless a contract states another tolerance."),
            ("3 Duplicate risk", "Repeated supplier invoice numbers or materially identical invoices must be held for investigation."),
            ("4 Escalation", "Invoices above INR 1,000,000 or with bank-detail changes require senior approval."),
            ("5 Audit", "Submission, review, decision and comments must be retained as separate timestamped events."),
        ],
    }
    for filename, clauses in policies.items():
        path = POLICY_DOCS / filename
        doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=18*mm, leftMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
        story = [Paragraph(filename.replace("_", " ").replace(".pdf", "").title(), styles["DocTitle2"])]
        for h, b in clauses:
            story.extend([Paragraph(h, styles["H2x"]), Paragraph(b, styles["Bodyx"])])
        story.append(Paragraph("Synthetic policy for portfolio testing.", styles["Bodyx"]))
        doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)


def build_documents(contracts, suppliers, invoice_headers, invoice_lines, quotes):
    sup_names = suppliers.set_index("supplier_id").supplier_name.to_dict()
    for row in contracts.itertuples(index=False):
        build_contract_pdf(row, sup_names[row.supplier_id])
    inv_line_groups = {k: v for k, v in invoice_lines.groupby("invoice_id")}
    for h in invoice_headers[invoice_headers.document_path.notna()].head(80).itertuples(index=False):
        build_invoice_pdf(h, inv_line_groups[h.invoice_id], sup_names[h.supplier_id])
    qgroups = list(quotes.groupby(["supplier_id", "rfq_id"], sort=False))[:40]
    for i, (_, grp) in enumerate(qgroups, 1):
        build_quote_pdf(grp, sup_names[grp.iloc[0].supplier_id], i)
    build_policy_pdfs()


def create_reference_files():
    holidays = pd.DataFrame([
        ("2024-01-26", "Republic Day"), ("2024-04-14", "Rongali Bihu"), ("2024-10-12", "Durga Puja"), ("2024-11-01", "Diwali"),
        ("2025-01-26", "Republic Day"), ("2025-04-14", "Rongali Bihu"), ("2025-10-02", "Durga Puja"), ("2025-10-21", "Diwali"),
    ], columns=["holiday_date", "holiday_name"])
    holidays.to_csv(REF / "illustrative_holiday_calendar.csv", index=False)
    (REF / "README.md").write_text("Reference files are illustrative and remain separate from synthetic operational transactions. Verify official calendars before real use.\n", encoding="utf-8")


def create_manifest_and_summary():
    records = []
    for path in sorted([p for p in ROOT.rglob("*") if p.is_file() and "qa" not in p.parts and "release" not in p.parts]):
        rel = path.relative_to(ROOT).as_posix()
        rows = None; cols = None
        if path.suffix.lower() == ".csv":
            try:
                df = pd.read_csv(path)
                rows, cols = len(df), len(df.columns)
            except Exception:
                pass
        records.append((rel, path.stat().st_size, sha256(path), rows, cols))
    manifest = pd.DataFrame(records, columns=["relative_path", "size_bytes", "sha256", "row_count", "column_count"])
    manifest.to_csv(DOCUMENTATION / "file_manifest.csv", index=False)
    summary = {
        "project": "ProcureAI FMCG Procurement Spend and Contract Intelligence Platform",
        "dataset_type": "Deterministic synthetic portfolio proof of concept",
        "seed": SEED,
        "period": [str(START.date()), str(END.date())],
        "generated_at_utc": "2026-09-27T00:00:00Z",
        "file_count_before_manifest": len(records),
    }
    (DOCUMENTATION / "generation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main():
    ensure_dirs()
    categories, warehouses, business_units, payment_terms, buyers, suppliers, materials = build_masters()
    contracts, contract_items, contract_events, supplier_to_contracts = build_contracts(suppliers, materials, payment_terms)
    quotes = build_quotes(suppliers, materials)
    po_headers, po_lines = build_purchase_orders(suppliers, warehouses, buyers, materials, contracts, contract_items, supplier_to_contracts)
    receipt_headers, receipt_lines, inspections, incidents = build_receipts_and_quality(po_headers, po_lines, suppliers, materials)
    invoice_headers, invoice_lines, approvals, payments = build_invoices(po_headers, po_lines, receipt_headers, receipt_lines, suppliers, payment_terms)
    build_documents(contracts, suppliers, invoice_headers, invoice_lines, quotes)
    create_reference_files()
    create_manifest_and_summary()
    print(json.dumps({
        "suppliers": len(suppliers), "materials": len(materials), "contracts": len(contracts),
        "purchase_orders": len(po_headers), "purchase_order_lines": len(po_lines),
        "invoices": len(invoice_headers), "invoice_lines": len(invoice_lines),
        "approval_events": len(approvals), "payments": len(payments),
        "pdfs": len(list(DOCS.rglob("*.pdf")))
    }, indent=2))


if __name__ == "__main__":
    main()
