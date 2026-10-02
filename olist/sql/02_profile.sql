-- Profiling: row counts, coverage, keys and known quirks, before any analysis.
SET search_path = olist;

-- 1. Row counts per table
SELECT 'orders' AS tbl, COUNT(*) FROM orders UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'customers', COUNT(*) FROM customers UNION ALL SELECT 'sellers', COUNT(*) FROM sellers
UNION ALL SELECT 'products', COUNT(*) FROM products UNION ALL SELECT 'order_payments', COUNT(*) FROM order_payments
UNION ALL SELECT 'order_reviews', COUNT(*) FROM order_reviews;

-- 2. Order status mix and date range
SELECT order_status, COUNT(*) AS orders, MIN(order_purchase_timestamp)::date AS first, MAX(order_purchase_timestamp)::date AS last
FROM orders GROUP BY order_status ORDER BY orders DESC;

-- 3. Delivered orders missing a delivery date (excluded from delivery analysis)
SELECT COUNT(*) AS delivered_without_date FROM orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NULL;

-- 4. Review quirks: orders with more than one review; duplicated review_id
SELECT (SELECT COUNT(*) FROM (SELECT order_id FROM order_reviews GROUP BY order_id HAVING COUNT(*) > 1) x) AS orders_with_2plus_reviews,
       (SELECT COUNT(*) FROM (SELECT review_id FROM order_reviews GROUP BY review_id HAVING COUNT(*) > 1) y) AS duplicated_review_ids;

-- 5. Customers: one person can have many customer_id values (one per order); customer_unique_id is the person
SELECT COUNT(DISTINCT customer_id) AS customer_ids, COUNT(DISTINCT customer_unique_id) AS people FROM customers;

-- 6. Monthly volume: thin months at the edges are excluded from trends
SELECT date_trunc('month', order_purchase_timestamp)::date AS month, COUNT(*) AS orders FROM orders GROUP BY 1 ORDER BY 1;

-- 7. Reconciliation: payments vs items + freight per order (should match for almost all orders)
SELECT COUNT(*) AS orders_compared,
       SUM(CASE WHEN ABS(p.paid - v.order_value) <= 1 THEN 1 ELSE 0 END) AS within_1_real
FROM (SELECT order_id, SUM(payment_value) AS paid FROM order_payments GROUP BY order_id) p
JOIN order_value v USING (order_id);
