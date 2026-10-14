"""ProcureAI - supplier delay model v2.

Predicts, at the moment a PO is placed, whether its goods receipt will land after
the promised delivery date. Every feature uses only information available on the
order date. Splits are chronological and training labels must have matured
(receipt posted) before the training cutoff.

Usage: python supplier_delay_v2.py <path to data/raw> [out_dir]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

RAW = Path(sys.argv[1])
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("delay_v2_out")
OUT.mkdir(parents=True, exist_ok=True)

TRAIN_END = pd.Timestamp("2025-03-31")
VAL_END = pd.Timestamp("2025-06-30")
PRIOR_K = 10  # smoothing strength for supplier late rates


# ---------------------------------------------------------------- data
ph = pd.read_csv(RAW / "purchase_order_headers.csv", parse_dates=["order_date", "promised_delivery_date"])
pl = pd.read_csv(RAW / "purchase_order_lines.csv")
rh = pd.read_csv(RAW / "goods_receipt_headers.csv", parse_dates=["receipt_date"])
sup = pd.read_csv(RAW / "suppliers.csv")

po = ph[ph.po_status != "Cancelled"].merge(rh[["po_id", "receipt_date"]], on="po_id")
po["late"] = (po.receipt_date > po.promised_delivery_date).astype(int)
agg = pl.groupby("po_id").agg(n_lines=("po_line_id", "size"), po_value=("line_gross_amount", "sum"))
po = po.merge(agg, on="po_id")
po = po.sort_values(["order_date", "po_id"]).reset_index(drop=True)
po["lead_days"] = (po.promised_delivery_date - po.order_date).dt.days
po["promised_month"] = po.promised_delivery_date.dt.month
po["log_value"] = np.log1p(po.po_value)


# ---------------------------------------------------------------- point-in-time supplier history
def supplier_history(df: pd.DataFrame) -> pd.DataFrame:
    """For each PO, the supplier's record from receipts posted strictly before its order date."""
    out = []
    events = df[["supplier_id", "receipt_date", "late", "lead_days"]].sort_values("receipt_date")
    for sid, orders in df.groupby("supplier_id"):
        ev = events[events.supplier_id == sid]
        t = ev.receipt_date.values
        cum_n = np.arange(1, len(ev) + 1)
        cum_late = ev.late.cumsum().values
        cum_lead = ev.lead_days.cumsum().values
        idx = np.searchsorted(t, orders.order_date.values, side="left")  # receipts before order date
        n = np.where(idx > 0, cum_n[idx - 1], 0)
        nl = np.where(idx > 0, cum_late[idx - 1], 0)
        ld = np.where(idx > 0, cum_lead[idx - 1], 0)
        # recent window: last 90 days of receipts
        idx90 = np.searchsorted(t, (orders.order_date - pd.Timedelta(days=90)).values, side="left")
        n90 = n - np.where(idx90 > 0, cum_n[idx90 - 1], 0)
        nl90 = nl - np.where(idx90 > 0, cum_late[idx90 - 1], 0)
        out.append(pd.DataFrame({"po_id": orders.po_id.values, "hist_n": n, "hist_late": nl,
                                 "hist_lead_sum": ld, "n90": n90, "late90": nl90}))
    return pd.concat(out)


po = po.merge(supplier_history(po), on="po_id")


def add_rates(df: pd.DataFrame, prior: float) -> pd.DataFrame:
    df = df.copy()
    df["hist_rate"] = (df.hist_late + PRIOR_K * prior) / (df.hist_n + PRIOR_K)
    df["rate90"] = (df.late90 + PRIOR_K * df.hist_rate) / (df.n90 + PRIOR_K)
    df["hist_lead_mean"] = np.where(df.hist_n > 0, df.hist_lead_sum / df.hist_n.clip(lower=1), np.nan)
    df["lead_vs_usual"] = df.lead_days - df.hist_lead_mean
    df["log_hist_n"] = np.log1p(df.hist_n)
    return df


# ---------------------------------------------------------------- splits (labels must mature)
train = po[(po.order_date <= TRAIN_END) & (po.receipt_date <= TRAIN_END)]
censored = int(((po.order_date <= TRAIN_END) & (po.receipt_date > TRAIN_END)).sum())
val = po[(po.order_date > TRAIN_END) & (po.order_date <= VAL_END)]
test = po[po.order_date > VAL_END]
prior = float(train.late.mean())
train, val, test = (add_rates(d, prior) for d in (train, val, test))


def logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def month_dummies(df):
    return pd.get_dummies(df.promised_month.astype(pd.CategoricalDtype(range(1, 13))), prefix="m").astype(float)


def X_logreg(df):
    X = pd.DataFrame({"logit_hist": logit(df.hist_rate.values), "logit_90": logit(df.rate90.values),
                      "lead_days": df.lead_days.values / 10, "log_hist_n": df.log_hist_n.values})
    return pd.concat([X.reset_index(drop=True), month_dummies(df).reset_index(drop=True)], axis=1)


GB_COLS = ["hist_rate", "rate90", "log_hist_n", "lead_days", "lead_vs_usual", "promised_month",
           "n_lines", "log_value"]


