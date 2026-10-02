-- Q4-Q6: Where does lateness concentrate, and is it the seller or the delivery leg?
SET search_path = olist;

-- Q4. Customer states: late rate (states with 1,000+ delivered orders)
SELECT customer_state, COUNT(*) AS orders,
       ROUND(100.0 * AVG(is_late::int), 1) AS late_pct,
       ROUND(AVG(delivered_at::date - purchased_at::date), 1) AS avg_days_to_deliver
FROM delivered GROUP BY 1 HAVING COUNT(*) >= 1000 ORDER BY late_pct DESC;

-- Q5. Seller concentration: what share of late orders comes from the worst 10% of sellers?
--     (sellers with 30+ delivered orders; an order with two sellers counts for both)
WITH s AS (
  SELECT os.seller_id, COUNT(*) AS orders, SUM(d.is_late::int) AS late_orders
  FROM order_seller os JOIN delivered d USING (order_id)
  GROUP BY 1 HAVING COUNT(*) >= 30),
ranked AS (
  SELECT *, late_orders::numeric / orders AS late_rate,
         NTILE(10) OVER (ORDER BY late_orders::numeric / orders DESC, seller_id) AS decile  -- seller_id breaks ties so deciles are repeatable
  FROM s)
SELECT decile, COUNT(*) AS sellers, SUM(orders) AS orders, SUM(late_orders) AS late_orders,
       ROUND(100.0 * SUM(late_orders) / SUM(orders), 1) AS late_pct,
       ROUND(100.0 * SUM(late_orders) / SUM(SUM(late_orders)) OVER (), 1) AS share_of_all_late
FROM ranked GROUP BY decile ORDER BY decile;

-- Q6. Seller leg vs delivery leg: did the seller hand over after the shipping deadline,
--     and how often is the order still late when the seller was on time?
WITH x AS (
  SELECT d.order_id, d.is_late,
         (d.handed_to_carrier_at > os.ship_by) AS seller_late_handover
  FROM delivered d JOIN order_seller os USING (order_id)
  WHERE d.handed_to_carrier_at IS NOT NULL)
SELECT CASE WHEN seller_late_handover THEN 'seller handed over late' ELSE 'seller on time' END AS seller_leg,
       COUNT(*) AS orders,
       ROUND(100.0 * AVG(is_late::int), 1) AS customer_late_pct,
       ROUND(100.0 * SUM(is_late::int) / SUM(SUM(is_late::int)) OVER (), 1) AS share_of_late_orders
FROM x GROUP BY 1 ORDER BY 1;
