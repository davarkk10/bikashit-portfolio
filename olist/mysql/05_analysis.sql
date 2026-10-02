-- MySQL 8: Q1-Q10. Same results as the PostgreSQL version (Q9 median uses ROW_NUMBER, since MySQL has no PERCENTILE_CONT).
USE olist_db;

-- Q1
SELECT CASE WHEN is_late THEN 'late' ELSE 'on time or early' END AS delivery,
       COUNT(*) AS orders,
       ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_orders,
       ROUND(AVG(review_score), 2) AS avg_review,
       ROUND(100 * AVG(review_score <= 2), 1) AS pct_1_2_star
FROM delivered
WHERE review_score IS NOT NULL
GROUP BY delivery
ORDER BY delivery;

-- Q2
SELECT CASE WHEN days_vs_promise <= -7 THEN '1. 7+ days early'
            WHEN days_vs_promise <= 0  THEN '2. 0-6 days early'
            WHEN days_vs_promise <= 3  THEN '3. 1-3 days late'
            WHEN days_vs_promise <= 7  THEN '4. 4-7 days late'
            WHEN days_vs_promise <= 14 THEN '5. 8-14 days late'
            ELSE '6. 15+ days late' END AS bucket,
       COUNT(*) AS orders,
       ROUND(AVG(review_score), 2) AS avg_review,
       ROUND(100 * AVG(review_score <= 2), 1) AS pct_1_2_star
FROM delivered
WHERE review_score IS NOT NULL
GROUP BY bucket
ORDER BY bucket;

-- Q3
SELECT purchase_month,
       COUNT(*) AS delivered_orders,
       ROUND(100 * AVG(is_late), 1) AS late_pct,
       ROUND(100 * AVG(review_score <= 2), 1) AS pct_1_2_star
FROM delivered
WHERE purchase_month BETWEEN '2017-01-01' AND '2018-08-01'
  AND review_score IS NOT NULL
GROUP BY purchase_month
ORDER BY purchase_month;

-- Q4
SELECT customer_state,
       COUNT(*) AS orders,
       ROUND(100 * AVG(is_late), 1) AS late_pct,
       ROUND(AVG(DATEDIFF(delivered_at, purchased_at)), 1) AS avg_days_to_deliver
FROM delivered
GROUP BY customer_state
HAVING COUNT(*) >= 1000
ORDER BY AVG(is_late) DESC;

-- Q5
WITH s AS (
  SELECT os.seller_id,
         COUNT(*) AS orders,
         SUM(d.is_late) AS late_orders
  FROM order_seller os
  JOIN delivered d ON d.order_id = os.order_id
  GROUP BY os.seller_id
  HAVING COUNT(*) >= 30),
ranked AS (
  SELECT s.*,
         NTILE(10) OVER (ORDER BY late_orders / orders DESC, seller_id) AS decile
  FROM s)
SELECT decile,
       COUNT(*) AS sellers,
       SUM(orders) AS orders,
       SUM(late_orders) AS late_orders,
       ROUND(100 * SUM(late_orders) / SUM(orders), 1) AS late_pct,
       ROUND(100 * SUM(late_orders) / SUM(SUM(late_orders)) OVER (), 1) AS share_of_all_late
FROM ranked
GROUP BY decile
ORDER BY decile;

-- Q6
WITH x AS (
  SELECT d.order_id, d.is_late,
         d.handed_to_carrier_at > os.ship_by AS seller_late_handover
  FROM delivered d
  JOIN order_seller os ON os.order_id = d.order_id
  WHERE d.handed_to_carrier_at IS NOT NULL)
SELECT CASE WHEN seller_late_handover THEN 'seller handed over late'
            ELSE 'seller on time' END AS seller_leg,
       COUNT(*) AS orders,
       ROUND(100 * AVG(is_late), 1) AS customer_late_pct,
       ROUND(100 * SUM(is_late) / SUM(SUM(is_late)) OVER (), 1) AS share_of_late_orders
FROM x
GROUP BY seller_leg
ORDER BY seller_leg;

-- Q7
WITH person_orders AS (
  SELECT c.customer_unique_id, o.order_id,
         MAX(o.order_purchase_timestamp) OVER (PARTITION BY c.customer_unique_id) AS last_purchase
  FROM orders o
  JOIN customers c ON c.customer_id = o.customer_id),
ranked AS (
  SELECT d.customer_unique_id, d.is_late, d.purchased_at, p.last_purchase,
         ROW_NUMBER() OVER (PARTITION BY d.customer_unique_id
                            ORDER BY d.purchased_at, d.order_id) AS rn
  FROM delivered d
  JOIN person_orders p ON p.order_id = d.order_id)
SELECT CASE WHEN is_late THEN 'first order late' ELSE 'first order on time' END AS first_order,
       COUNT(*) AS customers,
       SUM(last_purchase > purchased_at) AS came_back,
       ROUND(100 * AVG(last_purchase > purchased_at), 2) AS repeat_pct
FROM ranked
WHERE rn = 1
GROUP BY first_order
ORDER BY first_order;

-- Q8
SELECT CONCAT(s.seller_state, ' -> ', d.customer_state) AS lane,
       COUNT(*) AS orders,
       ROUND(100 * AVG(d.is_late), 1) AS late_pct,
       ROUND(AVG(DATEDIFF(d.delivered_at, d.purchased_at)), 1) AS avg_days,
       ROUND(AVG(DATEDIFF(d.promised_at, d.purchased_at)), 1) AS avg_days_promised
FROM delivered d
JOIN order_seller os ON os.order_id = d.order_id
JOIN sellers s ON s.seller_id = os.seller_id
GROUP BY lane
HAVING COUNT(*) >= 300
ORDER BY AVG(d.is_late) DESC
LIMIT 10;

-- Q9a median
WITH r AS (
  SELECT -days_vs_promise AS days_early,
         ROW_NUMBER() OVER (ORDER BY -days_vs_promise) AS rn,
         COUNT(*) OVER () AS n
  FROM delivered)
SELECT ROUND(AVG(days_early), 0) AS median_days_early
FROM r
WHERE rn IN (FLOOR((n + 1) / 2), CEIL((n + 1) / 2));

-- Q9b value
SELECT ROUND(SUM(CASE WHEN d.is_late THEN v.order_value END) / 1000000, 2) AS late_value_mn_brl,
       ROUND(100 * SUM(CASE WHEN d.is_late THEN v.order_value END) / SUM(v.order_value), 1) AS late_share_of_value_pct
FROM delivered d
JOIN order_value v ON v.order_id = d.order_id;

-- Q10
SELECT ROUND(100 * SUM(s.seller_state = 'SP' AND d.customer_state = 'RJ' AND d.is_late)
             / SUM(d.is_late), 1) AS sp_rj_share_of_late,
       ROUND(100 * SUM(d.customer_state IN ('MA','PI','CE','RN','PB','PE','AL','SE','BA',
                                            'PA','AM','AP','RR','RO','AC','TO') AND d.is_late)
             / SUM(d.is_late), 1) AS north_northeast_share_of_late,
       ROUND(100 * AVG(d.customer_state IN ('MA','PI','CE','RN','PB','PE','AL','SE','BA',
                                            'PA','AM','AP','RR','RO','AC','TO')), 1) AS north_northeast_share_of_orders
FROM delivered d
JOIN order_seller os ON os.order_id = d.order_id
JOIN sellers s ON s.seller_id = os.seller_id;
