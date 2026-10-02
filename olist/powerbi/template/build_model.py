# Builds the DataModelSchema (TMSL) for Olist Delivery 360 from measures.dax
import json, re, uuid

DAX = '/home/claude/bikashit-portfolio/olist/powerbi/measures.dax'
# light-theme colours in the DAX -> Case 4 dark theme colours
RECOLOR = {'#0D9488': '#5EAA12', '#D64550': '#8B7BFF', '#D87B43': '#C9821F', '#94A3B8': '#7F8BA0'}

def lt():
    return str(uuid.uuid4())

def m_lines(code):
    return code.strip('\n').split('\n')

def col(name, dtype, source=None, fmt=None, hidden=False, sort_by=None, summarize='none', key=False, category=None):
    c = {'name': name, 'dataType': dtype, 'sourceColumn': source or name, 'lineageTag': lt(),
         'summarizeBy': summarize, 'annotations': [{'name': 'SummarizationSetBy', 'value': 'Automatic'}]}
    if fmt: c['formatString'] = fmt
    if hidden: c['isHidden'] = True
    if sort_by: c['sortByColumn'] = sort_by
    if key: c['isKey'] = True
    if category: c['dataCategory'] = category
    if dtype == 'dateTime':
        c['formatString'] = fmt or 'Long Date'
        c['annotations'].append({'name': 'UnderlyingDateTimeDataType', 'value': 'Date'})
    return c

def calc_col(name, expr, dtype, fmt=None, hidden=False, sort_by=None):
    c = {'type': 'calculated', 'name': name, 'dataType': dtype, 'isDataTypeInferred': True,
         'expression': expr, 'lineageTag': lt(), 'summarizeBy': 'none',
         'annotations': [{'name': 'SummarizationSetBy', 'value': 'Automatic'}]}
    if fmt: c['formatString'] = fmt
    if hidden: c['isHidden'] = True
    if sort_by: c['sortByColumn'] = sort_by
    return c

def table(name, columns, m_code, hidden=False, measures=None, category=None):
    t = {'name': name, 'lineageTag': lt(), 'columns': columns,
         'partitions': [{'name': f'{name}-{uuid.uuid4()}', 'mode': 'import',
                         'source': {'type': 'm', 'expression': m_lines(m_code)}}],
         'annotations': [{'name': 'PBI_ResultType', 'value': 'Table'}]}
    if measures: t['measures'] = measures
    if hidden: t['isHidden'] = True
    if category: t['dataCategory'] = category
    return t

def csv_m(file, types, nullable):
    type_list = ', '.join('{"%s", %s}' % (c, t) for c, t in types)
    null_list = ', '.join('"%s"' % c for c in nullable)
    repl = (f'    Nulls = Table.ReplaceValue(Promoted, "", null, Replacer.ReplaceValue, {{{null_list}}}),\n'
            if nullable else '    Nulls = Promoted,\n')
    return f'''let
    Source = Csv.Document(File.Contents(DataFolder & "{file}"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
{repl}    Typed = Table.TransformColumnTypes(Nulls, {{{type_list}}}, "en-US")
in
    Typed'''

# ---------------- tables ----------------
fd_types = [('order_id', 'type text'), ('customer_unique_id', 'type text'), ('customer_state', 'type text'),
            ('purchase_date', 'type date'), ('handover_date', 'type date'), ('delivered_date', 'type date'),
            ('promised_date', 'type date'), ('days_vs_promise', 'Int64.Type'), ('days_to_deliver', 'Int64.Type'),
            ('days_promised', 'Int64.Type'), ('is_late', 'Int64.Type'), ('delay_bucket', 'type text'),
            ('delay_bucket_order', 'Int64.Type'), ('review_score', 'Int64.Type'), ('items_value', 'Currency.Type'),
            ('freight_value', 'Currency.Type'), ('order_value', 'Currency.Type')]
