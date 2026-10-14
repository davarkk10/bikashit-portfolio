"""Semantic model (TMSL) for the ProcureAI Model Results report.

Tables load from CSVs in the DataFolder parameter (default C:\\ProcureAI\\data\\).
Star schema: dim_date, dim_supplier, dim_warehouse -> fact_po (purchase orders, late-delivery model)
and fact_invoice (invoice risk model). Small result tables hold the headline metrics that
cannot be recomputed in DAX (PR-AUC needs every score at once).
"""
import json
import uuid


def lt():
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"procureai/{next(_ids)}"))


_ids = iter(range(10**6))


def col(name, dtype, fmt=None, hidden=False, sort_by=None, key=False, summarize='none', category=None):
    c = {'name': name, 'dataType': dtype, 'sourceColumn': name, 'lineageTag': lt(), 'summarizeBy': summarize,
         'annotations': [{'name': 'SummarizationSetBy', 'value': 'Automatic'}]}
    if fmt: c['formatString'] = fmt
    if hidden: c['isHidden'] = True
    if sort_by: c['sortByColumn'] = sort_by
    if key: c['isKey'] = True
    if category: c['dataCategory'] = category
    if dtype == 'dateTime':
        c['formatString'] = fmt or 'dd mmm yyyy'
        c['annotations'].append({'name': 'UnderlyingDateTimeDataType', 'value': 'Date'})
    return c


def calc_col(name, expr, dtype, fmt=None, hidden=False, sort_by=None):
    c = {'type': 'calculated', 'name': name, 'dataType': dtype, 'isDataTypeInferred': True, 'expression': expr,
         'lineageTag': lt(), 'summarizeBy': 'none', 'annotations': [{'name': 'SummarizationSetBy', 'value': 'Automatic'}]}
    if fmt: c['formatString'] = fmt
    if hidden: c['isHidden'] = True
    if sort_by: c['sortByColumn'] = sort_by
    return c


def table(name, columns, m_code, measures=None, hidden=False, category=None):
    t = {'name': name, 'lineageTag': lt(), 'columns': columns,
         'partitions': [{'name': f'{name}-partition', 'mode': 'import', 'source': {'type': 'm', 'expression': m_code.strip('\n').split('\n')}}],
         'annotations': [{'name': 'PBI_ResultType', 'value': 'Table'}]}
    if measures: t['measures'] = measures
    if hidden: t['isHidden'] = True
    if category: t['dataCategory'] = category
    return t


M_TYPE = {'string': 'type text', 'int64': 'Int64.Type', 'double': 'type number', 'decimal': 'Currency.Type', 'dateTime': 'type date'}


def csv_table(name, file, spec, calcs=(), nullable=(), measures=None):
    """spec: list of (column, dataType, kwargs) in CSV order."""
    types = ', '.join('{"%s", %s}' % (c, M_TYPE[t]) for c, t, _ in spec)
    nulls = ', '.join('"%s"' % c for c in nullable)
    repl = (f'    Nulls = Table.ReplaceValue(Promoted, "", null, Replacer.ReplaceValue, {{{nulls}}}),\n' if nullable
            else '    Nulls = Promoted,\n')
    m = f'''let
    Folder = if Text.EndsWith(DataFolder, "\\") then DataFolder else DataFolder & "\\",
    Source = Csv.Document(File.Contents(Folder & "{file}"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
{repl}    Typed = Table.TransformColumnTypes(Nulls, {{{types}}}, "en-US")
in
    Typed'''
    cols = [col(c, t, **kw) for c, t, kw in spec] + list(calcs)
    return table(name, cols, m, measures=measures)


H = {'hidden': True}
INR = '"₹"#,0'
PCT = '0.0%'