# ---------------------------------------------------------------- metrics
def ece(y, p, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    b = np.clip(np.digitize(p, edges) - 1, 0, bins - 1)
    return float(sum(abs(p[b == i].mean() - y[b == i].mean()) * (b == i).mean() for i in range(bins) if (b == i).any()))


def at_k(y, p, k):
    top = np.argsort(-p, kind="stable")[:k]
    tp = int(y[top].sum())
    return {"precision": tp / k, "recall": tp / int(y.sum())}


def report(y, p, k):
    return {"pr_auc": float(average_precision_score(y, p)), "roc_auc": float(roc_auc_score(y, p)),
            "ece": ece(y, p), "at_capacity": at_k(y, p, k)}


# ---------------------------------------------------------------- models
y_tr, y_va, y_te = train.late.values, val.late.values, test.late.values
scores = {}

# Baseline: supplier's own history (what the v1 model tied with)
scores["baseline_history"] = {"val": val.hist_rate.values, "test": test.hist_rate.values}

# v2a: logistic regression with seasonality
lr = LogisticRegression(C=1.0, max_iter=2000).fit(X_logreg(train), y_tr)
scores["logreg_season"] = {"val": lr.predict_proba(X_logreg(val))[:, 1], "test": lr.predict_proba(X_logreg(test))[:, 1]}

# v2b: gradient boosting (monotone in supplier late rate)
mono = [1 if c in ("hist_rate", "rate90") else 0 for c in GB_COLS]
gb = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=200,
                                    l2_regularization=1.0, monotonic_cst=mono, categorical_features=[GB_COLS.index("promised_month")],
                                    random_state=7).fit(train[GB_COLS], y_tr)
scores["gbm"] = {"val": gb.predict_proba(val[GB_COLS])[:, 1], "test": gb.predict_proba(test[GB_COLS])[:, 1]}

# Oracle: the generator's own lateness probability (uses hidden base_reliability; a ceiling, not a model)
rel = sup.set_index("supplier_id").base_reliability
def oracle(df):
    seasonal = np.where(df.promised_month.isin([4, 10, 11, 12]), 0.12, 0.0)
    return np.minimum(0.62, (1 - df.supplier_id.map(rel).values) * 1.5 + seasonal)
scores["oracle_ceiling"] = {"val": oracle(val), "test": oracle(test)}

# Review capacity: fixed for every model so recall comparisons are fair (25% of test POs)
k_val, k_test = int(0.25 * len(val)), int(0.25 * len(test))
results = {name: {"val": report(y_va, s["val"], k_val), "test": report(y_te, s["test"], k_test)} for name, s in scores.items()}

# Model selection on validation only; test is read once
candidates = ["logreg_season", "gbm"]
chosen = max(candidates, key=lambda m: results[m]["val"]["pr_auc"])

# Leakage check: perturb outcomes AFTER a date; features for orders before it must not change
cut = pd.Timestamp("2025-01-01")
pert = po.copy()
pert.loc[pert.receipt_date >= cut, "late"] = 1 - pert.loc[pert.receipt_date >= cut, "late"]
h1 = supplier_history(pert)
early = po[po.order_date <= cut].po_id
a = supplier_history(po).set_index("po_id").loc[early]
b = h1.set_index("po_id").loc[early]
leak_test_pass = bool((a.values == b.values).all())

# Paired bootstrap on test: is the chosen model's PR-AUC lift over the baseline real?
rng = np.random.default_rng(11)
diffs = []
for _ in range(1000):
    i = rng.integers(0, len(y_te), len(y_te))
    diffs.append(average_precision_score(y_te[i], scores[chosen]["test"][i])
                 - average_precision_score(y_te[i], scores["baseline_history"]["test"][i]))
lift_ci = [float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))]
headroom = results["oracle_ceiling"]["test"]["pr_auc"] - results["baseline_history"]["test"]["pr_auc"]
captured = (results[chosen]["test"]["pr_auc"] - results["baseline_history"]["test"]["pr_auc"]) / headroom

summary = {
    "pr_auc_lift_vs_baseline_95ci": lift_ci,
    "share_of_headroom_to_ceiling_captured": float(captured),
    "unit": "purchase order (non-cancelled), label = receipt after promised date",
    "rows": {"train_matured": len(train), "train_censored_excluded": censored, "val": len(val), "test": len(test)},
    "prevalence": {"train": float(y_tr.mean()), "val": float(y_va.mean()), "test": float(y_te.mean())},
    "review_capacity_test": k_test,
    "chosen_on_validation": chosen,
    "leakage_perturbation_test_pass": leak_test_pass,
    "logreg_month_coefficients": {f"m_{i}": round(float(c), 3) for i, c in zip(range(1, 13), lr.coef_[0][4:])},
    "results": results,
}
(OUT / "delay_v2_results.json").write_text(json.dumps(summary, indent=2))

print(f"rows train/val/test = {len(train)}/{len(val)}/{len(test)}  censored={censored}  leak_test={leak_test_pass}")
print(f"chosen on validation: {chosen}   test capacity K={k_test}")
print(f"{'model':18} {'val PR-AUC':>10} {'test PR-AUC':>11} {'ROC':>6} {'ECE':>6} {'prec@K':>7} {'rec@K':>6}")
for n, r in results.items():
    t = r["test"]
    print(f"{n:18} {r['val']['pr_auc']:10.3f} {t['pr_auc']:11.3f} {t['roc_auc']:6.3f} {t['ece']:6.3f} "
          f"{t['at_capacity']['precision']:7.3f} {t['at_capacity']['recall']:6.3f}")
print("month coefs:", summary["logreg_month_coefficients"])