fact_delivery = table('fact_delivery', [
    col('order_id', 'string', hidden=True), col('customer_unique_id', 'string', hidden=True),
    col('customer_state', 'string', hidden=True), col('purchase_date', 'dateTime', fmt='dd mmm yyyy'),
    col('handover_date', 'dateTime', fmt='dd mmm yyyy'), col('delivered_date', 'dateTime', fmt='dd mmm yyyy'),
    col('promised_date', 'dateTime', fmt='dd mmm yyyy'), col('days_vs_promise', 'int64', fmt='0'),
    col('days_to_deliver', 'int64', fmt='0'), col('days_promised', 'int64', fmt='0'), col('is_late', 'int64', fmt='0'),
    col('delay_bucket', 'string', sort_by='delay_bucket_order'), col('delay_bucket_order', 'int64', fmt='0', hidden=True),
    col('review_score', 'int64', fmt='0'), col('items_value', 'decimal', fmt='"R$" #,0.00'),
    col('freight_value', 'decimal', fmt='"R$" #,0.00'), col('order_value', 'decimal', fmt='"R$" #,0.00'),
    calc_col('Delivery Status', 'IF ( fact_delivery[is_late] = 1, "Late", "On time" )', 'string'),
    calc_col('In Review Window', 'IF ( fact_delivery[days_vs_promise] >= -20 && fact_delivery[days_vs_promise] <= 30, 1, 0 )', 'int64', fmt='0', hidden=True),
], csv_m('pbi_delivery.csv', fd_types, ['handover_date', 'review_score']))

fos = table('fact_order_seller', [
    col('order_id', 'string', hidden=True), col('seller_id', 'string', hidden=True),
    col('ship_by_date', 'dateTime', fmt='dd mmm yyyy'), col('seller_late_handover', 'int64', fmt='0'),
    calc_col('Lane', 'RELATED ( dim_seller[seller_state] ) & " → " & RELATED ( fact_delivery[customer_state] )', 'string'),
], csv_m('pbi_order_seller.csv', [('order_id', 'type text'), ('seller_id', 'type text'),
                                   ('ship_by_date', 'type date'), ('seller_late_handover', 'Int64.Type')],
         ['seller_late_handover']))

dim_seller = table('dim_seller', [
    col('seller_id', 'string', hidden=True), col('seller_city', 'string'), col('seller_state', 'string'),
    col('late_decile', 'int64', fmt='0'),
    calc_col('Seller Region', 'LOOKUPVALUE ( dim_state[Region], dim_state[State Code], dim_seller[seller_state] )', 'string'),
    calc_col('Seller Decile Label', 'IF ( ISBLANK ( dim_seller[late_decile] ), "Under 30 orders", "D" & dim_seller[late_decile] )', 'string', sort_by='Decile Sort'),
    calc_col('Decile Sort', 'IF ( ISBLANK ( dim_seller[late_decile] ), 99, dim_seller[late_decile] )', 'int64', fmt='0', hidden=True),
    calc_col('Seller Short', 'LEFT ( dim_seller[seller_id], 8 )', 'string'),
], '''let
    Source = Csv.Document(File.Contents(DataFolder & "pbi_seller.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Nulls = Table.ReplaceValue(Promoted, "", null, Replacer.ReplaceValue, {"late_decile"}),
    Typed = Table.TransformColumnTypes(Nulls, {{"seller_id", type text}, {"seller_city", type text}, {"seller_state", type text}, {"late_decile", Int64.Type}}, "en-US"),
    Proper = Table.TransformColumns(Typed, {{"seller_city", Text.Proper, type text}})
in
    Proper''')

first_order = table('first_order', [
    col('customer_unique_id', 'string', hidden=True), col('first_order_id', 'string', hidden=True),
    col('first_order_late', 'int64', fmt='0'), col('came_back', 'int64', fmt='0'),
], csv_m('pbi_first_order.csv', [('customer_unique_id', 'type text'), ('first_order_id', 'type text'),
                                  ('first_order_late', 'Int64.Type'), ('came_back', 'Int64.Type')], []))

