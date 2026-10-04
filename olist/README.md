# Late deliveries cost stars: Olist SQL + Power BI case study

A PostgreSQL analysis of the public Olist Brazilian e-commerce dataset (99,441 orders, Sep 2016 – Oct 2018).

**Question:** how much does late delivery hurt customers, and where should a logistics team look first?

Case page: https://davarkk10.github.io/bikashit-portfolio/olist/

Live Power BI report (6 pages, publish to web): https://app.powerbi.com/view?r=eyJrIjoiYzdmMWViOTgtN2Q2Mi00M2YxLTgzN2EtNWJiMzdiMGQ4ZjM2IiwidCI6ImM2ZTU0OWIzLTVmNDUtNDAzMi1hYWU5LWQ0MjQ0ZGM1YjJjNCJ9
Build files and DAX: [`powerbi/`](powerbi/)

## Results

| | Late | On time or early |
|---|---|---|
| Orders (delivered, with review) | 6,381 (6.7%) | 89,443 (93.3%) |
| Average review (1–5) | 2.27 | 4.29 |
| 1–2 star reviews | 62.4% | 9.3% |

- **Dose-response:** 1–2 star share is 9–11% for early/on-time orders, 32% at 1–3 days late, 68% at 4–7 days late, ~80% beyond a week. (Q2)
- **Peak months:** late rate rose from a normal 3–6% to 12.3% (Nov 2017), 14.0% (Feb 2018) and 18.7% (Mar 2018); bad reviews rose to 17–21% in the same months. (Q3)
- **Delivery leg, not seller leg:** when the seller handed over on time, 5.3% of orders were still late; these are 72.3% of all late orders. Late handover raises the late rate to 20.7% but explains 27.7%. (Q6)
- **Lanes:** São Paulo → Rio de Janeiro (8,274 orders, 14.0% late) holds 17.7% of all late orders. The worst 10% of sellers (63 sellers, 30+ orders each) hold 15.6%. (Q5, Q8, Q10)
- **Promise padding:** the median order arrives 12 days before the promised date. (Q9)
- **Repeat buying:** customers whose first order was late bought again later 2.33% of the time vs 2.86% (z ≈ 2.5; correlation only). (Q7)

## Data checks (02_profile.sql)

- 547 orders have 2+ reviews; 789 review IDs repeat → keep the latest answered review per order.
- 8 orders are "delivered" with no delivery date → excluded from timing.
- 96,096 unique people behind 99,441 customer IDs → repeat analysis uses `customer_unique_id`.
- Payments are within R$1 of items + freight for 98,416 of 98,665 paid orders.
- Trends use Jan 2017 – Aug 2018 (edge months are thin).
- **Late** = delivered on a later calendar day than `order_estimated_delivery_date`.

## Reproduce

```bash
# Kaggle: olistbr/brazilian-ecommerce (plain .csv or .csv.gz both work)
export DATA=/path/to/olist_csvs PGURL=postgresql://postgres@localhost/postgres
olist/sql/load.sh                          # schema + load 8 CSVs + views (~10 s)
psql "$PGURL" -f olist/sql/02_profile.sql  # data checks
olist/sql/export.sh                        # Q1–Q10 → olist/results/*.csv
```

| File | Contents |
|---|---|
| `sql/00_schema.sql` | 8 tables (geolocation not used) |
| `sql/01_views.sql` | `order_review` (one review per order), `delivered` (timing + review), `order_value`, `order_seller` |
| `sql/02_profile.sql` | Row counts, duplicates, payment reconciliation, month coverage |
| `sql/03_late_vs_reviews.sql` | Q1–Q3 |
| `sql/04_where_and_who.sql` | Q4–Q6 |
| `sql/05_impact_and_lanes.sql` | Q7–Q10 |
| `results/*.csv` | Saved output of every query |

## MySQL version

`mysql/` holds the same project for MySQL 8 (Workbench): schema, `LOAD DATA LOCAL INFILE` loader, data checks, views and Q1–Q10. It returns the same results; Q5 and Q7 break ties explicitly so both databases agree.

## Limits

Correlation, not cause; Brazil 2016–2018 only; no carrier field in the data; review analysis covers orders with a review (95,824 of 96,478 delivered). Lane and seller queries count a two-seller order once per seller.

## Licence

Data: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), CC BY-NC-SA 4.0. Raw data is not redistributed here.
