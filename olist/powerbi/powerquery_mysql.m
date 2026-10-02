// Power Query (M) — MySQL source. Home > Transform data > New Source > Blank Query > Advanced Editor.
// Needs the MySQL connector for Power BI (MySQL Connector/NET 8.x installed). Create one query per view.

// Query name: fact_delivery
let
    Source = MySQL.Database("localhost", "olist_db", [ReturnSingleDatabase = true]),
    View = Source{[Schema = "olist_db", Item = "pbi_delivery"]}[Data],
    Types = Table.TransformColumnTypes(View, {
        {"purchase_date", type date}, {"handover_date", type date}, {"delivered_date", type date}, {"promised_date", type date},
        {"days_vs_promise", Int64.Type}, {"days_to_deliver", Int64.Type}, {"days_promised", Int64.Type},
        {"is_late", Int64.Type}, {"delay_bucket_order", Int64.Type}, {"review_score", Int64.Type},
        {"items_value", Currency.Type}, {"freight_value", Currency.Type}, {"order_value", Currency.Type}})
in
    Types

// Query name: fact_order_seller
let
    Source = MySQL.Database("localhost", "olist_db", [ReturnSingleDatabase = true]),
    View = Source{[Schema = "olist_db", Item = "pbi_order_seller"]}[Data],
    Types = Table.TransformColumnTypes(View, {{"ship_by_date", type date}, {"seller_late_handover", Int64.Type}})
in
    Types

// Query name: dim_seller
let
    Source = MySQL.Database("localhost", "olist_db", [ReturnSingleDatabase = true]),
    View = Source{[Schema = "olist_db", Item = "pbi_seller"]}[Data],
    Types = Table.TransformColumnTypes(View, {{"late_decile", Int64.Type}}),
    Proper = Table.TransformColumns(Types, {{"seller_city", Text.Proper, type text}})
in
    Proper

// Query name: first_order
let
    Source = MySQL.Database("localhost", "olist_db", [ReturnSingleDatabase = true]),
    View = Source{[Schema = "olist_db", Item = "pbi_first_order"]}[Data],
    Types = Table.TransformColumnTypes(View, {{"first_order_late", Int64.Type}, {"came_back", Int64.Type}})
in
    Types
