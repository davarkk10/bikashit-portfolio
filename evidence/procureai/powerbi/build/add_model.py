"""Add the October 2026 model-result tables, measures and relationships to the
ProcureAI_FMCG semantic model (TMDL). Run on a copy of the PBIP folder.

Usage: python add_model.py <pbip folder> <model_results data folder on the user's PC>
"""
import csv
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(sys.argv[1])
PC_FOLDER = sys.argv[2]
DEF = ROOT / 'ProcureAI_FMCG.SemanticModel' / 'definition'
DATA = ROOT / 'model_results'
NS = uuid.UUID('6f1d0c1e-5c55-4bb4-9e0e-1a2b3c4d5e6f')
lt = lambda key: str(uuid.uuid5(NS, key))
FOLDER = 'Model results'
M_TYPE = {'string': 'type text', 'int64': 'Int64.Type', 'double': 'type number', 'dateTime': 'type date'}


def q(name):
    return f"'{name}'" if re.search(r'[^A-Za-z0-9_]', name) else name


def table_tmdl(name, file, cols, measures=(), calcs=(), nullable=()):
    """cols: (column, dataType, formatString or None, hidden)."""
    out = [f'table {q(name)}', f'\tlineageTag: {lt(name)}', '']
    for mname, expr, fmt, desc in measures:
        out.append(f'\t/// {desc}')
        out.append(f'\tmeasure {q(mname)} = {expr}')
        if fmt: out.append(f'\t\tformatString: {fmt}')
        out += [f'\t\tdisplayFolder: {FOLDER}', f'\t\tlineageTag: {lt(name + "/m/" + mname)}', '']
    for c, dt, fmt, hidden in cols:
        out.append(f'\tcolumn {q(c)}')
        out.append(f'\t\tdataType: {dt}')
        if fmt: out.append(f'\t\tformatString: {fmt}')
        if hidden: out.append('\t\tisHidden')
        out += [f'\t\tlineageTag: {lt(name + "/c/" + c)}', '\t\tsummarizeBy: none', f'\t\tsourceColumn: {c}', '',
                '\t\tannotation SummarizationSetBy = Automatic', '']
        if dt == 'dateTime':
            out.insert(-1, '\t\tannotation UnderlyingDateTimeDataType = Date')
            out.insert(-1, '')
    for c, expr, dt, fmt, sort_by in calcs:
        out.append(f'\tcolumn {q(c)} = {expr}')
        out.append(f'\t\tdataType: {dt}')
        if fmt: out.append(f'\t\tformatString: {fmt}')
        out += [f'\t\tlineageTag: {lt(name + "/cc/" + c)}', '\t\tsummarizeBy: none']
        if sort_by: out.append(f'\t\tsortByColumn: {q(sort_by)}')
        out += ['', '\t\tannotation SummarizationSetBy = Automatic', '']
    types = ', '.join('{"%s", %s}' % (c, M_TYPE[dt]) for c, dt, _, _ in cols)
    nulls = ', '.join('"%s"' % c for c in nullable)
    m = [f"// Power Query M — table '{name}'. Model results, October 2026 rebuild. Parameter: pModelFolder",
         'let',
         f'    Source = Csv.Document(File.Contents(pModelFolder & "\\{file}"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
         '    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),',
         (f'    Nulls = Table.ReplaceValue(Promoted, "", null, Replacer.ReplaceValue, {{{nulls}}}),' if nullable else '    Nulls = Promoted,'),
         f'    Typed = Table.TransformColumnTypes(Nulls, {{{types}}}, "en-US")',
         'in',
         '    Typed']
    out += [f'\tpartition {q(name)} = m', '\t\tmode: import', '\t\tsource ='] + ['\t\t\t\t' + l for l in m] + ['']
    # sanity: column list must equal CSV header
    with open(DATA / file, encoding='utf-8') as fh:
        header = next(csv.reader(fh))
    assert header == [c for c, *_ in cols], (name, header)
    return '\n'.join(out) + '\n'


MR = "'Model Results'"
def R(area, metric, role=None, method=None):
    f = [f'{MR}[area] = "{area}"', f'{MR}[metric] = "{metric}"']
    if role: f.append(f'{MR}[role] = "{role}"')
    if method: f.append(f'{MR}[method] = "{method}"')
    return f'CALCULATE ( MAX ( {MR}[value] ), ' + ', '.join(f) + ' )'


