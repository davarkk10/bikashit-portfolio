-- MySQL 8: the four clean views. ROW_NUMBER() replaces PostgreSQL DISTINCT ON.
USE olist_db;

CREATE OR REPLACE VIEW order_review AS
SELECT order_id, review_score, review_creation_date
FROM (
  SELECT order_id, review_score, review_creation_date,
         ROW_NUMBER() OVER (PARTITION BY order_id
                            ORDER BY review_answer_timestamp DESC, review_id) AS rn
  FROM order_reviews
) ranked
WHERE rn = 1;

CREATE OR REPLACE VIEW delivered AS
SELECT o.order_id, o.customer_id, c.customer_unique_id, c.customer_state,
       o.order_purchase_timestamp AS purchased_at,
       DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m-01') AS purchase_month,
       o.order_delivered_carrier_date AS handed_to_carrier_at,
       o.order_delivered_customer_date AS delivered_at,
       o.order_estimated_delivery_date AS promised_at,
       DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) AS days_vs_promise,
       DATE(o.order_delivered_customer_date) > DATE(o.order_estimated_delivery_date) AS is_late,
       r.review_score
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
LEFT JOIN order_review r ON r.order_id = o.order_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL;

CREATE OR REPLACE VIEW order_value AS
SELECT order_id,
       SUM(price) AS items_value,
       SUM(freight_value) AS freight_value,
       SUM(price + freight_value) AS order_value
FROM order_items
GROUP BY order_id;

CREATE OR REPLACE VIEW order_seller AS
SELECT order_id, seller_id, MAX(shipping_limit_date) AS ship_by
FROM order_items
GROUP BY order_id, seller_id;
