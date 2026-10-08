from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
MART = ROOT / "artifacts" / "release1" / "marts"
RAW = ROOT / "data" / "raw"
CONTRACT_DOCS = ROOT / "documents" / "contracts"

INVOICE_MATCH = MART / "invoice_three_way_match.csv"
SUPPLIER_PERFORMANCE = MART / "supplier_performance.csv"
CONTRACTS = RAW / "contracts.csv"


class ReviewDecision(BaseModel):
    invoice_id: str
    supplier_id: str | None = None
    review_priority: str
    recommended_action: str
    reasons: list[str]
    exception_count: int
    invoice_gross_amount: float | None = None
    note: str = (
        "Deterministic decision support for human review. "
        "This is not a fraud determination or autonomous payment approval."
    )


app = FastAPI(
    title="ProcureAI FMCG Decision API",
    version="1.0.0",
    description=(
        "FastAPI layer for ProcureAI's validated procurement marts. "
        "It exposes invoice exception triage, supplier performance and contract search "
        "for integration with approval workflows such as n8n or an ERP prototype."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://davarkk10.github.io",
        "https://procureai-fmcg-bikashit.netlify.app",
        "http://localhost:3000",
        "http://localhost:8000",
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _require(path: Path, label: str) -> Path:
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                f"{label} is not available yet. Reproduce the ProcureAI data first with "
                "'python src/generate_procureai_data.py' and "
                "'python src/build_release1_reference.py'."
            ),
        )
    return path


@lru_cache(maxsize=8)
def _csv(path_string: str) -> pd.DataFrame:
    return pd.read_csv(path_string, low_memory=False)


def _clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _record(row: pd.Series) -> dict[str, Any]:
    return {str(k): _clean(v) for k, v in row.to_dict().items()}


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    return bool(value)


def _decision_from_row(row: pd.Series) -> ReviewDecision:
    reasons: list[str] = []

    if _truthy(row.get("missing_po_reference_flag")):
        reasons.append("Missing or invalid purchase-order reference")
    if _truthy(row.get("price_exception_flag")):
        reasons.append("Invoice price differs from purchase-order price beyond the rule threshold")
    if _truthy(row.get("quantity_exception_flag")):
        reasons.append("Invoiced quantity exceeds accepted receipt quantity")
    if _truthy(row.get("probable_duplicate_flag")):
        reasons.append("Invoice is linked to a probable duplicate")
    if _truthy(row.get("bank_detail_change_flag")):
        reasons.append("Supplier bank-detail change requires additional verification")

    exception_count = int(_clean(row.get("exception_count")) or len(reasons))
    severe = _truthy(row.get("probable_duplicate_flag")) or _truthy(row.get("bank_detail_change_flag"))

    if severe or exception_count >= 2:
        priority = "High"
        action = "Hold for human review before approval or payment"
    elif exception_count == 1:
        priority = "Medium"
        action = "Route to procurement reviewer with the flagged evidence"
    else:
        priority = "Low"
        action = "No deterministic exception detected; continue the normal approval workflow"

    amount = _clean(row.get("invoice_gross_amount"))
    return ReviewDecision(
        invoice_id=str(row.get("invoice_id")),
        supplier_id=None if _clean(row.get("supplier_id")) is None else str(row.get("supplier_id")),
        review_priority=priority,
        recommended_action=action,
        reasons=reasons,
        exception_count=exception_count,
        invoice_gross_amount=None if amount is None else float(amount),
    )


@app.get("/", tags=["System"])
def root() -> dict[str, Any]:
    return {
        "service": "ProcureAI FMCG Decision API",
        "version": app.version,
        "purpose": "Expose validated procurement analytics to workflow and application layers",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["System"])
def health() -> dict[str, Any]:
    contract_count = len(list(CONTRACT_DOCS.glob("*.pdf"))) if CONTRACT_DOCS.exists() else 0
    required = {
        "invoice_three_way_match": INVOICE_MATCH.exists(),
        "supplier_performance": SUPPLIER_PERFORMANCE.exists(),
        "contracts": CONTRACTS.exists(),
    }
    return {
        "status": "ready" if all(required.values()) else "data_not_generated",
        "datasets": required,
        "contract_pdfs": contract_count,
        "synthetic_data_only": True,
    }


