"""ProcureAI v3 corpus: add real-world delivery drivers and re-simulate delivery outcomes.

Keeps every master, contract and PO from the seed-20260927 corpus unchanged. Adds the
data a procurement team could actually hold at order time, then redraws each PO's
receipt date from a delay process that depends on those drivers plus noise nobody
can observe.

New observable tables (written to <out>/):
  supplier_lanes.csv         supplier -> warehouse road distance, route, quoted transit
  supplier_capacity.csv      how many POs a supplier can handle in 30 days
  region_flood_risk.csv      monthly flood / corridor disruption climatology (published history)
  festival_calendar.csv      Bohag Bihu, Durga Puja, Diwali freight slowdown windows
  goods_receipt_headers.csv  re-simulated receipt dates
Hidden (for the ceiling only):
  ground_truth/disruption_events.csv, ground_truth/delay_probability.csv

Usage: python enrich_delivery_drivers.py <original data/raw> <out dir>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAW, OUT = Path(sys.argv[1]), Path(sys.argv[2])
(OUT / "ground_truth").mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(20261014)

ph = pd.read_csv(RAW / "purchase_order_headers.csv", parse_dates=["order_date", "promised_delivery_date"])
pl = pd.read_csv(RAW / "purchase_order_lines.csv")
rh = pd.read_csv(RAW / "goods_receipt_headers.csv")
sup = pd.read_csv(RAW / "suppliers.csv")
wh = pd.read_csv(RAW / "warehouses.csv")

# ------------------------------------------------------------------ 1. lanes: distance and route
CITY = {"Guwahati": (26.14, 91.74), "Kolkata": (22.57, 88.36), "Siliguri": (26.73, 88.40),
        "Dibrugarh": (27.47, 94.91), "Jorhat": (26.75, 94.20), "Delhi": (28.61, 77.21),
        "Mumbai": (19.08, 72.88), "Bengaluru": (12.97, 77.59), "Hyderabad": (17.39, 78.49),
        "Ahmedabad": (23.02, 72.57), "Jaipur": (26.91, 75.79), "Chennai": (13.08, 80.27)}
NE = {"Guwahati", "Dibrugarh", "Jorhat"}


def km(a, b):
    la1, lo1, la2, lo2 = map(np.radians, (a[0], a[1], b[0], b[1]))
    h = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(h))


processing = dict(zip(sup.supplier_id, rng.integers(3, 9, len(sup))))  # supplier's own dispatch days
lanes = []
for s in sup.itertuples():
    for w in wh.itertuples():
        road = round(km(CITY[s.city], (w.latitude, w.longitude)) * 1.35 + 15, 0)
        via = "Local NE" if s.city in NE else "Via Siliguri corridor"
        transit = int(np.ceil(1 + road / 380))
        lanes.append((s.supplier_id, w.warehouse_id, road, via, transit, transit + processing[s.supplier_id]))
lanes = pd.DataFrame(lanes, columns=["supplier_id", "warehouse_id", "road_distance_km", "route_type",
                                     "typical_transit_days", "quoted_lead_time_days"])
lanes.to_csv(OUT / "supplier_lanes.csv", index=False)

# ------------------------------------------------------------------ 2. flood climatology (published, known in advance)
RISK = {  # weekly probability of a disruptive flood / blockade, by month (Jun-Sep peak)
    "Brahmaputra upper": [.00, .00, .01, .03, .08, .22, .30, .26, .15, .04, .01, .00],   # Dibrugarh, Tinsukia, Jorhat
    "Brahmaputra lower": [.00, .00, .01, .02, .05, .15, .22, .18, .10, .03, .00, .00],   # Guwahati, Tezpur
    "Barak valley":      [.00, .00, .02, .04, .10, .20, .18, .14, .08, .03, .00, .00],   # Silchar
    "Siliguri corridor": [.00, .00, .00, .01, .03, .10, .16, .14, .08, .02, .00, .00],   # NH-10/NH-27 landslides
}
WH_REGION = {"WH001": "Brahmaputra lower", "WH002": "Brahmaputra upper", "WH003": "Brahmaputra upper",
             "WH004": "Brahmaputra upper", "WH005": "Barak valley", "WH006": "Brahmaputra lower"}
pd.DataFrame([(r, m + 1, p) for r, ps in RISK.items() for m, p in enumerate(ps)],
             columns=["region", "month", "weekly_disruption_probability"]).to_csv(OUT / "region_flood_risk.csv", index=False)
pd.DataFrame(list(WH_REGION.items()), columns=["warehouse_id", "region"]).to_csv(OUT / "warehouse_regions.csv", index=False)

# realised events: one draw per region-week (hidden from the model)
weeks = pd.date_range("2023-12-25", "2026-03-30", freq="W-MON")
events = [(r, wk) for r in RISK for wk in weeks if rng.random() < RISK[r][wk.month - 1]]
ev = pd.DataFrame(events, columns=["region", "week_start"])
ev.to_csv(OUT / "ground_truth" / "disruption_events.csv", index=False)
ev_set = set(zip(ev.region, ev.week_start))

# ------------------------------------------------------------------ 3. festival calendar (public)
fest = pd.DataFrame([
    ("Bohag Bihu", "2024-04-10", "2024-04-21"), ("Durga Puja", "2024-10-05", "2024-10-16"),
    ("Diwali", "2024-10-27", "2024-11-05"), ("Bohag Bihu", "2025-04-10", "2025-04-21"),
    ("Durga Puja", "2025-09-24", "2025-10-05"), ("Diwali", "2025-10-16", "2025-10-25"),
], columns=["festival", "slowdown_start", "slowdown_end"])
fest.to_csv(OUT / "festival_calendar.csv", index=False)
fs = [(pd.Timestamp(a), pd.Timestamp(b)) for a, b in zip(fest.slowdown_start, fest.slowdown_end)]

# ------------------------------------------------------------------ 4. supplier capacity and load
po = ph.merge(pl.groupby("po_id").ordered_quantity.sum().rename("order_qty"), on="po_id")
po = po.merge(sup[["supplier_id", "base_reliability"]], on="supplier_id")
po = po.merge(lanes, on=["supplier_id", "warehouse_id"]).sort_values(["order_date", "po_id"]).reset_index(drop=True)
# orders placed with the same supplier in the 30 days before (observable from the PO table itself)
po["orders_prev_30d"] = 0
for sid, g in po.groupby("supplier_id"):
    d = g.order_date.values
    po.loc[g.index, "orders_prev_30d"] = np.arange(len(d)) - np.searchsorted(d, d - np.timedelta64(30, "D"), side="left")
typical = po.groupby("supplier_id").orders_prev_30d.median()
cap = pd.DataFrame({"supplier_id": typical.index,
                    "capacity_pos_per_30d": np.maximum(3, np.round(typical.values * rng.uniform(0.7, 1.15, len(typical))))})
cap.to_csv(OUT / "supplier_capacity.csv", index=False)
po = po.merge(cap, on="supplier_id")
po["utilisation"] = po.orders_prev_30d / po.capacity_pos_per_30d
po["qty_ratio"] = po.order_qty / po.groupby("supplier_id").order_qty.transform("median")
po["promised_lead"] = (po.promised_delivery_date - po.order_date).dt.days
po["tightness"] = (po.quoted_lead_time_days - po.promised_lead) / po.quoted_lead_time_days

# ------------------------------------------------------------------ 5. delivery physics (v4)
# receipt = actual dispatch + actual transit. Lateness is no longer a coin flip: it comes from
# (a) the supplier dispatching late and (b) the truck being held up on the road.
def wk(d):
    return d - pd.to_timedelta(d.dt.weekday, unit="D")

planned = po.order_date + pd.to_timedelta(po.quoted_lead_time_days - po.typical_transit_days, unit="D")
fest_dispatch = np.zeros(len(po), bool)
for a, b in fs:
    fest_dispatch |= (planned >= a) & (planned <= b)

# (a) supplier-side dispatch slip
s = (-0.9 + 3.0 * (0.75 - po.base_reliability) + 1.3 * np.clip(po.utilisation - 1.0, -0.5, 1.5)
     + 0.45 * np.log(np.clip(po.qty_ratio, 0.2, 5)) + 0.75 * fest_dispatch + rng.normal(0, 0.5, len(po)))
slips = rng.random(len(po)) < 1 / (1 + np.exp(-s))
slip = np.where(slips, np.ceil(rng.gamma(2.0, 2.0 + 3.0 * np.clip(s, 0, None), len(po))), 0).astype(int)
dispatch = planned + pd.to_timedelta(slip, unit="D")

# (b) road transit: typical days, small jitter, plus flood / corridor hold-ups in the arrival week
arrive_wk = wk(dispatch + pd.to_timedelta(po.typical_transit_days, unit="D"))
dest_hit = np.array([(WH_REGION[w], t) in ev_set for w, t in zip(po.warehouse_id, arrive_wk)])
corr_hit = np.array([v == "Via Siliguri corridor" and ("Siliguri corridor", t) in ev_set for v, t in zip(po.route_type, arrive_wk)])
transit = (po.typical_transit_days + rng.integers(-1, 3, len(po))
           + np.where(dest_hit, rng.integers(3, 10, len(po)), 0) + np.where(corr_hit, rng.integers(2, 7, len(po)), 0))
receipt = dispatch + pd.to_timedelta(transit, unit="D")
late = (receipt > po.promised_delivery_date).values

po["receipt_date"] = np.minimum(receipt, pd.Timestamp("2026-02-14"))
new_rh = rh.drop(columns="receipt_date").merge(po[["po_id", "receipt_date"]], on="po_id")[rh.columns]
new_rh["receipt_date"] = new_rh.receipt_date.dt.date
new_rh.to_csv(OUT / "goods_receipt_headers.csv", index=False)
pd.DataFrame({"po_id": po.po_id, "planned_dispatch_date": planned.dt.date, "actual_dispatch_date": dispatch.dt.date}).to_csv(
    OUT / "asn_dispatch.csv", index=False)

# ------------------------------------------------------------------ 6. disruption advisories (as v3)
adv = []
for e in ev.itertuples():
    if rng.random() < 0.8:
        adv.append((e.region, e.week_start - pd.Timedelta(days=int(rng.integers(2, 8))), e.week_start))
for r in RISK:
    for w in weeks:
        if (r, w) not in ev_set and rng.random() < RISK[r][w.month - 1] * 0.35:
            adv.append((r, w - pd.Timedelta(days=int(rng.integers(2, 8))), w))
pd.DataFrame(adv, columns=["region", "issued_date", "covers_week_start"]).sort_values("issued_date").to_csv(
    OUT / "disruption_advisories.csv", index=False)
# no closed-form ceiling in v4; placeholder columns keep the training script's interface
pd.DataFrame({"po_id": po.po_id, "p_late_true": np.nan, "p_late_order_time_ceiling": np.nan,
              "p_late_prearrival_upper_bound": np.nan}).to_csv(OUT / "ground_truth" / "delay_probability.csv", index=False)

slack = (po.promised_delivery_date - planned).dt.days - po.typical_transit_days
print(f"late rate {late.mean():.3f}  slipped {slips.mean():.3f}  median slip if slipped {np.median(slip[slips]):.0f}d  "
      f"median slack {slack.median():.0f}d  flood-hit {dest_hit.mean():.3f}")