fact_po = csv_table('fact_po', 'fact_po.csv', [
    ('po_id', 'string', {}), ('order_date', 'dateTime', {}), ('promised_date', 'dateTime', {}), ('receipt_date', 'dateTime', {}),
    ('supplier_id', 'string', H), ('warehouse_id', 'string', H), ('po_value', 'decimal', {'fmt': INR}), ('late', 'int64', {'fmt': '0'}),
    ('lead_days', 'int64', {'fmt': '0'}), ('quoted_lead_time_days', 'int64', {'fmt': '0'}), ('promise_slack_days', 'int64', {'fmt': '0'}),
    ('road_distance_km', 'double', {'fmt': '#,0'}), ('route_type', 'string', {}), ('utilisation', 'double', {'fmt': '0.00'}),
    ('festival_window', 'int64', {'fmt': '0'}), ('dest_flood_risk', 'double', {'fmt': '0.00'}), ('dispatched_by_rescore', 'int64', {'fmt': '0'}),
    ('dispatch_slip_seen', 'int64', {'fmt': '0'}), ('advisory', 'int64', {'fmt': '0'}), ('supplier_past_late_rate', 'double', {'fmt': PCT}),
    ('split', 'string', {}), ('p_order', 'double', {'fmt': '0.000'}), ('p_pre', 'double', {'fmt': '0.000'}),
    ('flag_order', 'int64', {'fmt': '0'}), ('flag_pre', 'int64', {'fmt': '0'}),
], calcs=[
    calc_col('Delivery', 'IF ( fact_po[late] = 1, "Late", "On time" )', 'string'),
    calc_col('Load Band', 'SWITCH ( TRUE (), fact_po[utilisation] < 0.8, "Under 80%", fact_po[utilisation] < 1.0, "80–100%", '
             'fact_po[utilisation] < 1.2, "100–120%", "Over 120%" )', 'string', sort_by='Load Band Order'),
    calc_col('Load Band Order', 'SWITCH ( TRUE (), fact_po[utilisation] < 0.8, 1, fact_po[utilisation] < 1.0, 2, fact_po[utilisation] < 1.2, 3, 4 )',
             'int64', fmt='0', hidden=True),
], nullable=['p_order', 'p_pre'])

fact_invoice = csv_table('fact_invoice', 'fact_invoice.csv', [
    ('invoice_id', 'string', {}), ('invoice_date', 'dateTime', {}), ('supplier_id', 'string', H), ('po_id', 'string', {}),
    ('gross_amount', 'decimal', {'fmt': INR}), ('rules_policy', 'int64', {'fmt': '0'}), ('rules_refined', 'int64', {'fmt': '0'}),
    ('max_price_var', 'double', {'fmt': '0.0%'}), ('supplier_price_drift_120d', 'double', {'fmt': '0.00%'}),
    ('prior_inv_same_po', 'int64', {'fmt': '0'}), ('similar_number_seen', 'int64', {'fmt': '0'}), ('split', 'string', {}),
    ('model_score', 'double', {'fmt': '0.000'}), ('model_flag', 'int64', {'fmt': '0'}), ('condition', 'string', {}),
    ('condition_group', 'string', {}), ('is_condition', 'int64', {'fmt': '0'}),
], calcs=[
    calc_col('Model Says', 'IF ( fact_invoice[model_flag] = 1, "Review", "Pass" )', 'string'),
    calc_col('Rules Say', 'IF ( fact_invoice[rules_refined] = 1, "Flag", "Pass" )', 'string'),
], nullable=['po_id', 'model_score', 'max_price_var', 'prior_inv_same_po', 'similar_number_seen'])

dim_supplier = csv_table('dim_supplier', 'dim_supplier.csv', [
    ('supplier_id', 'string', {'key': True, 'hidden': True}), ('supplier_name', 'string', {}), ('city', 'string', {'category': 'City'}),
    ('category_name', 'string', {}), ('category_group', 'string', {})])
dim_warehouse = csv_table('dim_warehouse', 'dim_warehouse.csv', [
    ('warehouse_id', 'string', {'key': True, 'hidden': True}), ('warehouse_name', 'string', {}), ('city', 'string', {'category': 'City'}),
    ('flood_region', 'string', {})])
model_results = csv_table('model_results', 'model_results.csv', [
    ('area', 'string', {}), ('method', 'string', {'sort_by': 'method_order'}), ('role', 'string', {}), ('method_order', 'int64', {'fmt': '0', 'hidden': True}),
    ('metric', 'string', {}), ('value', 'double', {'fmt': '0.000'})])