dim_date = table('dim_date', [
    col('Date', 'dateTime', fmt='dd mmm yyyy', key=True), col('Year', 'int64', fmt='0'), col('Quarter', 'string'),
    col('Month No', 'int64', fmt='0', hidden=True), col('Month', 'string', sort_by='Month No'),
    col('Year Month', 'string', sort_by='Month Start'), col('Month Start', 'dateTime', fmt='mmm yy'),
    col('In Trend Window', 'int64', fmt='0', hidden=True),
], '''let
    StartDate = #date(2016, 9, 1),
    EndDate = #date(2018, 10, 31),
    Dates = List.Dates(StartDate, Duration.Days(EndDate - StartDate) + 1, #duration(1, 0, 0, 0)),
    Base = Table.FromList(Dates, Splitter.SplitByNothing(), {"Date"}),
    Typed = Table.TransformColumnTypes(Base, {{"Date", type date}}),
    AddYear = Table.AddColumn(Typed, "Year", each Date.Year([Date]), Int64.Type),
    AddQuarter = Table.AddColumn(AddYear, "Quarter", each "Q" & Text.From(Date.QuarterOfYear([Date])), type text),
    AddMonthNo = Table.AddColumn(AddQuarter, "Month No", each Date.Month([Date]), Int64.Type),
    AddMonth = Table.AddColumn(AddMonthNo, "Month", each Date.ToText([Date], "MMM", "en-US"), type text),
    AddYearMonth = Table.AddColumn(AddMonth, "Year Month", each Date.ToText([Date], "MMM yyyy", "en-US"), type text),
    AddMonthStart = Table.AddColumn(AddYearMonth, "Month Start", each Date.StartOfMonth([Date]), type date),
    AddWindow = Table.AddColumn(AddMonthStart, "In Trend Window", each if [Date] >= #date(2017, 1, 1) and [Date] <= #date(2018, 8, 31) then 1 else 0, Int64.Type)
in
    AddWindow''', category='Time')

states = [('AC', 'Acre', 'North'), ('AP', 'Amapá', 'North'), ('AM', 'Amazonas', 'North'), ('PA', 'Pará', 'North'),
          ('RO', 'Rondônia', 'North'), ('RR', 'Roraima', 'North'), ('TO', 'Tocantins', 'North'),
          ('AL', 'Alagoas', 'Northeast'), ('BA', 'Bahia', 'Northeast'), ('CE', 'Ceará', 'Northeast'),
          ('MA', 'Maranhão', 'Northeast'), ('PB', 'Paraíba', 'Northeast'), ('PE', 'Pernambuco', 'Northeast'),
          ('PI', 'Piauí', 'Northeast'), ('RN', 'Rio Grande do Norte', 'Northeast'), ('SE', 'Sergipe', 'Northeast'),
          ('DF', 'Distrito Federal', 'Central-West'), ('GO', 'Goiás', 'Central-West'), ('MT', 'Mato Grosso', 'Central-West'),
          ('MS', 'Mato Grosso do Sul', 'Central-West'), ('ES', 'Espírito Santo', 'Southeast'), ('MG', 'Minas Gerais', 'Southeast'),
          ('RJ', 'Rio de Janeiro', 'Southeast'), ('SP', 'São Paulo', 'Southeast'), ('PR', 'Paraná', 'South'),
          ('RS', 'Rio Grande do Sul', 'South'), ('SC', 'Santa Catarina', 'South')]
rows = ', '.join('{"%s", "%s", "%s"}' % s for s in states)
dim_state = table('dim_state', [col('State Code', 'string'), col('State', 'string', category='StateOrProvince'), col('Region', 'string')],
                  f'''let
    Source = #table(type table [State Code = text, State = text, Region = text], {{{rows}}})
in
    Source''')

