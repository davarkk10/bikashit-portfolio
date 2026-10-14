"""Build the CSV folder the ProcureAI Power BI project imports.

Inputs (all reproducible from the repo scripts):
  <raw>        original corpus, seed 20260927 (suppliers, categories, warehouses)
  <pbi_data>   fact_invoice.csv and fact_po.csv exported by invoice_anomaly_v2.py and supplier_delay_v3.py
  <inv_json>   invoice_v2_results.json
  <delay_json> delay_v3_results.json
  <qa_json>    heldout_first_run.json (contract assistant)
Writes dim_*.csv, model_results.csv, invoice_catch.csv, driver_importance.csv, contract_qa.csv
and expected_values.json (numbers the report must show, for checking after refresh).

Usage: python build_pbi_data.py <raw> <pbi_data> <inv_json> <delay_json> <qa_json>
"""
import json
import sys
from pathlib import Path

import pandas as pd

RAW, OUT = Path(sys.argv[1]), Path(sys.argv[2])
inv = json.loads(Path(sys.argv[3]).read_text())
dl = json.loads(Path(sys.argv[4]).read_text())
qa = json.loads(Path(sys.argv[5]).read_text())["rows"]

cat = pd.read_csv(RAW / "categories.csv")
sup = pd.read_csv(RAW / "suppliers.csv").merge(cat[["category_id", "category_name", "category_group"]],
                                              left_on="primary_category_id", right_on="category_id")
sup[["supplier_id", "supplier_name", "city", "category_name", "category_group"]].to_csv(OUT / "dim_supplier.csv", index=False)
wh = pd.read_csv(RAW / "warehouses.csv")
region = {"WH001": "Brahmaputra lower", "WH002": "Brahmaputra upper", "WH003": "Brahmaputra upper",
          "WH004": "Brahmaputra upper", "WH005": "Barak valley", "WH006": "Brahmaputra lower"}
wh["flood_region"] = wh.warehouse_id.map(region)
wh[["warehouse_id", "warehouse_name", "city", "flood_region"]].to_csv(OUT / "dim_warehouse.csv", index=False)

# ---- headline results (long format: one row per method x metric)
R = []
def add(area, method, role, order, **metrics):
    for m, v in metrics.items():
        R.append({"area": area, "method": method, "role": role, "method_order": order, "metric": m, "value": round(float(v), 4)})
t = inv["test"]; h = inv["test_subtle_only_pr_auc"]
add("Invoice risk", "Policy rules as written", "Rules", 1, pr_auc=t["policy rules"]["pr_auc"], pr_auc_hard=h["policy rules"],
    precision_at_capacity=t["policy rules"]["precision_at_k"])
add("Invoice risk", "Best hand-written rules", "Rules", 2, pr_auc=t["refined rules"]["pr_auc"], pr_auc_hard=h["refined rules"],
    precision_at_capacity=t["refined rules"]["precision_at_k"])
add("Invoice risk", "Gradient boosting", "Model", 3, pr_auc=t["model"]["pr_auc"], pr_auc_hard=h["model"],
    precision_at_capacity=t["model"]["precision_at_k"])
r = dl["results"]
for order, (key, name, role) in enumerate([("v2 features (logistic)", "Supplier history only", "Baseline"),
                                           ("v3 features (logistic)", "Logistic regression, order time", "Model"),
                                           ("pre-arrival (logistic)", "Logistic regression, 3 days before", "Model")], 1):
    x = r[key]
    add("Late delivery", name, role, order, pr_auc=x["test_pr_auc"], precision_at_capacity=x["test_at_25pct"]["precision"],
        recall_at_capacity=x["test_at_25pct"]["recall"])
add("Late delivery", "Best possible at order time", "Ceiling", 4, pr_auc=r["order-time ceiling"]["test_pr_auc"])
ok = [q for q in qa if q["ok"]]
add("Contract assistant", "BM25 + thesaurus", "Model", 1, correct=len(ok), questions=len(qa),
    wrong_answers=sum((not q["ok"]) and (not q["response"]["abstain"]) for q in qa),
    refusals_correct=sum(q["ok"] for q in qa if not q["answerable"]), unanswerable=sum(not q["answerable"] for q in qa))
