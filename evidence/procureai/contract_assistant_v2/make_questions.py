"""Write the contract-assistant question sets BEFORE any retriever exists.

dev.jsonl      - used while building and tuning
heldout.jsonl  - frozen now; its sha256 is recorded; run once at the end and reported as-is

The two sets use different phrasings and different documents. Each item carries the
exact answer string as it appears in the PDF, the file and page that must be cited,
or answerable=false when the documents do not contain the answer.

Usage: python make_questions.py <data/raw> <documents dir> <out dir>
"""
import hashlib
import json
import random
import sys
from pathlib import Path

import pandas as pd

RAW, DOCS, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
ctr = pd.read_csv(RAW / "contracts.csv")
sup = pd.read_csv(RAW / "suppliers.csv").set_index("supplier_id").supplier_name.to_dict()
ih = pd.read_csv(RAW / "invoice_headers.csv")
inv = ih[ih.document_path.notna()].head(80)
q = pd.read_csv(RAW / "supplier_quotes.csv")
qgroups = list(q.groupby(["supplier_id", "rfq_id"], sort=False))[:40]


def c_facts(r):
    return {
        "escalation": f"{r.price_escalation_cap_pct:.1f} percent",
        "notice": f"{r.termination_notice_days} days",
        "end": str(r.end_date), "start": str(r.start_date),
        "renewal": "not enabled" if not r.auto_renewal_flag else "enabled",
        "value": f"{r.contract_value:,.2f}", "law": r.governing_law_state,
        "payment": r.payment_term_id, "supplier": sup[r.supplier_id],
    }


# page of each clause: contracts are short; clauses 1-8 on page 1, 9-12 may run to page 2.
# The grader accepts the file plus the page the answer sentence is actually on (checked against the PDF text).
DEV_T = {
    "escalation": ["What is the annual price escalation cap in {cid}?", "Price escalation limit for contract {cid}"],
    "notice": ["What termination notice period applies to {cid}?", "Notice days required to terminate {cid}"],
    "end": ["What is the end date of {cid}?"], "start": ["What is the start date of {cid}?"],
    "renewal": ["Is auto renewal enabled for {cid}?"], "value": ["What is the contract value of {cid}?"],
    "law": ["What is the governing law state for {cid}?"], "payment": ["Which payment term applies to {cid}?"],
    "supplier": ["Which supplier is party to {cid}?"],
}
HELD_T = {
    "escalation": ["max price hike % allowed for {cid}", "By how much can prices go up each year under {cid}?",
                   "what's the ceiling on yearly price increases in {cid}"],
    "notice": ["how many days warning do we owe to get out of {cid}", "If we want to end {cid}, how much notice is needed?"],
    "end": ["when does {cid} expire", "last day {cid} is valid?"],
    "start": ["{cid} kicks in from which date?"],
    "renewal": ["does {cid} roll over by itself at the end", "will {cid} renew automatically?"],
    "value": ["roughly how much is {cid} worth"],
    "law": ["which state's courts and law apply to {cid}?", "jurisdiction for {cid}"],
    "payment": ["what pay terms did we agree in {cid}"],
    "supplier": ["who is the vendor on {cid}?"],
}
POLICY_DEV = [
    ("Purchases above what amount require three quotations?", "500,000", "procurement_policy.pdf"),
    ("What price difference triggers documented review?", "two percent", "invoice_approval_policy.pdf"),
    ("Which invoices require senior approval?", "1,000,000", "invoice_approval_policy.pdf"),
]
POLICY_HELD = [
    ("How big does a purchase have to be before we need 3 competing quotes?", "500,000", "procurement_policy.pdf"),
    ("how far can an invoice price drift from the PO before someone must check it", "two percent", "invoice_approval_policy.pdf"),
    ("At what invoice value does a senior person have to sign off?", "1,000,000", "invoice_approval_policy.pdf"),
    ("Can an AI recommendation release a payment on its own?", "No AI recommendation", "procurement_policy.pdf"),
    ("what happens if a supplier sends the same invoice number twice", "held for investigation", "invoice_approval_policy.pdf"),
]
UNANSWERABLE_DEV = ["What late delivery penalty applies to {cid}?", "What is the termination notice period for CTR00999?"]
UNANSWERABLE_HELD = ["what % penalty do we charge if {cid} delivers late", "warranty period on goods under {cid}?",
                     "who signed {cid} on behalf of the supplier", "insurance cover the vendor must carry under {cid}",
                     "notice period to terminate CTR00777", "what is the exchange rate clause in {cid}"]


def build(templates, policy, unans, contracts, invoices, rng, inv_templates, quote_templates):
    items = []
    for cid in contracts:
        r = ctr[ctr.contract_id == cid].iloc[0]; f = c_facts(r)
        field = rng.choice(list(templates)); text = rng.choice(templates[field]).format(cid=cid)
        items.append({"q": text, "type": f"contract:{field}", "answerable": True, "answer": f[field], "file": f"{cid}.pdf"})
    for text, ans, file in policy:
        items.append({"q": text, "type": "policy", "answerable": True, "answer": ans, "file": file})
    for iid in invoices:
        h = inv[inv.invoice_id == iid].iloc[0]; t, field = rng.choice(inv_templates)
        ans = {"gross": f"{h.invoice_gross_amount:,.2f}", "po": str(h.po_id), "due": str(h.due_date)}[field]
        items.append({"q": t.format(iid=iid), "type": f"invoice:{field}", "answerable": True, "answer": ans, "file": f"{iid}.pdf"})
    for n in quote_templates[1]:
        (sid, rfq), _ = qgroups[n - 1]
        items.append({"q": quote_templates[0].format(n=n), "type": "quote:rfq", "answerable": True, "answer": rfq, "file": f"QUOTE{n:04d}.pdf"})
    for t in unans:
        items.append({"q": t.format(cid=rng.choice(contracts)), "type": "unanswerable", "answerable": False, "answer": None, "file": None})
    return items


all_c = ctr.contract_id.tolist(); random.Random(1).shuffle(all_c)
all_i = inv.invoice_id.tolist(); random.Random(2).shuffle(all_i)
dev = build(DEV_T, POLICY_DEV, UNANSWERABLE_DEV, all_c[:40], all_i[:10], random.Random(11),
            [("What is the gross amount of invoice {iid}?", "gross"), ("Which purchase order does {iid} reference?", "po")],
            ("Which RFQ does QUOTE{n:04d} answer?", [1, 2, 3, 4, 5]))
held = build(HELD_T, POLICY_HELD, UNANSWERABLE_HELD, all_c[40:80], all_i[10:22], random.Random(22),
             [("how much do we owe in total on {iid}", "gross"), ("{iid} is billed against which PO", "po"),
              ("payment for {iid} falls due when?", "due")],
             ("quotation QUOTE{n:04d} was submitted for which RFQ number", [11, 17, 23, 29, 35]))
for name, items in [("dev", dev), ("heldout", held)]:
    p = OUT / f"{name}.jsonl"
    p.write_text("".join(json.dumps(x) + "\n" for x in items))
    print(name, len(items), hashlib.sha256(p.read_bytes()).hexdigest())
