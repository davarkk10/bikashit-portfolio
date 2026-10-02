SET search_path = olist;

-- One review per order: some orders have several reviews; keep the most recently answered one.
CREATE OR REPLACE VIEW order_review AS
SELECT DISTINCT ON (order_id) order_id, review_score, review_creation_date
FROM order_reviews
ORDER BY order_id, review_answer_timestamp DESC NULLS LAST, review_id;

-- Delivered orders with a known delivery date: the population for every delivery question.
-- "Late" = delivered to the customer after the estimated date shown at purchase (calendar days).
CREATE OR REPLACE VIEW delivered AS
SELECT o.order_id, o.customer_id, c.customer_unique_id, c.customer_state,
       o.order_purchase_timestamp AS purchased_at,
       date_trunc('month', o.order_purchase_timestamp)::date AS purchase_month,
       o.order_delivered_carrier_date AS handed_to_carrier_at,
       o.order_delivered_customer_date AS delivered_at,
       o.order_estimated_delivery_date AS promised_at,
       (o.order_delivered_customer_date::date - o.order_estimated_delivery_date::date) AS days_vs_promise,
       (o.order_delivered_customer_date::date > o.order_estimated_delivery_date::date) AS is_late,
       r.review_score
FROM orders o
JOIN customers c USING (customer_id)
LEFT JOIN order_review r USING (order_id)
WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL;

-- Order value (items + freight) per order.
CREATE OR REPLACE VIEW order_value AS
SELECT order_id, SUM(price) AS items_value, SUM(freight_value) AS freight_value, SUM(price + freight_value) AS order_value
FROM order_items GROUP BY order_id;

-- Each (order, seller) pair once, with the seller's shipping deadline for that order.
CREATE OR REPLACE VIEW order_seller AS
SELECT order_id, seller_id, MAX(shipping_limit_date) AS ship_by
FROM order_items GROUP BY order_id, seller_id;