IRS, PDS, CQA = "'Invoice Risk Scores'", "'PO Delay Scores'", "'Contract QA'"
PCT, D2 = '0.0%', '0.00'

TABLES = {
    'Invoice Risk Scores': table_tmdl('Invoice Risk Scores', 'invoice_risk_scores.csv', [
        ('invoice_id', 'string', None, False), ('invoice_date', 'dateTime', 'dd mmm yyyy', False), ('date_key', 'int64', '0', True),
        ('supplier_id', 'string', None, True), ('po_id', 'string', None, False), ('gross_amount', 'double', '₹ #,##0', False),
        ('rules_policy', 'int64', '0', False), ('rules_refined', 'int64', '0', False), ('max_price_var', 'double', '0.0%', False),
        ('supplier_price_drift_120d', 'double', '0.00%', False), ('prior_inv_same_po', 'int64', '0', False),
        ('similar_number_seen', 'int64', '0', False), ('split', 'string', None, False), ('model_score', 'double', '0.000', False),
        ('model_flag', 'int64', '0', False), ('condition', 'string', None, False), ('condition_group', 'string', None, False),
        ('is_condition', 'int64', '0', False)],
        measures=[
            ('Invoice Model PR-AUC (hard cases)', R('Invoice risk', 'pr_auc_hard', role='Model'), D2, 'Gradient-boosted model PR-AUC on the three hard conditions (test window, Python evaluation).'),
            ('Invoice Rules PR-AUC (hard cases)', R('Invoice risk', 'pr_auc_hard', method='Best hand-written rules'), D2, 'Best hand-written rules PR-AUC on the hard conditions.'),
            ('Invoice Test Conditions', f'CALCULATE ( COUNTROWS ( {IRS} ), {IRS}[split] = "Test", {IRS}[is_condition] = 1 )', '#,##0', 'Invoices in the test window that carry an injected condition.'),
            ('Model Flagged Invoices', f'CALCULATE ( COUNTROWS ( {IRS} ), {IRS}[model_flag] = 1 )', '#,##0', 'Test invoices the model sends for review (review capacity).'),
            ('Model Hits', f'CALCULATE ( COUNTROWS ( {IRS} ), {IRS}[model_flag] = 1, {IRS}[is_condition] = 1 )', '#,##0', 'Flagged invoices that carry a real condition.'),
            ('Model Precision', 'DIVIDE ( [Model Hits], [Model Flagged Invoices] )', PCT, 'Share of model flags that are real.'),
            ('Model Recall', 'DIVIDE ( [Model Hits], [Invoice Test Conditions] )', PCT, 'Share of real conditions the model flags.'),
            ('Rules Flagged Invoices', '[Invoice Test Conditions]', '#,##0', 'Invoices the best hand-written rules send for review: the same capacity as the model (one per real condition in test).'),
            ('Rules Hits', 'ROUND ( [Rules Precision] * [Rules Flagged Invoices], 0 )', '#,##0', 'Real conditions among the invoices the rules rank highest, at the same review capacity as the model.'),
            ('Rules Precision', 'CALCULATE ( MAX ( \'Model Results\'[value] ), \'Model Results\'[area] = "Invoice risk", \'Model Results\'[metric] = "precision_at_capacity", \'Model Results\'[method] = "Best hand-written rules" )', PCT, 'Share of the invoices the best rules rank highest that are real, at the same review capacity as the model (from the model run; the rule score is not in the scored rows).'),
            ('Rules Recall', 'DIVIDE ( [Rules Hits], [Invoice Test Conditions] )', PCT, 'Share of real conditions the rules catch at the same review capacity (equals precision, since capacity = number of conditions).'),
            ('Rules Caught %', "AVERAGE ( 'Invoice Condition Catch'[rules_caught] )", PCT, 'Share of each condition the best rules catch.'),
            ('Model Caught %', "AVERAGE ( 'Invoice Condition Catch'[model_caught] )", PCT, 'Share of each condition the model catches at review capacity.'),
        ],
        calcs=[('Model Says', f'IF ( {IRS}[model_flag] = 1, "Review", "Pass" )', 'string', None, None),
               ('Rules Say', f'IF ( {IRS}[rules_refined] = 1, "Flag", "Pass" )', 'string', None, None)],
        nullable=['po_id', 'model_score', 'max_price_var']),

    'PO Delay Scores': table_tmdl('PO Delay Scores', 'po_delay_scores.csv', [
        ('po_id', 'string', None, False), ('order_date_key', 'int64', '0', True), ('order_date', 'dateTime', 'dd mmm yyyy', False),
        ('promised_date', 'dateTime', 'dd mmm yyyy', False), ('receipt_date', 'dateTime', 'dd mmm yyyy', False),
        ('supplier_id', 'string', None, True), ('warehouse_id', 'string', None, True), ('po_value', 'double', '₹ #,##0', False),
        ('late', 'int64', '0', False), ('lead_days', 'int64', '0', False), ('quoted_lead_time_days', 'int64', '0', False),
        ('promise_slack_days', 'int64', '0', False), ('road_distance_km', 'double', '#,##0', False), ('route_type', 'string', None, False),
        ('utilisation', 'double', '0.00', False), ('festival_window', 'int64', '0', False), ('dest_flood_risk', 'double', '0.00', False),
        ('dispatched_by_rescore', 'int64', '0', False), ('dispatch_slip_seen', 'int64', '0', False), ('advisory', 'int64', '0', False),
        ('supplier_past_late_rate', 'double', '0.0%', False), ('split', 'string', None, False), ('p_order', 'double', '0.000', False),
        ('p_pre', 'double', '0.000', False), ('flag_order', 'int64', '0', False), ('flag_pre', 'int64', '0', False)],
        measures=[
            ('Delay Baseline PR-AUC', R('Late delivery', 'pr_auc', role='Baseline'), D2, "Each supplier's past late rate used as the score."),
            ('Delay PR-AUC (order time)', R('Late delivery', 'pr_auc', method='Logistic regression, order time'), D2, 'Logistic regression scored when the PO is raised.'),
            ('Delay PR-AUC (3 days out)', R('Late delivery', 'pr_auc', method='Logistic regression, 3 days before'), D2, 'Logistic regression re-scored 3 days before the promised date.'),
            ('PO Late %', f'DIVIDE ( SUM ( {PDS}[late] ), COUNTROWS ( {PDS} ) )', PCT, 'Share of POs received after the promised date.'),
            ('Test PO Late %', f'CALCULATE ( [PO Late %], {PDS}[split] = "Test" )', PCT, 'Late rate in the test window (Jul–Dec 2025).'),
            ('Avg Predicted Late Risk', f'AVERAGE ( {PDS}[p_order] )', PCT, 'Average order-time predicted probability of a late delivery.'),
            ('Flagged PO Late % (3 days out)', f'CALCULATE ( [PO Late %], {PDS}[flag_pre] = 1 )', PCT, 'Of the top 25% flagged 3 days out, the share that arrive late.'),
            ('Late POs Caught (3 days out)', f'DIVIDE ( CALCULATE ( SUM ( {PDS}[late] ), {PDS}[flag_pre] = 1 ), CALCULATE ( SUM ( {PDS}[late] ), {PDS}[split] = "Test" ) )', PCT, 'Share of late test POs inside the flagged top 25%.'),
            ('Delay Driver Importance', "SUM ( 'Delay Drivers'[pr_auc_lost_when_removed] )", '0.000', 'Validation PR-AUC lost when the driver is removed.'),
        ],
        calcs=[('Delivery Outcome', f'IF ( {PDS}[late] = 1, "Late", "On time" )', 'string', None, None),
               ('Supplier Load Band', f'SWITCH ( TRUE (), {PDS}[utilisation] < 0.8, "Under 80%", {PDS}[utilisation] < 1.0, "80–100%", {PDS}[utilisation] < 1.2, "100–120%", "Over 120%" )', 'string', None, 'Supplier Load Order'),
               ('Supplier Load Order', f'SWITCH ( TRUE (), {PDS}[utilisation] < 0.8, 1, {PDS}[utilisation] < 1.0, 2, {PDS}[utilisation] < 1.2, 3, 4 )', 'int64', '0', None)],
        nullable=['p_order', 'p_pre']),

    'Model Results': table_tmdl('Model Results', 'model_results.csv', [
        ('area', 'string', None, False), ('method', 'string', None, False), ('role', 'string', None, False),
        ('method_order', 'int64', '0', True), ('metric', 'string', None, False), ('value', 'double', '0.000', False)]),
    'Invoice Condition Catch': table_tmdl('Invoice Condition Catch', 'invoice_condition_catch.csv', [
        ('condition', 'string', None, False), ('condition_group', 'string', None, False), ('test_cases', 'int64', '#,##0', False),
        ('rules_caught', 'double', '0.0%', False), ('model_caught', 'double', '0.0%', False)]),
    'Delay Drivers': table_tmdl('Delay Drivers', 'delay_drivers.csv', [
        ('driver', 'string', None, False), ('pr_auc_lost_when_removed', 'double', '0.000', False)]),
    'Contract QA': table_tmdl('Contract QA', 'contract_qa.csv', [
        ('question_no', 'int64', '0', False), ('question', 'string', None, False), ('question_type', 'string', None, False),
        ('answerable', 'int64', '0', False), ('result', 'string', None, False), ('is_correct', 'int64', '0', False),
        ('answer', 'string', None, False), ('citation', 'string', None, False)],
        measures=[
            ('Contract Questions', f'COUNTROWS ( {CQA} )', '#,##0', 'Questions in the locked unseen set.'),
            ('Contract Correct', f'SUM ( {CQA}[is_correct] )', '#,##0', 'Correct answers plus correct refusals.'),
            ('Contract Accuracy', 'DIVIDE ( [Contract Correct], [Contract Questions] )', PCT, 'Share answered correctly.'),
            ('Contract Score', 'FORMAT ( [Contract Correct], "0" ) & " / " & FORMAT ( [Contract Questions], "0" )', None, 'Correct out of total, as text.'),
            ('Contract Wrong Answers', f'CALCULATE ( COUNTROWS ( {CQA} ), {CQA}[result] = "Wrong answer" ) + 0', '0', 'Answers given that were wrong.'),
            ('Contract Refusals Correct', f'FORMAT ( CALCULATE ( SUM ( {CQA}[is_correct] ), {CQA}[answerable] = 0 ), "0" ) & " / " & FORMAT ( CALCULATE ( COUNTROWS ( {CQA} ), {CQA}[answerable] = 0 ), "0" )', None, 'Unanswerable questions correctly refused.'),
        ], nullable=['citation']),
}
for name, body in TABLES.items():
    (DEF / 'tables' / f'{name}.tmdl').write_text(body, encoding='utf-8')

