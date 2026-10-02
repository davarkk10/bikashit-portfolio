-- Q7-Q9: What does lateness cost, which routes are worst, and are delivery promises set well?
SET search_path = olist;

-- Q7. Do customers come back? First delivered order late vs on time -> bought again at a later time
--     (strictly later: a few people placed two orders at the same second, which is one checkout, not a return visit)
WITH person_orders AS (
  SELECT c.customer_unique_id, o.order_id,
         MAX(o.order_purchase_timestamp) OVER (PARTITION BY c.customer_unique_id) AS last_purchase
  FROM orders o JOIN customers c USING (customer_id)),
firsts AS (
  SELECT DISTINCT ON (d.customer_unique_id) d.customer_unique_id, d.is_late, d.purchased_at, p.last_purchase
  FROM delivered d JOIN person_orders p USING (order_id)
  ORDER BY d.customer_unique_id, d.purchased_at, d.order_id)
SELECT CASE WHEN is_late THEN 'first order late' ELSE 'first order on time' END AS first_order,
       COUNT(*) AS customers,
       SUM((last_purchase > purchased_at)::int) AS came_back,
       ROUND(100.0 * AVG((last_purchase > purchased_at)::int), 2) AS repeat_pct
FROM firsts GROUP BY 1 ORDER BY 1;

-- Q8. Worst seller-state -> customer-state lanes (300+ delivered orders)
SELECT s.seller_state || ' -> ' || d.customer_state AS lane,
       COUNT(*) AS orders,
       ROUND(100.0 * AVG(d.is_late::int), 1) AS late_pct,
       ROUND(AVG(d.delivered_at::date - d.purchased_at::date), 1) AS avg_days,
       ROUND(AVG(d.promised_at::date - d.purchased_at::date), 1) AS avg_days_promised
FROM delivered d JOIN order_seller os USING (order_id) JOIN sellers s USING (seller_id)
GROUP BY 1 HAVING COUNT(*) >= 300 ORDER BY late_pct DESC LIMIT 10;

-- Q9. Promise padding: how early do on-time orders arrive vs the promise (median), and value at stake
SELECT ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY -days_vs_promise)::numeric, 0) AS median_days_early_all,
       ROUND(SUM(v.order_value) FILTER (WHERE is_late) / 1e6, 2) AS late_order_value_mn_brl,
       ROUND(100.0 * SUM(v.order_value) FILTER (WHERE is_late) / SUM(v.order_value), 1) AS late_share_of_value_pct
FROM delivered d JOIN order_value v USING (order_id);

-- Q10. How much of all lateness sits on the SP -> RJ lane and in the North/Northeast?
SELECT ROUND(100.0 * SUM((s.seller_state = 'SP' AND d.customer_state = 'RJ' AND d.is_late)::int) / SUM(d.is_late::int), 1) AS sp_rj_share_of_late,
       ROUND(100.0 * SUM((d.customer_state IN ('MA','PI','CE','RN','PB','PE','AL','SE','BA','PA','AM','AP','RR','RO','AC','TO') AND d.is_late)::int) / SUM(d.is_late::int), 1) AS north_northeast_share_of_late,
       ROUND(100.0 * AVG((d.customer_state IN ('MA','PI','CE','RN','PB','PE','AL','SE','BA','PA','AM','AP','RR','RO','AC','TO'))::int), 1) AS north_northeast_share_of_orders
FROM delivered d JOIN order_seller os USING (order_id) JOIN sellers s USING (seller_id);
