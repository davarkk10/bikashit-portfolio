"""ProcureAI - supplier delay model v3 (enriched drivers).

Same question, splits and rules as v2: predict at order time whether a PO will be
received after its promised date. v3 adds the delivery-driver tables produced by
enrich_delivery_drivers.py. Every feature is known on the order date.

Usage: python supplier_delay_v3.py <original data/raw> <enriched dir> [out_dir]
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

RAW, ENR = Path(sys.argv[1]), Path(sys.argv[2])
OUT = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("delay_v3_out")
OUT.mkdir(parents=True, exist_ok=True)
TRAIN_END, VAL_END, PRIOR_K = pd.Timestamp("2025-03-31"), pd.Timestamp("2025-06-30"), 10

# ------------------------------------------------------------------ load
ph = pd.read_csv(RAW / "purchase_order_headers.csv", parse_dates=["order_date", "promised_delivery_date"])
pl = pd.read_csv(RAW / "purchase_order_lines.csv")
rh = pd.read_csv(ENR / "goods_receipt_headers.csv", parse_dates=["receipt_date"])
lanes = pd.read_csv(ENR / "supplier_lanes.csv")
cap = pd.read_csv(ENR / "supplier_capacity.csv")
risk = pd.read_csv(ENR / "region_flood_risk.csv")
whr = pd.read_csv(ENR / "warehouse_regions.csv")
fest = pd.read_csv(ENR / "festival_calendar.csv", parse_dates=["slowdown_start", "slowdown_end"])
ceil = pd.read_csv(ENR / "ground_truth" / "delay_probability.csv")

po = ph.merge(rh[["po_id", "receipt_date"]], on="po_id")
po = po.merge(pl.groupby("po_id").agg(order_qty=("ordered_quantity", "sum"), n_lines=("po_line_id", "size"),
                                      po_value=("line_gross_amount", "sum")), on="po_id")
po = po.merge(lanes, on=["supplier_id", "warehouse_id"]).merge(cap, on="supplier_id").merge(whr, on="warehouse_id")
po = po.sort_values(["order_date", "po_id"]).reset_index(drop=True)

# ------------------------------------------------------------------ order-time features
po["late"] = (po.receipt_date > po.promised_delivery_date).astype(int)
po["lead_days"] = (po.promised_delivery_date - po.order_date).dt.days
po["promised_month"] = po.promised_delivery_date.dt.month
po["log_value"] = np.log1p(po.po_value)
po["tightness"] = (po.quoted_lead_time_days - po.lead_days) / po.quoted_lead_time_days
po["corridor"] = (po.route_type == "Via Siliguri corridor").astype(int)
rk = risk.set_index(["region", "month"]).weekly_disruption_probability
po["dest_flood_risk"] = [rk[(r, m)] for r, m in zip(po.region, po.promised_month)]
po["corridor_risk"] = np.where(po.corridor == 1, [rk[("Siliguri corridor", m)] for m in po.promised_month], 0.0)
po["festival_window"] = 0
for f in fest.itertuples():
    po.loc[po.promised_delivery_date.between(f.slowdown_start, f.slowdown_end), "festival_window"] = 1

# supplier load and order size use only POs placed before this one
po["orders_prev_30d"] = 0
po["qty_ratio"] = 1.0
for sid, g in po.groupby("supplier_id"):
    d = g.order_date.values
    po.loc[g.index, "orders_prev_30d"] = np.arange(len(d)) - np.searchsorted(d, d - np.timedelta64(30, "D"), side="left")
    past_median = g.order_qty.expanding().median().shift(1).fillna(g.order_qty.iloc[0])
    po.loc[g.index, "qty_ratio"] = g.order_qty.values / past_median.values
po["utilisation"] = po.orders_prev_30d / po.capacity_pos_per_30d
po["log_qty_ratio"] = np.log(po.qty_ratio.clip(0.05, 20))

# ------------------------------------------------------------------ checkpoint 2: re-score 3 days before the promised date
asn = pd.read_csv(ENR / "asn_dispatch.csv", parse_dates=["planned_dispatch_date", "actual_dispatch_date"])
adv = pd.read_csv(ENR / "disruption_advisories.csv", parse_dates=["issued_date", "covers_week_start"])
po = po.merge(asn, on="po_id")
po["rescore_date"] = po.promised_delivery_date - pd.Timedelta(days=3)
seen = np.minimum(po.actual_dispatch_date, po.rescore_date)          # what the ASN feed shows on the re-score date
po["dispatched_by_rescore"] = (po.actual_dispatch_date <= po.rescore_date).astype(int)
po["dispatch_slip_seen"] = (seen - po.planned_dispatch_date).dt.days.clip(lower=0)
po["days_since_dispatch"] = np.where(po.dispatched_by_rescore == 1, (po.rescore_date - po.actual_dispatch_date).dt.days, -1)
pweek = po.promised_delivery_date - pd.to_timedelta(po.promised_delivery_date.dt.weekday, unit="D")
adv_known = {}
for a in adv.itertuples():
    adv_known.setdefault((a.region, a.covers_week_start), []).append(a.issued_date)
def advised(region, week, asof):
    return int(any(d <= asof for d in adv_known.get((region, week), [])))
po["advisory_destination"] = [advised(r, w, t) for r, w, t in zip(po.region, pweek, po.rescore_date)]
po["advisory_corridor"] = [advised("Siliguri corridor", w, t) if c else 0 for c, w, t in zip(po.corridor, pweek, po.rescore_date)]
po = po[po.po_status != "Cancelled"].reset_index(drop=True)


def supplier_history(df):
    out = []
    events = df[["supplier_id", "receipt_date", "late"]].sort_values("receipt_date")
    for sid, orders in df.groupby("supplier_id"):
        ev = events[events.supplier_id == sid]
        t, cn, cl = ev.receipt_date.values, np.arange(1, len(ev) + 1), ev.late.cumsum().values
        i = np.searchsorted(t, orders.order_date.values, side="left")
        i90 = np.searchsorted(t, (orders.order_date - pd.Timedelta(days=90)).values, side="left")
        n, nl = np.where(i > 0, cn[i - 1], 0), np.where(i > 0, cl[i - 1], 0)
        out.append(pd.DataFrame({"po_id": orders.po_id.values, "hist_n": n, "hist_late": nl,
                                 "n90": n - np.where(i90 > 0, cn[i90 - 1], 0),
                                 "late90": nl - np.where(i90 > 0, cl[i90 - 1], 0)}))
    return pd.concat(out)


po = po.merge(supplier_history(po), on="po_id").merge(ceil, on="po_id")

train = po[(po.order_date <= TRAIN_END) & (po.receipt_date <= TRAIN_END)].copy()
censored = int(((po.order_date <= TRAIN_END) & (po.receipt_date > TRAIN_END)).sum())
val = po[(po.order_date > TRAIN_END) & (po.order_date <= VAL_END)].copy()
test = po[po.order_date > VAL_END].copy()
prior = float(train.late.mean())
for d in (train, val, test):
    d["hist_rate"] = (d.hist_late + PRIOR_K * prior) / (d.hist_n + PRIOR_K)
    d["rate90"] = (d.late90 + PRIOR_K * d.hist_rate) / (d.n90 + PRIOR_K)
    d["log_hist_n"] = np.log1p(d.hist_n)

V2 = ["hist_rate", "rate90", "log_hist_n", "lead_days", "promised_month"]
GROUPS = {
    "distance & route": ["road_distance_km", "corridor"],
    "flood climatology": ["dest_flood_risk", "corridor_risk"],
    "festival calendar": ["festival_window"],
    "supplier load": ["utilisation", "orders_prev_30d"],
    "order size": ["log_qty_ratio"],
    "promise vs quoted lead": ["tightness", "quoted_lead_time_days"],
}
V3 = V2 + [c for g in GROUPS.values() for c in g]


def ece(y, p, bins=10):
    b = np.clip(np.digitize(p, np.linspace(0, 1, bins + 1)) - 1, 0, bins - 1)
    return float(sum(abs(p[b == i].mean() - y[b == i].mean()) * (b == i).mean() for i in range(bins) if (b == i).any()))


def at_k(y, p, k):
    top = np.argsort(-p, kind="stable")[:k]
    return {"precision": float(y[top].mean()), "recall": float(y[top].sum() / y.sum())}


def fit_gbm(cols, tr):
    cat = [cols.index("promised_month")] if "promised_month" in cols else None
    return HistGradientBoostingClassifier(max_iter=400, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=100,
                                          l2_regularization=1.0, categorical_features=cat, random_state=7).fit(tr[cols], tr.late)


def logit_cols(cols, df):
    X = df[cols].astype(float).copy()
    if "promised_month" in cols:
        X = pd.concat([X.drop(columns="promised_month"),
                       pd.get_dummies(df.promised_month.astype(pd.CategoricalDtype(range(1, 13))), prefix="m").astype(float)], axis=1)
    return X


def fit_lr(cols, tr):
    X = logit_cols(cols, tr)
    mu, sd = X.mean(), X.std().replace(0, 1)
    m = LogisticRegression(C=1.0, max_iter=3000).fit((X - mu) / sd, tr.late)
    return lambda df: m.predict_proba((logit_cols(cols, df) - mu) / sd)[:, 1]


y_va, y_te = val.late.values, test.late.values
k_va, k_te = int(0.25 * len(val)), int(0.25 * len(test))
preds = {}
g2 = fit_gbm(V2, train); preds["v2 features (GBM)"] = (g2.predict_proba(val[V2])[:, 1], g2.predict_proba(test[V2])[:, 1])
l2 = fit_lr(V2, train); preds["v2 features (logistic)"] = (l2(val), l2(test))
g3 = fit_gbm(V3, train); preds["v3 features (GBM)"] = (g3.predict_proba(val[V3])[:, 1], g3.predict_proba(test[V3])[:, 1])
l3 = fit_lr(V3, train); preds["v3 features (logistic)"] = (l3(val), l3(test))
preds["order-time ceiling"] = (val.p_late_order_time_ceiling.values, test.p_late_order_time_ceiling.values)
PRE = V3 + ["dispatched_by_rescore", "dispatch_slip_seen", "days_since_dispatch", "advisory_destination", "advisory_corridor"]
gp = fit_gbm(PRE, train); preds["pre-arrival (GBM)"] = (gp.predict_proba(val[PRE])[:, 1], gp.predict_proba(test[PRE])[:, 1])
lp = fit_lr(PRE, train); preds["pre-arrival (logistic)"] = (lp(val), lp(test))
preds["pre-arrival upper bound"] = (val.p_late_prearrival_upper_bound.values, test.p_late_prearrival_upper_bound.values)

res = {n: {"val_pr_auc": float(average_precision_score(y_va, v)), "test_pr_auc": float(average_precision_score(y_te, t)),
           "test_roc_auc": float(roc_auc_score(y_te, t)), "test_ece": ece(y_te, t), "test_at_25pct": at_k(y_te, t, k_te)}
       for n, (v, t) in preds.items()}
chosen = max([n for n in res if n.startswith("v3")], key=lambda n: res[n]["val_pr_auc"])
chosen_v2 = max([n for n in res if n.startswith("v2")], key=lambda n: res[n]["val_pr_auc"])
chosen_pre = max(["pre-arrival (GBM)", "pre-arrival (logistic)"], key=lambda n: res[n]["val_pr_auc"])
pre_curve = {f"{int(c*100)}%": at_k(y_te, preds[chosen_pre][1], int(c * len(test))) for c in (0.10, 0.25, 0.40, 0.50)}

# capacity curve for the chosen model
pt = preds[chosen][1]
curve = {f"{int(c*100)}%": at_k(y_te, pt, int(c * len(test))) for c in (0.10, 0.25, 0.40, 0.50)}

# ablation on validation: drop one driver group at a time (GBM)
base_val = average_precision_score(y_va, g3.predict_proba(val[V3])[:, 1])
ablation = {}
for gname, cols in GROUPS.items():
    keep = [c for c in V3 if c not in cols]
    m = fit_gbm(keep, train)
    ablation[gname] = float(base_val - average_precision_score(y_va, m.predict_proba(val[keep])[:, 1]))

# bootstrap CI for v3 over v2 on test
rng = np.random.default_rng(11)
d = []
for _ in range(500):
    i = rng.integers(0, len(y_te), len(y_te))
    d.append(average_precision_score(y_te[i], preds[chosen][1][i]) - average_precision_score(y_te[i], preds[chosen_v2][1][i]))

# leakage: flip outcomes received after a date; earlier orders' history must not move
cut = pd.Timestamp("2025-01-01")
pert = po.copy(); m_ = pert.receipt_date >= cut; pert.loc[m_, "late"] = 1 - pert.loc[m_, "late"]
early = po[po.order_date <= cut].po_id
leak_ok = bool((supplier_history(po).set_index("po_id").loc[early].values ==
                supplier_history(pert).set_index("po_id").loc[early].values).all())

summary = {"rows": {"train": len(train), "censored": censored, "val": len(val), "test": len(test)},
           "test_prevalence": float(y_te.mean()), "chosen_v3": chosen, "chosen_v2": chosen_v2,
           "results": res, "capacity_curve_chosen": curve, "chosen_pre_arrival": chosen_pre,
           "capacity_curve_pre_arrival": pre_curve,
           "ablation_val_pr_auc_drop": dict(sorted(ablation.items(), key=lambda x: -x[1])),
           "v3_minus_v2_test_pr_auc_95ci": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
           "leakage_test_pass": leak_ok}
(OUT / "delay_v3_results.json").write_text(json.dumps(summary, indent=2))

print(f"rows {summary['rows']}  prevalence {y_te.mean():.3f}  leak_ok={leak_ok}")
print(f"{'model':26} {'valPR':>6} {'testPR':>7} {'ROC':>6} {'ECE':>6} {'P@25%':>6} {'R@25%':>6}")
for n, r in res.items():
    print(f"{n:26} {r['val_pr_auc']:6.3f} {r['test_pr_auc']:7.3f} {r['test_roc_auc']:6.3f} {r['test_ece']:6.3f} "
          f"{r['test_at_25pct']['precision']:6.3f} {r['test_at_25pct']['recall']:6.3f}")
print("chosen:", chosen, "| lift CI:", summary["v3_minus_v2_test_pr_auc_95ci"])
print("capacity:", {k: (round(v['precision'], 3), round(v['recall'], 3)) for k, v in curve.items()})
print("ablation:", {k: round(v, 3) for k, v in summary["ablation_val_pr_auc_drop"].items()})
print("pre-arrival:", chosen_pre, {k: (round(v["precision"],3), round(v["recall"],3)) for k,v in pre_curve.items()})

# ------------------------------------------------------------------ optional: scored rows for Power BI
if len(sys.argv) > 4:
    EXP = Path(sys.argv[4]); EXP.mkdir(parents=True, exist_ok=True)
    parts = []
    for name, d in (("Train", train), ("Validation", val), ("Test", test)):
        d = d.copy(); d["split"] = name
        if name != "Train":
            d["p_order"] = l3(d); d["p_pre"] = lp(d)
        parts.append(d)
    E = pd.concat(parts)
    k = int(0.25 * len(test))
    E["flag_order"] = 0; E["flag_pre"] = 0
    tmask = E.split == "Test"
    E.loc[E[tmask].sort_values("p_order", ascending=False).index[:k], "flag_order"] = 1
    E.loc[E[tmask].sort_values("p_pre", ascending=False).index[:k], "flag_pre"] = 1
    E["promise_slack_days"] = E.lead_days - E.quoted_lead_time_days
    E["advisory"] = ((E.advisory_destination + E.advisory_corridor) > 0).astype(int)
    cols = ["po_id", "order_date", "promised_delivery_date", "receipt_date", "supplier_id", "warehouse_id", "po_value", "late",
            "lead_days", "quoted_lead_time_days", "promise_slack_days", "road_distance_km", "route_type", "utilisation",
            "festival_window", "dest_flood_risk", "dispatched_by_rescore", "dispatch_slip_seen", "advisory", "hist_rate",
            "split", "p_order", "p_pre", "flag_order", "flag_pre"]
    E = E[cols].rename(columns={"promised_delivery_date": "promised_date", "hist_rate": "supplier_past_late_rate"})
    for c in ("order_date", "promised_date", "receipt_date"):
        E[c] = pd.to_datetime(E[c]).dt.date
    for c in ("p_order", "p_pre", "utilisation", "supplier_past_late_rate", "dest_flood_risk"):
        E[c] = E[c].round(4)
    E["po_value"] = E.po_value.round(2)
    E.to_csv(EXP / "fact_po.csv", index=False)
    print("exported", len(E), "POs; test flagged", int(E.flag_order.sum()))