# parameter
exp = (DEF / 'expressions.tmdl').read_text(encoding='utf-8')
if 'pModelFolder' not in exp:
    exp = exp.rstrip('\n') + '\n\n' + (
        f'expression pModelFolder = "{PC_FOLDER}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]\n'
        f'\tlineageTag: {lt("pModelFolder")}\n\n\tannotation PBI_ResultType = Text\n\n')
    (DEF / 'expressions.tmdl').write_text(exp, encoding='utf-8')

# relationships
rels = [('r90_invoicerisk_date_key', "'Invoice Risk Scores'.date_key", 'Date.date_key'),
        ('r91_invoicerisk_supplier_id', "'Invoice Risk Scores'.supplier_id", 'Supplier.supplier_id'),
        ('r92_podelay_order_date_key', "'PO Delay Scores'.order_date_key", 'Date.date_key'),
        ('r93_podelay_supplier_id', "'PO Delay Scores'.supplier_id", 'Supplier.supplier_id'),
        ('r94_podelay_warehouse_id', "'PO Delay Scores'.warehouse_id", 'Warehouse.warehouse_id')]
rt = (DEF / 'relationships.tmdl').read_text(encoding='utf-8')
for n, f, t in rels:
    if n not in rt:
        rt = rt.rstrip('\n') + f'\n\nrelationship {n}\n\tfromColumn: {f}\n\ttoColumn: {t}\n'
(DEF / 'relationships.tmdl').write_text(rt, encoding='utf-8')

# model.tmdl: table refs + query order
mt = (DEF / 'model.tmdl').read_text(encoding='utf-8')
new = list(TABLES)
m = re.search(r'annotation PBI_QueryOrder = (\[.*\])', mt)
import json
order = json.loads(m.group(1))
for p in ['pModelFolder']:
    if p not in order: order.insert(order.index('pCsvFolder') + 1, p)
for t in new:
    if t not in order: order.append(t)
mt = mt.replace(m.group(0), 'annotation PBI_QueryOrder = ' + json.dumps(order, ensure_ascii=False))
anchor = "ref table 'Security Scope'\n"
assert anchor in mt
refs = ''.join(f'ref table {q(t)}\n' for t in new if f'ref table {q(t)}\n' not in mt)
mt = mt.replace(anchor, anchor + refs)
(DEF / 'model.tmdl').write_text(mt, encoding='utf-8')
print('added', len(new), 'tables,', sum(b.count('\tmeasure ') for b in TABLES.values()), 'measures,', len(rels), 'relationships')
