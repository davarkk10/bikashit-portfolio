-- MySQL 8: data checks before analysis.
USE olist_db;

SELECT order_status, COUNT(*) AS orders,
       DATE(MIN(order_purchase_timestamp)) AS first,
       DATE(MAX(order_purchase_timestamp)) AS last
FROM orders
GROUP BY order_status
ORDER BY orders DESC;

SELECT COUNT(*) AS delivered_without_date
FROM orders
WHERE order_status = 'delivered' AND order_delivered_customer_date IS NULL;

SELECT
  (SELECT COUNT(*) FROM (SELECT order_id FROM order_reviews
                         GROUP BY order_id HAVING COUNT(*) > 1) x) AS orders_with_2plus_reviews,
  (SELECT COUNT(*) FROM (SELECT review_id FROM order_reviews
                         GROUP BY review_id HAVING COUNT(*) > 1) y) AS duplicated_review_ids;

SELECT COUNT(DISTINCT customer_id) AS customer_ids,
       COUNT(DISTINCT customer_unique_id) AS people
FROM customers;

SELECT DATE_FORMAT(order_purchase_timestamp, '%Y-%m') AS month, COUNT(*) AS orders
FROM orders
GROUP BY month
ORDER BY month;

SELECT COUNT(*) AS orders_compared,
       SUM(ABS(p.paid - v.order_value) <= 1) AS within_1_real
FROM (SELECT order_id, SUM(payment_value) AS paid
      FROM order_payments GROUP BY order_id) p
JOIN (SELECT order_id, SUM(price + freight_value) AS order_value
      FROM order_items GROUP BY order_id) v
  USING (order_id);
