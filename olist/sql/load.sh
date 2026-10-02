#!/usr/bin/env bash
# Load eight Olist CSVs (plain .csv or .csv.gz; geolocation is not used) into PostgreSQL. Usage: DATA=path/to/raw PGURL=postgresql://... ./load.sh
set -euo pipefail
DATA=${DATA:-raw}; PGURL=${PGURL:-postgresql://postgres@127.0.0.1:5432/postgres}
psql "$PGURL" -v ON_ERROR_STOP=1 -q -f "$(dirname "$0")/00_schema.sql"
load() { f="$DATA/$1.csv"; [ -f "$f" ] && src="cat $f" || src="zcat $f.gz"; $src | sed '1s/^\xEF\xBB\xBF//' | psql "$PGURL" -v ON_ERROR_STOP=1 -q -c "\copy olist.$2 FROM STDIN WITH (FORMAT csv, HEADER true)"; }
load olist_customers_dataset customers
load olist_sellers_dataset sellers
load olist_products_dataset products
load product_category_name_translation category_translation
load olist_orders_dataset orders
load olist_order_items_dataset order_items
load olist_order_payments_dataset order_payments
load olist_order_reviews_dataset order_reviews
psql "$PGURL" -v ON_ERROR_STOP=1 -q -f "$(dirname "$0")/01_views.sql"
echo "loaded"
