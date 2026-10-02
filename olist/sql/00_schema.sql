-- Olist Brazilian e-commerce (public dataset, Kaggle, CC BY-NC-SA 4.0): ~100k real orders, 2016-2018.
-- Raw tables are loaded as-is; every cleaning decision is made in a view, not by editing the data.
DROP SCHEMA IF EXISTS olist CASCADE;
CREATE SCHEMA olist;
SET search_path = olist;

CREATE TABLE customers (customer_id text PRIMARY KEY, customer_unique_id text NOT NULL,
  customer_zip_code_prefix text, customer_city text, customer_state char(2));
CREATE TABLE sellers (seller_id text PRIMARY KEY, seller_zip_code_prefix text, seller_city text, seller_state char(2));
CREATE TABLE products (product_id text PRIMARY KEY, product_category_name text, product_name_lenght int,
  product_description_lenght int, product_photos_qty int, product_weight_g int, product_length_cm int,
  product_height_cm int, product_width_cm int);
CREATE TABLE category_translation (product_category_name text PRIMARY KEY, product_category_name_english text);
CREATE TABLE orders (order_id text PRIMARY KEY, customer_id text REFERENCES customers, order_status text,
  order_purchase_timestamp timestamp, order_approved_at timestamp, order_delivered_carrier_date timestamp,
  order_delivered_customer_date timestamp, order_estimated_delivery_date timestamp);
CREATE TABLE order_items (order_id text REFERENCES orders, order_item_id int, product_id text REFERENCES products,
  seller_id text REFERENCES sellers, shipping_limit_date timestamp, price numeric(10,2), freight_value numeric(10,2),
  PRIMARY KEY (order_id, order_item_id));
CREATE TABLE order_payments (order_id text REFERENCES orders, payment_sequential int, payment_type text,
  payment_installments int, payment_value numeric(10,2), PRIMARY KEY (order_id, payment_sequential));
-- review_id is NOT unique in the source (a known quirk), so no primary key here; duplicates are handled in a view.
CREATE TABLE order_reviews (review_id text, order_id text REFERENCES orders, review_score int CHECK (review_score BETWEEN 1 AND 5),
  review_comment_title text, review_comment_message text, review_creation_date timestamp, review_answer_timestamp timestamp);
