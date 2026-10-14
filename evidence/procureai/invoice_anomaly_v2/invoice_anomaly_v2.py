"""ProcureAI - invoice anomaly v2: subtle conditions and realistic noise.

The first-release anomalies (price +8-25%, quantity +5-18%, missing PO, bank change,
exact duplicate) are caught by simple rules, so ML could not show value. v2 keeps those
and adds three conditions that single-invoice rules miss, plus benign look-alikes so
they are not trivially separable:

  SPLIT_BELOW_APPROVAL  one large bill split into 2-3 invoices just under the INR 10 lakh
                        senior-approval limit, submitted within a few days
  PRICE_CREEP           a few suppliers bill +0.8-1.9% over PO price for months, always
                        inside the 2% tolerance
  NEAR_DUPLICATE        an earlier invoice resubmitted weeks later with an altered invoice
                        number and a slightly changed amount
Benign noise on clean invoices:
  - 18% get one line priced -1.5% to +1.8% off PO (freight, rounding, legit and in tolerance)
  - 6% of POs are invoiced in two legitimate partial bills
  - legitimate invoices just under 10 lakh occur naturally

Compared on the same chronological split: policy rules as written, refined rules
(policy + exact-amount duplicate + over-billing against PO value), and a gradient-boosted
model on point-in-time features.

Usage: python invoice_anomaly_v2.py <data/raw> <data/ground_truth> <out_dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score

RAW, GT, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(20261015)
LIMIT = 1_000_000          # senior-approval limit from invoice_approval_policy.pdf
TRAIN_END, VAL_END = pd.Timestamp("2025-03-31"), pd.Timestamp("2025-06-30")

ih = pd.read_csv(RAW / "invoice_headers.csv", parse_dates=["invoice_date"])
il = pd.read_csv(RAW / "invoice_lines.csv")
pl = pd.read_csv(RAW / "purchase_order_lines.csv")
gt = pd.read_csv(GT / "invoice_anomaly_ground_truth.csv")
labels = dict(zip(gt.invoice_id, gt.anomaly_type))
po_price = pl.set_index("po_line_id").unit_price.to_dict()
po_value = pl.groupby("po_id").line_gross_amount.sum().to_dict()

# ------------------------------------------------------------------ build invoice table (one row per invoice)
lines = {k: g.copy() for k, g in il.groupby("invoice_id")}
inv = ih.copy()
inv["label"] = inv.invoice_id.map(labels).fillna("")
next_id = [int(ih.invoice_id.str[3:].astype(int).max())]


def new_id():
    next_id[0] += 1
    return f"INV{next_id[0]:07d}"


def reprice(df, factor_by_line):
    df = df.copy()
    df["invoice_unit_price"] = (df.invoice_unit_price * factor_by_line).round(2)
    df["line_net_amount"] = (df.invoiced_quantity * df.invoice_unit_price).round(2)
    df["line_tax_amount"] = (df.line_net_amount * df.tax_rate_pct / 100).round(2)
    df["line_gross_amount"] = (df.line_net_amount + df.line_tax_amount).round(2)
    return df


def scale_qty(df, f):
    df = df.copy()
    df["invoiced_quantity"] = np.maximum(1, np.round(df.invoiced_quantity * f))
    return reprice(df, 1.0)


def header_from(base, inv_id, lines_df, date, number, label):
    r = base.copy()
    r["invoice_id"], r["invoice_date"], r["supplier_invoice_number"], r["label"] = inv_id, date, number, label
    r["invoice_net_amount"] = round(lines_df.line_net_amount.sum(), 2)
    r["invoice_tax_amount"] = round(lines_df.line_tax_amount.sum(), 2)
    r["invoice_gross_amount"] = round(lines_df.line_gross_amount.sum(), 2)
    r["duplicate_of_invoice_id"] = None
    return r


clean = inv[(inv.label == "") & inv.po_id.notna()].invoice_id.tolist()
rng.shuffle(clean)
used = set()
take = lambda n: [x for x in (clean.pop() for _ in range(n)) if x not in used]
new_rows, drop_ids = [], set()

# --- benign noise 1: in-tolerance price differences on 18% of clean invoices
for iid in clean[: int(0.18 * len(clean))]:
    df = lines[iid]; f = np.ones(len(df)); f[rng.integers(0, len(df))] = 1 + rng.uniform(-0.015, 0.018)
    lines[iid] = reprice(df, f)
clean = clean[int(0.18 * len(clean)):]
hidx = inv.set_index("invoice_id")

# --- benign noise 2: legitimate partial invoicing (6% of clean POs, two bills 5-30 days apart)
for iid in take(int(0.06 * len(inv))):
    used.add(iid); base = hidx.loc[iid].copy(); base["invoice_id"] = iid
    f = rng.uniform(0.3, 0.7); a, b = scale_qty(lines[iid], f), scale_qty(lines[iid], 1 - f)
    i1, i2 = new_id(), new_id()
    d1 = base.invoice_date; d2 = d1 + pd.Timedelta(days=int(rng.integers(5, 31)))
    lines[i1], lines[i2] = a.assign(invoice_id=i1), b.assign(invoice_id=i2)
    new_rows += [header_from(base, i1, a, d1, base.supplier_invoice_number + "/1", ""),
                 header_from(base, i2, b, d2, base.supplier_invoice_number + "/2", "")]
    drop_ids.add(iid)

# --- subtle 1: SPLIT_BELOW_APPROVAL (invoices of 11-29 lakh split into 2-3 bills just under 10 lakh)
big = [i for i in clean if 1.1e6 <= hidx.loc[i].invoice_gross_amount <= 2.9e6 and i not in used]
for iid in big[:260]:
    used.add(iid); base = hidx.loc[iid].copy(); g = base.invoice_gross_amount
    k = int(np.ceil(g / (LIMIT * 0.985)))
    if k > 3: continue
    parts = rng.dirichlet(np.ones(k) * rng.choice([3, 20]))
    for j in range(k):
        nid = new_id(); df = scale_qty(lines[iid], parts[j]).assign(invoice_id=nid)
        lines[nid] = df
        new_rows.append(header_from(base, nid, df, base.invoice_date + pd.Timedelta(days=int(rng.integers(0, 7))),
                                    f"{base.supplier_invoice_number}-{j+1}", "SPLIT_BELOW_APPROVAL"))
    drop_ids.add(iid)
# --- benign look-alike: staged deliveries of big POs billed per delivery (same numbering style, close dates)
for iid in big[260:560]:
    used.add(iid); base = hidx.loc[iid].copy(); g = base.invoice_gross_amount
    if rng.random() < 0.4:   # supplier bills per truckload, sized just under the limit
        k = int(np.ceil(g / (LIMIT * 0.985))); parts = rng.dirichlet(np.ones(k) * 20)
    else:
        k = int(rng.integers(2, 4)); parts = rng.dirichlet(np.ones(k) * 4)
    d = base.invoice_date
    for j in range(k):
        nid = new_id(); df = scale_qty(lines[iid], parts[j]).assign(invoice_id=nid); lines[nid] = df
        new_rows.append(header_from(base, nid, df, d, f"{base.supplier_invoice_number}-{j+1}", ""))
        d = d + pd.Timedelta(days=int(rng.integers(0, 11)))
    drop_ids.add(iid)
clean = [i for i in clean if i not in used]

# --- subtle 2: PRICE_CREEP (8 suppliers, from a random month, 55% of their invoices, +0.8-1.9% on most lines)
sups = inv.supplier_id.value_counts().index[10:60].to_numpy()
creepers = rng.choice(sups, 8, replace=False)
start = {s: pd.Timestamp("2024-03-01") + pd.Timedelta(days=int(rng.integers(0, 480))) for s in creepers}
share = {s: rng.uniform(0.4, 0.9) for s in creepers}
for iid in clean:
    h = hidx.loc[iid]
    if h.supplier_id in start and h.invoice_date >= start[h.supplier_id] and rng.random() < 0.55:
        df = lines[iid]; f = np.where(rng.random(len(df)) < share[h.supplier_id], 1 + rng.uniform(0.005, 0.019, len(df)), 1.0)
        lines[iid] = reprice(df, f); used.add(iid)
        new_rows.append(header_from(h.copy(), iid, lines[iid], h.invoice_date, h.supplier_invoice_number, "PRICE_CREEP"))
        drop_ids.add(iid)
clean = [i for i in clean if i not in used]

# --- benign look-alike: approved monsoon freight surcharge (10 other suppliers, Jun-Sep, +0.5-1.8% on all lines)
surch = rng.choice([x for x in sups if x not in creepers], 10, replace=False)
all_year = set(surch[:4])
for iid in clean:
    h = hidx.loc[iid]
    if h.supplier_id in surch and (h.supplier_id in all_year or h.invoice_date.month in (6, 7, 8, 9)) and rng.random() < 0.5:
        df = lines[iid]; lines[iid] = reprice(df, np.where(rng.random(len(df)) < 0.8, 1 + rng.uniform(0.005, 0.018), 1.0)); used.add(iid)
        new_rows.append(header_from(h.copy(), iid, lines[iid], h.invoice_date, h.supplier_invoice_number, ""))
        drop_ids.add(iid)
clean = [i for i in clean if i not in used]


def alter(num):
    r = rng.random()
    if r < 0.35: return num + "A"
    if r < 0.6: return num.replace("/", "-", 1)
    digits = [i for i, c in enumerate(num) if c.isdigit()]
    i = digits[-2]; s = list(num); s[i], s[i + 1] = s[i + 1], s[i]
    return "".join(s) if "".join(s) != num else num + " "


fraud_rej = set()
# --- subtle 3: NEAR_DUPLICATE (resubmitted 15-60 days later, altered number, amount 0-0.4% different)
for iid in take(380):
    used.add(iid); base = hidx.loc[iid].copy(); nid = new_id()
    if rng.random() < 0.15: fraud_rej.add(iid)   # original also shows Rejected, so status alone can't clear it
    f = 1 + rng.uniform(-0.004, 0.004) if rng.random() < 0.7 else 1.0
    df = reprice(lines[iid], f).assign(invoice_id=nid); lines[nid] = df
    new_rows.append(header_from(base, nid, df, base.invoice_date + pd.Timedelta(days=int(rng.integers(15, 61))),
                                alter(base.supplier_invoice_number), "NEAR_DUPLICATE"))

# --- benign look-alike: corrected re-issue of a rejected invoice (75% have the original marked Rejected)
rejected = set()
for iid in take(320):
    used.add(iid); base = hidx.loc[iid].copy(); nid = new_id()
    if rng.random() < 0.75: rejected.add(iid)
    df = reprice(lines[iid], 1 + rng.uniform(-0.004, 0.004)).assign(invoice_id=nid); lines[nid] = df
    new_rows.append(header_from(base, nid, df, base.invoice_date + pd.Timedelta(days=int(rng.integers(5, 41))),
                                alter(base.supplier_invoice_number), ""))

inv = pd.concat([inv[~inv.invoice_id.isin(drop_ids)], pd.DataFrame(new_rows)], ignore_index=True)
inv.loc[inv.invoice_id.isin(rejected | fraud_rej), "invoice_status"] = "Rejected"
inv = inv.sort_values(["invoice_date", "invoice_id"]).reset_index(drop=True)
L = pd.concat([lines[i] for i in inv.invoice_id], ignore_index=True)
inv.drop(columns=[c for c in ["document_path"] if c in inv], inplace=True)
inv.to_csv(OUT / "invoice_headers_v2.csv", index=False)
L.to_csv(OUT / "invoice_lines_v2.csv", index=False)
inv[["invoice_id", "label"]].to_csv(OUT / "invoice_labels_v2.csv", index=False)

# ------------------------------------------------------------------ features (point-in-time)
L["po_price"] = L.po_line_id.map(po_price)
L["price_var"] = np.where(L.po_price.notna(), L.invoice_unit_price / L.po_price - 1, np.nan)
rcv = pd.read_csv(RAW / "goods_receipt_lines.csv").groupby("po_line_id").accepted_quantity.sum()
L["qty_over"] = L.invoiced_quantity - L.po_line_id.map(rcv).fillna(0)
ordered = pl.set_index("po_line_id").ordered_quantity
L["qty_over_ordered"] = L.invoiced_quantity / L.po_line_id.map(ordered) - 1
f = L.groupby("invoice_id").agg(max_var=("price_var", "max"), mean_var=("price_var", "mean"),
                                share_pos=("price_var", lambda v: float((v > 0.0005).mean())),
                                n_lines=("invoice_line_id", "size"), max_qty_over=("qty_over", "max"), max_over_ordered=("qty_over_ordered", "max"),
                                missing_po_lines=("po_line_id", lambda v: int(v.isna().sum())))
X = inv.merge(f, on="invoice_id")
X["log_gross"] = np.log1p(X.invoice_gross_amount)
X["missing_po"] = X.po_id.isna().astype(int)
X["bank_change"] = X.bank_detail_change_flag.astype(str).str.lower().eq("true").astype(int)
X["gap_to_limit"] = (LIMIT - X.invoice_gross_amount) / LIMIT
X["just_under_limit"] = ((X.invoice_gross_amount < LIMIT) & (X.invoice_gross_amount > 0.85 * LIMIT)).astype(int)

# history-based features: only invoices dated strictly earlier (or same day, lower id)
X = X.sort_values(["invoice_date", "invoice_id"]).reset_index(drop=True)
X["po_value"] = X.po_id.map(po_value)
X["prior_inv_same_po"] = X.groupby("po_id").cumcount().where(X.po_id.notna(), 0)
X["cum_billed_ratio"] = (X.groupby("po_id").invoice_gross_amount.cumsum() / X.po_value).fillna(0)
X["days_since_prev_same_po"] = X.groupby("po_id").invoice_date.diff().dt.days.fillna(-1)
X["po_cum_amount"] = X.groupby("po_id").invoice_gross_amount.cumsum().where(X.po_id.notna(), X.invoice_gross_amount)


def num_key(s):
    return "".join(c for c in str(s) if c.isalnum()).lstrip("0")


def sim_prior(group):
    seen, out = [], []
    for num, amt, st in zip(group.supplier_invoice_number, group.invoice_gross_amount, group.invoice_status):
        k = num_key(num); best = 0.0; amt_close = 0; rej = 0
        for pk, pa, ps in seen[-60:]:
            if k == pk or k[:-1] == pk or pk[:-1] == k or (len(k) == len(pk) and sum(a != b for a, b in zip(k, pk)) == 2 and sorted(k) == sorted(pk)) or k.rstrip("A") == pk:
                best = 1.0; rej = max(rej, int(ps == "Rejected"))
            if pa and abs(amt / pa - 1) < 0.005:
                amt_close = 1
        out.append((best, amt_close, rej)); seen.append((k, amt, st))
    return pd.DataFrame(out, index=group.index, columns=["num_similar_prior", "amount_match_prior", "similar_prior_rejected"])


X = X.join(X.groupby("supplier_id", group_keys=False)[["supplier_invoice_number", "invoice_gross_amount", "invoice_status"]].apply(sim_prior))
# supplier invoices in the 3 days before, and their combined value with this one
X["sup_inv_3d"], X["sup_sum_3d"] = 0, 0.0
for sid, g in X.groupby("supplier_id"):
    d = g.invoice_date.values; a = g.invoice_gross_amount.values; cs = np.cumsum(a)
    lo = np.searchsorted(d, d - np.timedelta64(3, "D"), side="left"); idx = np.arange(len(d))
    X.loc[g.index, "sup_inv_3d"] = idx - lo
    X.loc[g.index, "sup_sum_3d"] = cs - np.where(lo > 0, cs[lo - 1], 0)
X["combined_over_limit"] = ((X.sup_sum_3d > LIMIT) & (X.invoice_gross_amount < LIMIT)).astype(int)
# supplier's average price variance over the prior 120 days (point-in-time, from earlier invoices only)
X["sup_var_120d"] = 0.0
for sid, g in X.groupby("supplier_id"):
    d = g.invoice_date.values; v = g.mean_var.fillna(0).values; cs = np.concatenate([[0], np.cumsum(v)])
    lo = np.searchsorted(d, d - np.timedelta64(120, "D"), side="left"); hi = np.searchsorted(d, d, side="left")
    n = hi - lo
    X.loc[g.index, "sup_var_120d"] = np.where(n > 0, (cs[hi] - cs[lo]) / np.maximum(n, 1), 0)
X["y"] = (X.label != "").astype(int)

FEAT = ["max_over_ordered", "max_var", "mean_var", "share_pos", "n_lines", "max_qty_over", "missing_po", "bank_change", "log_gross",
        "gap_to_limit", "just_under_limit", "prior_inv_same_po", "cum_billed_ratio", "days_since_prev_same_po",
        "num_similar_prior", "amount_match_prior", "similar_prior_rejected", "sup_inv_3d", "sup_sum_3d", "combined_over_limit", "sup_var_120d"]

# ------------------------------------------------------------------ rules
dup_num = X.duplicated(["supplier_id", "supplier_invoice_number"], keep="first")
policy = ((X.max_var > 0.02) | (X.max_qty_over > 0) | (X.missing_po == 1) | (X.bank_change == 1) | dup_num).astype(int)
# best hand-written rules an auditor would add: tolerance-aware match, near-duplicate, over-billing, split and creep checks
r_match = (X.max_var > 0.02) | (X.max_over_ordered > 0.001) | (X.missing_po == 1) | (X.bank_change == 1) | dup_num
r_dup = (X.amount_match_prior == 1) & (X.num_similar_prior == 1) | (X.cum_billed_ratio > 1.01)
r_split = (X.invoice_gross_amount < LIMIT) & (((X.po_cum_amount > LIMIT) & X.days_since_prev_same_po.between(0, 7))
                                            | ((X.combined_over_limit == 1) & (X.just_under_limit == 1)))
r_creep = X.sup_var_120d > 0.006
refined = (r_match | r_dup | r_split | r_creep).astype(int)
X["rule_hits"] = r_match.astype(int) * 2 + r_dup.astype(int) + r_split.astype(int) + r_creep.astype(int)
X["rules_policy"], X["rules_refined"] = policy, refined

tr = X[X.invoice_date <= TRAIN_END]; va = X[(X.invoice_date > TRAIN_END) & (X.invoice_date <= VAL_END)]; te = X[X.invoice_date > VAL_END]
gbm = HistGradientBoostingClassifier(max_iter=400, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=40,
                                     l2_regularization=1.0, random_state=7).fit(tr[FEAT], tr.y)
te = te.assign(p=gbm.predict_proba(te[FEAT])[:, 1], p_rule=te.rule_hits + 0.01 * te.rules_policy)
va_p = gbm.predict_proba(va[FEAT])[:, 1]

subtle = {"SPLIT_BELOW_APPROVAL", "PRICE_CREEP", "NEAR_DUPLICATE"}


def metrics(df, score, k):
    y = df.y.values; s = df[score].values
    top = np.argsort(-s, kind="stable")[:k]
    return {"pr_auc": float(average_precision_score(y, s)), "roc_auc": float(roc_auc_score(y, s)),
            "precision_at_k": float(y[top].mean()), "recall_at_k": float(y[top].sum() / y.sum())}


K = int(te.y.sum())  # review capacity = number of true conditions in test
res = {name: metrics(te, col, K) for name, col in [("policy rules", "rules_policy"), ("refined rules", "p_rule"), ("model", "p")]}
for name, col in [("policy rules", "rules_policy"), ("refined rules", "rules_refined")]:
    flagged = te[col] == 1
    res[name]["flagged"] = int(flagged.sum()); res[name]["precision_flagged"] = float(te.y[flagged].mean())
    res[name]["recall_flagged"] = float(te.y[flagged].sum() / te.y.sum())
# recall by condition type: rules (flagged) vs model (top K)
topk = set(te.sort_values("p", ascending=False).invoice_id.head(K))
by_type = {}
for t, g in te[te.y == 1].groupby("label"):
    by_type[t] = {"n": len(g), "policy_rules": float(g.rules_policy.mean()), "refined_rules": float(g.rules_refined.mean()),
                  "model_top_k": float(g.invoice_id.isin(topk).mean())}
# subtle-only view: subtle positives vs all negatives
sub = te[(te.y == 0) | te.label.isin(subtle)]
res_sub = {name: float(average_precision_score(sub.y, sub[col])) for name, col in [("policy rules", "rules_policy"), ("refined rules", "p_rule"), ("model", "p")]}

rng2 = np.random.default_rng(3); d = []
for _ in range(500):
    i = rng2.integers(0, len(te), len(te)); yy = te.y.values[i]
    d.append(average_precision_score(yy, te.p.values[i]) - average_precision_score(yy, te.p_rule.values[i]))

summary = {"invoices": len(X), "test_invoices": len(te), "test_positives": int(te.y.sum()), "test_prevalence": float(te.y.mean()),
           "review_capacity_k": K, "val_pr_auc_model": float(average_precision_score(va.y, va_p)),
           "test": res, "test_subtle_only_pr_auc": res_sub, "recall_by_type": by_type,
           "model_minus_refined_pr_auc_95ci": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
           "label_counts": X.label.replace("", "CLEAN").value_counts().to_dict()}
(OUT / "invoice_v2_results.json").write_text(json.dumps(summary, indent=2))
print(json.dumps({k: summary[k] for k in ["invoices", "test_invoices", "test_positives", "review_capacity_k", "val_pr_auc_model"]}))
for n, r in res.items(): print(n, {k: round(v, 3) if isinstance(v, float) else v for k, v in r.items()})
print("subtle-only PR-AUC", {k: round(v, 3) for k, v in res_sub.items()})
for t, r in by_type.items(): print(t, {k: round(v, 3) if isinstance(v, float) else v for k, v in r.items()})
print("CI", summary["model_minus_refined_pr_auc_95ci"]); print(summary["label_counts"])