invoice_catch = csv_table('invoice_catch', 'invoice_catch.csv', [
    ('condition', 'string', {}), ('condition_group', 'string', {}), ('test_cases', 'int64', {'fmt': '#,0'}),
    ('rules_caught', 'double', {'fmt': PCT}), ('model_caught', 'double', {'fmt': PCT})])
driver_importance = csv_table('driver_importance', 'driver_importance.csv', [
    ('driver', 'string', {}), ('pr_auc_lost_when_removed', 'double', {'fmt': '0.000'})])
contract_qa = csv_table('contract_qa', 'contract_qa.csv', [
    ('question_no', 'int64', {'fmt': '0'}), ('question', 'string', {}), ('question_type', 'string', {}), ('answerable', 'int64', {'fmt': '0'}),
    ('result', 'string', {}), ('is_correct', 'int64', {'fmt': '0'}), ('answer', 'string', {}), ('citation', 'string', {})],
    nullable=['citation'])

dim_date = table('dim_date', [
    col('Date', 'dateTime', key=True), col('Year', 'int64', fmt='0'), col('Month No', 'int64', fmt='0', hidden=True),
    col('Month', 'string', sort_by='Month No'), col('Month Start', 'dateTime', fmt='mmm yy'),
], '''let
    StartDate = #date(2024, 1, 1),
    EndDate = #date(2026, 3, 31),
    Dates = List.Dates(StartDate, Duration.Days(EndDate - StartDate) + 1, #duration(1, 0, 0, 0)),
    Base = Table.FromList(Dates, Splitter.SplitByNothing(), {"Date"}),
    Typed = Table.TransformColumnTypes(Base, {{"Date", type date}}),
    AddYear = Table.AddColumn(Typed, "Year", each Date.Year([Date]), Int64.Type),
    AddMonthNo = Table.AddColumn(AddYear, "Month No", each Date.Month([Date]), Int64.Type),
    AddMonth = Table.AddColumn(AddMonthNo, "Month", each Date.ToText([Date], "MMM", "en-US"), type text),
    AddMonthStart = Table.AddColumn(AddMonth, "Month Start", each Date.StartOfMonth([Date]), type date)
in
    AddMonthStart''', category='Time')


def R(area, metric, role=None, method=None):
    f = [f'model_results[area] = "{area}"', f'model_results[metric] = "{metric}"']
    if role: f.append(f'model_results[role] = "{role}"')
    if method: f.append(f'model_results[method] = "{method}"')
    return 'CALCULATE ( MAX ( model_results[value] ), ' + ', '.join(f) + ' )'


