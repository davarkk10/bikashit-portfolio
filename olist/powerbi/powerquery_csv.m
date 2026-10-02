// Power Query (M) — CSV fallback. Export each pbi_ view to C:\olist\powerbi_data\<view>.csv first
// (MySQL Workbench: right-click the view > Table Data Export Wizard > CSV). One query per file.

// Query name: fact_delivery
let
    Source = Csv.Document(File.Contents("C:\olist\powerbi_data\pbi_delivery.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Types = Table.TransformColumnTypes(Headers, {
        {"purchase_date", type date}, {"handover_date", type date}, {"delivered_date", type date}, {"promised_date", type date},
        {"days_vs_promise", Int64.Type}, {"days_to_deliver", Int64.Type}, {"days_promised", Int64.Type},
        {"is_late", Int64.Type}, {"delay_bucket_order", Int64.Type}, {"review_score", Int64.Type},
        {"items_value", Currency.Type}, {"freight_value", Currency.Type}, {"order_value", Currency.Type}}, "en-US")
in
    Types

// Repeat the same pattern for pbi_order_seller.csv (fact_order_seller), pbi_seller.csv (dim_seller)
// and pbi_first_order.csv (first_order), with the types listed in powerquery_mysql.m.
// Empty cells in review_score / handover_date / seller_late_handover / late_decile must stay null:
// if the export wrote "NULL" as text, add: Table.ReplaceValue(Types, "NULL", null, Replacer.ReplaceValue, {"review_score"}) before typing.