dim_bm = table('dim_bm', [col('Benchmark', 'string', sort_by='BM Order'), col('BM Order', 'int64', fmt='0', hidden=True)],
               '''let
    Source = #table(type table [Benchmark = text, BM Order = Int64.Type], {{"vs LY", 1}, {"vs Target", 2}})
in
    Source''')
dim_metric = table('dim_metric', [col('Metric', 'string', sort_by='Metric Order'), col('Metric Order', 'int64', fmt='0', hidden=True)],
                   '''let
    Source = #table(type table [Metric = text, Metric Order = Int64.Type], {{"Late %", 1}, {"Avg Review", 2}, {"Bad Review %", 3}, {"Avg Days to Deliver", 4}})
in
    Source''')
checks = [(1, 'Delivered orders with a date', 96470, '01_views.sql: delivered'), (2, 'Delivered orders with a review', 95824, 'Q1'),
          (3, 'Late orders (with a review)', 6381, 'Q1'), (4, 'Avg review: late orders', 2.27, 'Q1'),
          (5, 'Avg review: on-time orders', 4.29, 'Q1'), (6, '1-2 star share: late orders', 0.624, 'Q1'),
          (7, 'Late orders: seller handed over on time', 0.723, 'Q6'), (8, 'Late orders on SP -> RJ lane', 0.177, 'Q10'),
          (9, 'Late orders: worst seller decile', 0.156, 'Q5'), (10, 'Median days early vs promise', 12, 'Q9'),
          (11, 'Late order value (R$ M)', 1.15, 'Q9'), (12, 'Repeat rate: first order late', 0.0233, 'Q7')]
crow = ', '.join('{%d, "%s", %s, "%s"}' % c for c in checks)
sql_check = table('sql_check', [col('Check No', 'int64', fmt='0'), col('Check', 'string'),
                                col('SQL Value', 'double', fmt='0.####'), col('SQL Source', 'string')],
                  f'''let
    Source = #table(type table [Check No = Int64.Type, Check = text, SQL Value = number, SQL Source = text], {{{crow}}})
in
    Source''')
top_n = table('Top N', [col('Top N', 'int64', fmt='0')], '''let
    Source = #table(type table [Top N = Int64.Type], {{5}, {10}, {15}, {20}, {25}})
in
    Source''')

# ---------------- measures from measures.dax ----------------
src = open(DAX, encoding='utf-8').read()
body = src[src.index('// 3. MEASURES'):]
folder = ''
measures = []
cur = None
SKIP_START = ('VAR ', 'RETURN', 'CALCULATE', 'SUMX', 'IF ', 'DIVIDE', 'SWITCH', 'FORMAT', 'RANKX', 'FILTER', 'ADDCOLUMNS', 'SELECTED')
def strip_comment(line):
    out, q = [], False
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == '"': q = not q
        if not q and line[i:i+2] == '//': break
        out.append(ch); i += 1
    return ''.join(out).rstrip()
for raw in body.split('\n'):
    fm = re.match(r'// \[(\d+) ([^\]]+)\]', raw)
    if fm:
        folder = f'{fm.group(1)} {fm.group(2)}'; cur = None; continue
    if raw.startswith('//') or not raw.strip():
        if raw.startswith('//'): cur = None if not raw.startswith('//   ') else cur
        continue
    line = strip_comment(raw)
    if not line.strip(): continue
    m = re.match(r'^([A-Za-z][^=\[]*?) =\s*(.*)$', line)
    if m and not line.startswith(SKIP_START) and not line.startswith(' '):
        cur = {'name': m.group(1).strip(), 'expr': [m.group(2)] if m.group(2) else [], 'folder': folder}
        measures.append(cur)
    elif cur is not None:
        cur['expr'].append(line)
measures.append({'name': 'Top N Value', 'expr': ["SELECTEDVALUE ( 'Top N'[Top N], 10 )"], 'folder': '5 Sellers & Lanes'})