MEASURES = [
    # name, expression, format, folder
    ('POs', 'COUNTROWS ( fact_po )', '#,0', '1 Overview'),
    ('Invoices', 'COUNTROWS ( fact_invoice )', '#,0', '1 Overview'),
    ('Invoice Value', 'SUM ( fact_invoice[gross_amount] )', '"₹"#,0.0,,"M"', '1 Overview'),
    ('Suppliers', 'COUNTROWS ( dim_supplier )', '#,0', '1 Overview'),
    ('PR-AUC Explainer', '"PR-AUC: a 0-to-1 score for how well a model puts real problems at the top of the review list. '
     'Guessing scores the problem rate (about 0.04 for hard invoice cases, 0.37 for late deliveries); 1.0 is perfect."', None, '1 Overview'),

    ('Invoice Model PR-AUC Hard', R('Invoice risk', 'pr_auc_hard', role='Model'), '0.00', '2 Invoice risk'),
    ('Invoice Rules PR-AUC Hard', R('Invoice risk', 'pr_auc_hard', method='Best hand-written rules'), '0.00', '2 Invoice risk'),
    ('Invoice Model PR-AUC', R('Invoice risk', 'pr_auc', role='Model'), '0.00', '2 Invoice risk'),
    ('Invoice Rules PR-AUC', R('Invoice risk', 'pr_auc', method='Best hand-written rules'), '0.00', '2 Invoice risk'),
    ('Invoice Model Callout', '"Best rules " & FORMAT ( [Invoice Rules PR-AUC Hard], "0.00" ) & " · guessing ≈ 0.04"', None, '2 Invoice risk'),
    ('Test Conditions', 'CALCULATE ( [Invoices], fact_invoice[split] = "Test", fact_invoice[is_condition] = 1 )', '#,0', '2 Invoice risk'),
    ('Model Flagged', 'CALCULATE ( [Invoices], fact_invoice[model_flag] = 1 )', '#,0', '2 Invoice risk'),
    ('Model Hits', 'CALCULATE ( [Invoices], fact_invoice[model_flag] = 1, fact_invoice[is_condition] = 1 )', '#,0', '2 Invoice risk'),
    ('Model Precision', 'DIVIDE ( [Model Hits], [Model Flagged] )', PCT, '2 Invoice risk'),
    ('Model Recall', 'DIVIDE ( [Model Hits], [Test Conditions] )', PCT, '2 Invoice risk'),
    ('Rules Flagged', 'CALCULATE ( [Invoices], fact_invoice[split] = "Test", fact_invoice[rules_refined] = 1 )', '#,0', '2 Invoice risk'),
    ('Rules Hits', 'CALCULATE ( [Invoices], fact_invoice[split] = "Test", fact_invoice[rules_refined] = 1, fact_invoice[is_condition] = 1 )', '#,0', '2 Invoice risk'),
    ('Rules Precision', 'DIVIDE ( [Rules Hits], [Rules Flagged] )', PCT, '2 Invoice risk'),
    ('Rules Recall', 'DIVIDE ( [Rules Hits], [Test Conditions] )', PCT, '2 Invoice risk'),
    ('Model Precision Callout', '"of " & FORMAT ( [Model Flagged], "#,0" ) & " flagged are real · catches " & FORMAT ( [Model Recall], "0%" )', None, '2 Invoice risk'),
    ('Rules Precision Callout', '"of " & FORMAT ( [Rules Flagged], "#,0" ) & " flagged are real · catches " & FORMAT ( [Rules Recall], "0%" )', None, '2 Invoice risk'),
    ('Rules Caught %', 'AVERAGE ( invoice_catch[rules_caught] )', PCT, '2 Invoice risk'),
    ('Model Caught %', 'AVERAGE ( invoice_catch[model_caught] )', PCT, '2 Invoice risk'),

    ('Delay Baseline PR-AUC', R('Late delivery', 'pr_auc', role='Baseline'), '0.00', '3 Late delivery'),
    ('Delay Order PR-AUC', R('Late delivery', 'pr_auc', method='Logistic regression, order time'), '0.00', '3 Late delivery'),
    ('Delay Pre PR-AUC', R('Late delivery', 'pr_auc', method='Logistic regression, 3 days before'), '0.00', '3 Late delivery'),
    ('Delay Ceiling PR-AUC', R('Late delivery', 'pr_auc', role='Ceiling'), '0.00', '3 Late delivery'),
    ('Delay Order Callout', '"Supplier history alone " & FORMAT ( [Delay Baseline PR-AUC], "0.00" ) & " · guessing 0.37"', None, '3 Late delivery'),
    ('Delay Pre Callout', '"Adds dispatch notice and flood or bandh warnings"', None, '3 Late delivery'),
    ('Late %', 'DIVIDE ( SUM ( fact_po[late] ), [POs] )', PCT, '3 Late delivery'),
    ('Test Late %', 'CALCULATE ( [Late %], fact_po[split] = "Test" )', PCT, '3 Late delivery'),
    ('Avg Predicted Risk', 'AVERAGE ( fact_po[p_order] )', PCT, '3 Late delivery'),
    ('Flagged Late % (Order)', 'CALCULATE ( [Late %], fact_po[flag_order] = 1 )', PCT, '3 Late delivery'),
    ('Flagged Late % (Pre)', 'CALCULATE ( [Late %], fact_po[flag_pre] = 1 )', PCT, '3 Late delivery'),
    ('Late Caught (Pre)', 'DIVIDE ( CALCULATE ( SUM ( fact_po[late] ), fact_po[flag_pre] = 1 ), CALCULATE ( SUM ( fact_po[late] ), fact_po[split] = "Test" ) )', PCT, '3 Late delivery'),
    ('Flagged Callout', '"Top 25% reviewed 3 days out · catches " & FORMAT ( [Late Caught (Pre)], "0%" ) & " of late POs"', None, '3 Late delivery'),
    ('Test Late Callout', 'FORMAT ( CALCULATE ( [POs], fact_po[split] = "Test" ), "#,0" ) & " test POs, Jul–Dec 2025"', None, '3 Late delivery'),
    ('Driver Importance', 'SUM ( driver_importance[pr_auc_lost_when_removed] )', '0.000', '3 Late delivery'),

    ('Questions', 'COUNTROWS ( contract_qa )', '#,0', '4 Contract assistant'),
    ('Correct', 'SUM ( contract_qa[is_correct] )', '#,0', '4 Contract assistant'),
    ('Accuracy', 'DIVIDE ( [Correct], [Questions] )', PCT, '4 Contract assistant'),
    ('Contract Score', 'FORMAT ( [Correct], "0" ) & " / " & FORMAT ( [Questions], "0" )', None, '4 Contract assistant'),
    ('Wrong Answers', 'CALCULATE ( [Questions], contract_qa[result] = "Wrong answer" ) + 0', '0', '4 Contract assistant'),
    ('Refusals Correct', 'FORMAT ( CALCULATE ( [Correct], contract_qa[answerable] = 0 ), "0" ) & " / " & FORMAT ( CALCULATE ( [Questions], contract_qa[answerable] = 0 ), "0" )', None, '4 Contract assistant'),
    ('Contract Callout', 'FORMAT ( [Accuracy], "0.0%" ) & " · question set locked before any code"', None, '4 Contract assistant'),
]