@app.get("/api/v1/exceptions", tags=["Invoice Review"])
def list_exceptions(
    limit: int = Query(25, ge=1, le=200),
    min_exceptions: int = Query(1, ge=1, le=5),
    supplier_id: str | None = None,
) -> dict[str, Any]:
    frame = _csv(str(_require(INVOICE_MATCH, "Invoice exception mart"))).copy()
    frame["exception_count"] = pd.to_numeric(frame["exception_count"], errors="coerce").fillna(0).astype(int)
    frame = frame[frame["exception_count"] >= min_exceptions]

    if supplier_id:
        frame = frame[frame["supplier_id"].astype(str).eq(supplier_id)]

    frame["invoice_gross_amount"] = pd.to_numeric(frame["invoice_gross_amount"], errors="coerce")
    frame = frame.sort_values(
        ["exception_count", "invoice_gross_amount"],
        ascending=[False, False],
        na_position="last",
    ).head(limit)

    fields = [
        "invoice_id",
        "supplier_id",
        "po_id",
        "invoice_date",
        "invoice_gross_amount",
        "exception_count",
        "missing_po_reference_flag",
        "price_exception_flag",
        "quantity_exception_flag",
        "probable_duplicate_flag",
        "bank_detail_change_flag",
        "exception_status",
    ]
    available = [c for c in fields if c in frame.columns]
    return {
        "count": int(len(frame)),
        "ranking": "exception_count desc, then invoice_gross_amount desc",
        "records": [_record(row) for _, row in frame[available].iterrows()],
    }


@app.get(
    "/api/v1/invoices/{invoice_id}/decision-support",
    response_model=ReviewDecision,
    tags=["Invoice Review"],
)
def invoice_decision_support(invoice_id: str) -> ReviewDecision:
    frame = _csv(str(_require(INVOICE_MATCH, "Invoice exception mart")))
    match = frame[frame["invoice_id"].astype(str).eq(invoice_id)]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Invoice '{invoice_id}' was not found")
    return _decision_from_row(match.iloc[0])


@app.get("/api/v1/suppliers/{supplier_id}/performance", tags=["Supplier Performance"])
def supplier_performance(supplier_id: str) -> dict[str, Any]:
    frame = _csv(str(_require(SUPPLIER_PERFORMANCE, "Supplier performance mart")))
    match = frame[frame["supplier_id"].astype(str).eq(supplier_id)]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Supplier '{supplier_id}' was not found")

    row = match.iloc[0]
    data = _record(row)

    otif = float(data.get("otif_rate") or 0)
    rejection = float(data.get("rejection_rate") or 0)
    if otif < 0.75 or rejection > 0.08 or str(data.get("risk_tier", "")).lower() == "high":
        review_band = "High"
    elif otif < 0.88 or rejection > 0.04 or str(data.get("risk_tier", "")).lower() == "medium":
        review_band = "Medium"
    else:
        review_band = "Low"

    return {
        "supplier": data,
        "review_band": review_band,
        "interpretation": (
            "Operational review band derived from OTIF, rejection rate and the synthetic supplier risk tier; "
            "it is not a credit rating."
        ),
    }


@lru_cache(maxsize=1)
def _contract_index() -> list[dict[str, str | None]]:
    contracts = _csv(str(_require(CONTRACTS, "Contracts source")))
    rows: list[dict[str, str | None]] = []

    for _, row in contracts.iterrows():
        contract_id = str(row.get("contract_id"))
        document_path = row.get("document_path")
        pdf_path = ROOT / str(document_path) if isinstance(document_path, str) else CONTRACT_DOCS / f"{contract_id}.pdf"
        text = ""
        if pdf_path.exists():
            try:
                reader = PdfReader(str(pdf_path))
                text = "\n".join((page.extract_text() or "") for page in reader.pages)
            except Exception:
                text = ""

        rows.append(
            {
                "contract_id": contract_id,
                "supplier_id": None if _clean(row.get("supplier_id")) is None else str(row.get("supplier_id")),
                "contract_title": None if _clean(row.get("contract_title")) is None else str(row.get("contract_title")),
                "document_path": None if _clean(document_path) is None else str(document_path),
                "text": text,
            }
        )
    return rows


def _snippet(text: str, query: str, radius: int = 220) -> str | None:
    if not text:
        return None
    low = text.lower()
    pos = low.find(query.lower())
    if pos < 0:
        return text[: radius * 2].strip() or None
    start = max(0, pos - radius)
    end = min(len(text), pos + len(query) + radius)
    compact = " ".join(text[start:end].split())
    return compact


@app.get("/api/v1/contracts/search", tags=["Contract Evidence"])
def search_contracts(
    q: str = Query(..., min_length=2, max_length=120),
    supplier_id: str | None = None,
    limit: int = Query(10, ge=1, le=50),
) -> dict[str, Any]:
    needle = q.lower().strip()
    results: list[dict[str, Any]] = []

    for item in _contract_index():
        if supplier_id and item["supplier_id"] != supplier_id:
            continue
        haystack = " ".join(
            str(item.get(k) or "") for k in ("contract_id", "supplier_id", "contract_title", "text")
        ).lower()
        if needle not in haystack:
            continue
        results.append(
            {
                "contract_id": item["contract_id"],
                "supplier_id": item["supplier_id"],
                "contract_title": item["contract_title"],
                "document_path": item["document_path"],
                "evidence_snippet": _snippet(str(item.get("text") or ""), q),
            }
        )
        if len(results) >= limit:
            break

    return {
        "query": q,
        "count": len(results),
        "results": results,
        "method": "Deterministic keyword search over generated synthetic contract PDFs and contract metadata",
    }
