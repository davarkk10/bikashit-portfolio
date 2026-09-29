-- ProcureAI decision-grade SQL catalogue. Every query is read-only.

-- Q01 Monthly realized spend and growth base
SELECT TO_CHAR(invoice_date,'YYYY-MM') month, SUM(line_net_amount) net_spend
FROM core.fct_invoice_line WHERE invoice_status='Posted' GROUP BY 1 ORDER BY 1;

-- Q02 Supplier concentration and cumulative share
WITH s AS (SELECT supplier_id,SUM(line_net_amount) spend FROM core.fct_invoice_line WHERE invoice_status='Posted' GROUP BY 1),
t AS (SELECT SUM(spend) total FROM s)
SELECT supplier_id,spend,spend/t.total share,SUM(spend) OVER(ORDER BY spend DESC)/t.total cumulative_share FROM s CROSS JOIN t ORDER BY spend DESC;

-- Q03 Tail-spend suppliers below INR 500,000
SELECT supplier_id,SUM(line_net_amount) spend FROM core.fct_invoice_line WHERE invoice_status='Posted' GROUP BY 1 HAVING SUM(line_net_amount)<500000 ORDER BY spend;

-- Q04 Off-contract spend by business unit
SELECT business_unit_id,SUM(off_contract_spend) off_contract_spend,SUM(off_contract_spend)/NULLIF(SUM(net_spend),0) off_contract_pct
FROM mart.v_spend_contract_compliance GROUP BY 1 ORDER BY off_contract_spend DESC;

-- Q05 Purchase-price variance by supplier
SELECT supplier_id,SUM(price_variance_amount) ppv FROM mart.v_invoice_three_way_match GROUP BY 1 ORDER BY ABS(SUM(price_variance_amount)) DESC;

-- Q06 Quote dispersion by material
SELECT material_id,COUNT(*) quote_count,MIN(quoted_unit_price) low_quote,MAX(quoted_unit_price) high_quote,
       STDDEV_SAMP(quoted_unit_price) quote_stddev
FROM raw.supplier_quotes GROUP BY 1 HAVING COUNT(*)>=3 ORDER BY quote_stddev DESC NULLS LAST;

-- Q07 Supplier OTIF ranking with minimum sample
SELECT * FROM mart.v_supplier_performance WHERE eligible_po_lines>=100 ORDER BY otif_rate ASC,eligible_po_lines DESC;

-- Q08 Late-delivery exposure by warehouse
SELECT warehouse_id,COUNT(*) FILTER(WHERE days_late>0) late_lines,AVG(GREATEST(days_late,0)) avg_late_days
FROM mart.v_po_line_service_outcome GROUP BY 1 ORDER BY late_lines DESC;

-- Q09 Quality loss by supplier
SELECT supplier_id,SUM(rejected_quantity) rejected,SUM(received_quantity) received,
       SUM(rejected_quantity)::NUMERIC/NULLIF(SUM(received_quantity),0) defect_rate
FROM core.fct_goods_receipt_line GROUP BY 1 ORDER BY defect_rate DESC;

-- Q10 Open supplier incidents by severity
SELECT supplier_id,severity,COUNT(*) incidents FROM core.fct_supplier_incident
WHERE incident_status<>'Closed' GROUP BY 1,2 ORDER BY incidents DESC;

-- Q11 Invoice exception queue by financial exposure
SELECT invoice_id,supplier_id,invoice_gross_amount,exception_count,price_variance_amount
FROM mart.v_invoice_three_way_match WHERE exception_count>0 ORDER BY invoice_gross_amount DESC;

-- Q12 Probable duplicate exposure
SELECT supplier_id,COUNT(*) invoice_count,SUM(invoice_gross_amount) gross_exposure
FROM mart.v_invoice_three_way_match WHERE probable_duplicate_flag GROUP BY 1 ORDER BY gross_exposure DESC;

-- Q13 Bank-change exposure
SELECT supplier_id,COUNT(*) invoice_count,SUM(invoice_gross_amount) gross_exposure
FROM mart.v_invoice_three_way_match WHERE bank_detail_change_flag GROUP BY 1 ORDER BY gross_exposure DESC;

-- Q14 Approval bottlenecks by supplier
SELECT supplier_id,COUNT(*) invoices,PERCENTILE_CONT(.5) WITHIN GROUP(ORDER BY approval_cycle_hours) median_hours,
       PERCENTILE_CONT(.9) WITHIN GROUP(ORDER BY approval_cycle_hours) p90_hours
FROM mart.v_invoice_approval_cycle GROUP BY 1 ORDER BY p90_hours DESC;

-- Q15 Payment timing distribution
SELECT payment_timing,COUNT(*) invoices,SUM(invoice_gross_amount) gross_value
FROM mart.v_payment_performance GROUP BY 1 ORDER BY gross_value DESC;

-- Q16 Overdue unpaid exposure as of lifecycle cutoff
SELECT supplier_id,COUNT(*) invoices,SUM(outstanding_amount) outstanding
FROM mart.v_payment_performance WHERE payment_timing='Unpaid' AND due_date<DATE '2026-03-05'
GROUP BY 1 ORDER BY outstanding DESC;

-- Q17 Contract expiry exposure by band
SELECT expiry_band,COUNT(*) contracts,SUM(contract_value) contract_value
FROM mart.v_contract_portfolio GROUP BY 1 ORDER BY MIN(days_to_expiry);

-- Q18 Auto-renewal contracts near expiry
SELECT contract_id,supplier_id,end_date,days_to_expiry,contract_value
FROM mart.v_contract_portfolio WHERE auto_renewal_flag AND days_to_expiry BETWEEN 0 AND 90 ORDER BY days_to_expiry;

-- Q19 Contract leakage by supplier/category
SELECT supplier_id,category_id,SUM(off_contract_spend) leakage,SUM(net_spend) spend
FROM mart.v_spend_contract_compliance GROUP BY 1,2 HAVING SUM(off_contract_spend)>0 ORDER BY leakage DESC;

-- Q20 Exception aging from invoice to due date
SELECT invoice_id,supplier_id,due_date-invoice_date allowed_days,exception_count,invoice_gross_amount
FROM mart.v_invoice_three_way_match WHERE exception_count>0 ORDER BY allowed_days DESC,invoice_gross_amount DESC;

-- Q21 Material price trend and volatility
SELECT material_id,DATE_TRUNC('month',invoice_date) month,AVG(invoice_unit_price) avg_price,STDDEV_SAMP(invoice_unit_price) price_stddev
FROM core.fct_invoice_line WHERE invoice_status='Posted' GROUP BY 1,2 ORDER BY 1,2;

-- Q22 Buyer off-contract accountability
SELECT pol.buyer_id,SUM(il.line_net_amount) FILTER(WHERE NOT COALESCE(pol.contract_valid_at_order_flag,FALSE)) off_contract_spend,
       SUM(il.line_net_amount) total_spend
FROM core.fct_invoice_line il LEFT JOIN core.fct_purchase_order_line pol USING(po_line_id)
WHERE il.invoice_status='Posted' GROUP BY 1 ORDER BY off_contract_spend DESC;