measures = []
for name, expr, fmt, folder in MEASURES:
    d = {'name': name, 'expression': expr, 'lineageTag': lt(), 'displayFolder': folder}
    if fmt: d['formatString'] = fmt
    measures.append(d)

measures_tbl = table('_Measures', [col('Column1', 'string', hidden=True)], '''let
    Source = #table(type table [Column1 = text], {})
in
    Source''', measures=measures)

tables = [measures_tbl, fact_po, fact_invoice, dim_supplier, dim_warehouse, dim_date, model_results, invoice_catch, driver_importance, contract_qa]


def rel(f_t, f_c, t_t, t_c, active=True):
    r = {'name': lt(), 'fromTable': f_t, 'fromColumn': f_c, 'toTable': t_t, 'toColumn': t_c}
    if not active: r['isActive'] = False
    return r


relationships = [
    rel('fact_po', 'order_date', 'dim_date', 'Date'),
    rel('fact_po', 'supplier_id', 'dim_supplier', 'supplier_id'),
    rel('fact_po', 'warehouse_id', 'dim_warehouse', 'warehouse_id'),
    rel('fact_invoice', 'invoice_date', 'dim_date', 'Date'),
    rel('fact_invoice', 'supplier_id', 'dim_supplier', 'supplier_id'),
]

model = {
    'name': 'SemanticModel',
    'compatibilityLevel': 1567,
    'model': {
        'culture': 'en-US',
        'dataAccessOptions': {'legacyRedirects': True, 'returnErrorValuesAsNull': True},
        'defaultPowerBIDataSourceVersion': 'powerBI_V3',
        'sourceQueryCulture': 'en-US',
        'tables': tables,
        'relationships': relationships,
        'expressions': [{
            'name': 'DataFolder', 'kind': 'm', 'lineageTag': lt(),
            'expression': ['"C:\\ProcureAI\\data\\" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]'],
            'annotations': [{'name': 'PBI_ResultType', 'value': 'Text'}, {'name': 'PBI_NavigationStepName', 'value': 'Navigation'}]}],
        'annotations': [
            {'name': 'PBI_QueryOrder', 'value': json.dumps(['DataFolder'] + [t['name'] for t in tables])},
            {'name': '__PBI_TimeIntelligenceEnabled', 'value': '0'}],
    },
}

if __name__ == '__main__':
    print(len(measures), 'measures,', len(tables), 'tables,', len(relationships), 'relationships')
