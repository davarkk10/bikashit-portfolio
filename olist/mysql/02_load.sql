-- MySQL 8 version. Before running: SET GLOBAL local_infile = 1; and add OPT_LOCAL_INFILE=1
-- to the Workbench connection (Edit Connection > Advanced > Others). Change C:/olist/data to your folder.
-- Empty strings in date and number columns are turned into NULL with NULLIF.
LOAD DATA LOCAL INFILE 'C:/olist/data/olist_customers_dataset.csv' INTO TABLE customers
  FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES;

LOAD DATA LOCAL INFILE 'C:/olist/data/olist_sellers_dataset.csv' INTO TABLE sellers
  FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES;

LOAD DATA LOCAL INFILE 'C:/olist/data/olist_products_dataset.csv' INTO TABLE products
  FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES
  (product_id, @cat, @name_len, @desc_len, @photos, @weight, @length, @height, @width)
  SET product_category_name      = NULLIF(@cat, ''),
      product_name_lenght        = NULLIF(@name_len, ''),
      product_description_lenght = NULLIF(@desc_len, ''),
      product_photos_qty         = NULLIF(@photos, ''),
      product_weight_g           = NULLIF(@weight, ''),
      product_length_cm          = NULLIF(@length, ''),
      product_height_cm          = NULLIF(@height, ''),
      product_width_cm           = NULLIF(@width, '');

LOAD DATA LOCAL INFILE 'C:/olist/data/product_category_name_translation.csv' INTO TABLE category_translation
  FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES;

LOAD DATA LOCAL INFILE 'C:/olist/data/olist_orders_dataset.csv' INTO TABLE orders
  FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES
  (order_id, customer_id, order_status, order_purchase_timestamp, @approved, @carrier, @delivered, order_estimated_delivery_date)
  SET order_approved_at             = NULLIF(@approved, ''),
      order_delivered_carrier_date  = NULLIF(@carrier, ''),
      order_delivered_customer_date = NULLIF(@delivered, '');

LOAD DATA LOCAL INFILE 'C:/olist/data/olist_order_items_dataset.csv' INTO TABLE order_items
  FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES;

LOAD DATA LOCAL INFILE 'C:/olist/data/olist_order_payments_dataset.csv' INTO TABLE order_payments
  FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 LINES;

LOAD DATA LOCAL INFILE 'C:/olist/data/olist_order_reviews_dataset.csv' INTO TABLE order_reviews
  FIELDS TERMINATED BY ',' ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES
  (review_id, order_id, review_score, @title, @message, review_creation_date, @answered)
  SET review_comment_title    = NULLIF(@title, ''),
      review_comment_message  = NULLIF(@message, ''),
      review_answer_timestamp = NULLIF(@answered, '');