pd.DataFrame(R).to_csv(OUT / "model_results.csv", index=False)

names = {"PRICE_CREEP": "Price creep", "SPLIT_BELOW_APPROVAL": "Split below approval", "NEAR_DUPLICATE": "Near-duplicate",
         "PRICE_MISMATCH": "Price over tolerance", "QUANTITY_MISMATCH": "Quantity over order", "BANK_DETAIL_CHANGE": "Bank detail change",
         "MISSING_PO_REFERENCE": "Missing PO", "PROBABLE_DUPLICATE": "Exact duplicate"}
hard = {"PRICE_CREEP", "SPLIT_BELOW_APPROVAL", "NEAR_DUPLICATE"}
pd.DataFrame([{"condition": names[k], "condition_group": "Hard case" if k in hard else "Simple mismatch", "test_cases": v["n"],
               "rules_caught": round(v["refined_rules"], 4), "model_caught": round(v["model_top_k"], 4)}
              for k, v in inv["recall_by_type"].items()]).to_csv(OUT / "invoice_catch.csv", index=False)

drv = {"supplier load": "Supplier load vs capacity", "promise vs quoted lead": "Promised vs quoted lead time",
       "festival calendar": "Festival calendar", "order size": "Order size vs usual", "distance & route": "Distance and route",
       "flood climatology": "Flood-risk history"}
pd.DataFrame([{"driver": drv[k], "pr_auc_lost_when_removed": round(v, 4)} for k, v in dl["ablation_val_pr_auc_drop"].items()]
             ).to_csv(OUT / "driver_importance.csv", index=False)

rows = []
for i, q in enumerate(qa, 1):
    resp = q["response"]
    if q["ok"]:
        result = "Correct refusal" if not q["answerable"] else "Correct answer"
    else:
        result = "Missed (refused)" if resp["abstain"] else "Wrong answer"
    rows.append({"question_no": i, "question": q["q"], "question_type": q["type"].split(":")[0].title(),
                 "answerable": int(q["answerable"]), "result": result, "is_correct": int(q["ok"]),
                 "answer": resp.get("answer", resp.get("reason")), "citation": resp.get("citation", "")})
pd.DataFrame(rows).to_csv(OUT / "contract_qa.csv", index=False)

# ---- expected values the refreshed report must show
fi = pd.read_csv(OUT / "fact_invoice.csv"); fp = pd.read_csv(OUT / "fact_po.csv")
ti, tp = fi[fi.split == "Test"], fp[fp.split == "Test"]
exp = {
    "Invoices": len(fi), "Invoice Value (INR)": round(fi.gross_amount.sum(), 2),
    "Test Invoices": len(ti), "Test Conditions": int(ti.is_condition.sum()),
    "Model Flagged (test)": int(ti.model_flag.sum()), "Model Precision (test)": round(ti[ti.model_flag == 1].is_condition.mean(), 4),
    "Model Recall (test)": round(ti[ti.model_flag == 1].is_condition.sum() / ti.is_condition.sum(), 4),
    "Rules Flagged (test)": int(ti.rules_refined.sum()), "Rules Precision (test)": round(ti[ti.rules_refined == 1].is_condition.mean(), 4),
    "Rules Recall (test)": round(ti[ti.rules_refined == 1].is_condition.sum() / ti.is_condition.sum(), 4),
    "POs Modelled": len(fp), "Test POs": len(tp), "Test Late %": round(tp.late.mean(), 4),
    "Flagged Late % (order time)": round(tp[tp.flag_order == 1].late.mean(), 4),
    "Flagged Late % (3 days before)": round(tp[tp.flag_pre == 1].late.mean(), 4),
    "Late Caught (order time)": round(tp[tp.flag_order == 1].late.sum() / tp.late.sum(), 4),
    "Contract Correct": len(ok), "Contract Questions": len(qa),
}
(OUT / "expected_values.json").write_text(json.dumps(exp, indent=2))
print(json.dumps(exp, indent=2))