def fmt_for(n):
    if n.startswith(('COLOR', 'Callout', 'Selected', 'Metric Title', 'Trend Title', 'Last Data', 'Selection', 'Headline', 'Check Status', 'Checks Summary', 'Seller Risk')): return None
    if n == 'LY Cutoff': return 'dd mmm yyyy'
    if '(pp)' in n: return '+0.0;-0.0;0.0'
    if n.startswith('Repeat Rate'): return '0.00%'
    if n in ('PBI Value', 'SQL Value'): return '0.####'
    if n in ('Order Value', 'Late Order Value'): return '"R$" #,0'
    if '%' in n or 'Share' in n: return '0.0%'
    if n.startswith('Avg Review') or n in ('Review Gap', 'Seller Avg Review', 'Avg Review Chg', 'Avg Review Target', 'Avg Review BM'): return '0.00'
    if n.startswith(('Avg Days', 'Lane Avg Days', 'Promise Buffer')) or n == 'Avg Days Chg': return '0.0'
    if n == 'Median Days Early': return '0'
    if n in ('Show In Top N', 'Show State Top5', 'Show Lane Top5', 'Checks Passed', 'Top N Value'): return '0'
    return '#,0'

tm = []
for m in measures:
    expr = '\n'.join(m['expr']).strip()
    for a, b in RECOLOR.items(): expr = expr.replace(a, b)
    d = {'name': m['name'], 'expression': expr.split('\n'), 'lineageTag': lt(), 'displayFolder': m['folder']}
    f = fmt_for(m['name'])
    if f: d['formatString'] = f
    if m['name'] == 'Metric Value':
        d.pop('formatString', None)
        d['formatStringDefinition'] = {'expression': 'SWITCH ( [Selected Metric], "Avg Review", "0.00", "Avg Days to Deliver", "0.0", "0.0%" )'}
    tm.append(d)

measures_tbl = table('_Measures', [col('Column1', 'string', hidden=True)], '''let
    Source = #table(type table [Column1 = text], {})
in
    Source''', measures=tm)

tables = [measures_tbl, fact_delivery, fos, dim_seller, first_order, dim_date, dim_state, dim_bm, dim_metric, sql_check, top_n]

def rel(f_t, f_c, t_t, t_c, one_to_one=False):
    r = {'name': lt(), 'fromTable': f_t, 'fromColumn': f_c, 'toTable': t_t, 'toColumn': t_c}
    if one_to_one:
        r['fromCardinality'] = 'one'; r['crossFilteringBehavior'] = 'bothDirections'
    return r
relationships = [
    rel('fact_delivery', 'purchase_date', 'dim_date', 'Date'),
    rel('fact_delivery', 'customer_state', 'dim_state', 'State Code'),
    rel('fact_order_seller', 'order_id', 'fact_delivery', 'order_id'),
    rel('fact_order_seller', 'seller_id', 'dim_seller', 'seller_id'),
    rel('first_order', 'first_order_id', 'fact_delivery', 'order_id', one_to_one=True),
]

model = {
    'name': lt(),
    'compatibilityLevel': 1601,
    'model': {
        'culture': 'en-US',
        'dataAccessOptions': {'legacyRedirects': True, 'returnErrorValuesAsNull': True},
        'defaultPowerBIDataSourceVersion': 'powerBI_V3',
        'sourceQueryCulture': 'en-US',
        'tables': tables,
        'relationships': relationships,
        'expressions': [{
            'name': 'DataFolder', 'kind': 'm', 'lineageTag': lt(),
            'expression': ['"C:\\olist\\Olist_Delivery_360\\data\\" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]'],
            'annotations': [{'name': 'PBI_ResultType', 'value': 'Text'}, {'name': 'PBI_NavigationStepName', 'value': 'Navigation'}]}],
        'annotations': [
            {'name': 'PBI_QueryOrder', 'value': json.dumps(['DataFolder'] + [t['name'] for t in tables])},
            {'name': '__PBI_TimeIntelligenceEnabled', 'value': '0'}],
    }
}
if __name__ == '__main__':
    print(len(tm), 'measures'); print([m['name'] for m in tm])
