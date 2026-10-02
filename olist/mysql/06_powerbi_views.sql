-- MySQL 8: views that Power BI imports. Run after 04_views.sql.
USE olist_db;

-- 1. One row per delivered order: the main fact table
CREATE OR REPLACE VIEW pbi_delivery AS
SELECT d.order_id,
       d.customer_unique_id,
       d.customer_state,
       DATE(d.purchased_at)                        AS purchase_date,
       DATE(d.handed_to_carrier_at)                AS handover_date,
       DATE(d.delivered_at)                        AS delivered_date,
       DATE(d.promised_at)                         AS promised_date,
       d.days_vs_promise,
       DATEDIFF(d.delivered_at, d.purchased_at)    AS days_to_deliver,
       DATEDIFF(d.promised_at, d.purchased_at)     AS days_promised,
       CAST(d.is_late AS SIGNED)                   AS is_late,
       CASE WHEN d.days_vs_promise <= -7 THEN '7+ days early'
            WHEN d.days_vs_promise <= 0  THEN '0-6 days early'
            WHEN d.days_vs_promise <= 3  THEN '1-3 days late'
            WHEN d.days_vs_promise <= 7  THEN '4-7 days late'
            WHEN d.days_vs_promise <= 14 THEN '8-14 days late'
            ELSE '15+ days late' END               AS delay_bucket,
       CASE WHEN d.days_vs_promise <= -7 THEN 1
            WHEN d.days_vs_promise <= 0  THEN 2
            WHEN d.days_vs_promise <= 3  THEN 3
            WHEN d.days_vs_promise <= 7  THEN 4
            WHEN d.days_vs_promise <= 14 THEN 5
            ELSE 6 END                             AS delay_bucket_order,
       d.review_score,
       v.items_value,
       v.freight_value,
       v.order_value
FROM delivered d
LEFT JOIN order_value v ON v.order_id = d.order_id;

-- 2. One row per order-seller pair: for seller and lane analysis
CREATE OR REPLACE VIEW pbi_order_seller AS
SELECT os.order_id,
       os.seller_id,
       DATE(os.ship_by) AS ship_by_date,
       CASE WHEN d.handed_to_carrier_at IS NULL THEN NULL
            WHEN d.handed_to_carrier_at > os.ship_by THEN 1 ELSE 0 END AS seller_late_handover
FROM order_seller os
JOIN delivered d ON d.order_id = os.order_id;

-- 3. Sellers, with each seller's all-time late-rate decile (sellers with 30+ delivered orders; 1 = worst)
CREATE OR REPLACE VIEW pbi_seller AS
WITH s AS (
  SELECT os.seller_id, COUNT(*) AS orders, SUM(d.is_late) AS late_orders
  FROM order_seller os JOIN delivered d ON d.order_id = os.order_id
  GROUP BY os.seller_id HAVING COUNT(*) >= 30),
ranked AS (
  SELECT seller_id, NTILE(10) OVER (ORDER BY late_orders / orders DESC, seller_id) AS late_decile
  FROM s)
SELECT se.seller_id, se.seller_city, se.seller_state, r.late_decile
FROM sellers se LEFT JOIN ranked r ON r.seller_id = se.seller_id;

-- 4. One row per customer (person): first delivered order and whether they came back
CREATE OR REPLACE VIEW pbi_first_order AS
WITH person_orders AS (
  SELECT c.customer_unique_id, o.order_id,
         MAX(o.order_purchase_timestamp) OVER (PARTITION BY c.customer_unique_id) AS last_purchase
  FROM orders o JOIN customers c ON c.customer_id = o.customer_id),
ranked AS (
  SELECT d.customer_unique_id, d.order_id, d.is_late, d.purchased_at, p.last_purchase,
         ROW_NUMBER() OVER (PARTITION BY d.customer_unique_id ORDER BY d.purchased_at, d.order_id) AS rn
  FROM delivered d JOIN person_orders p ON p.order_id = d.order_id)
SELECT customer_unique_id,
       order_id AS first_order_id,
       CAST(is_late AS SIGNED) AS first_order_late,
       CAST(last_purchase > purchased_at AS SIGNED) AS came_back
FROM ranked
WHERE rn = 1;
