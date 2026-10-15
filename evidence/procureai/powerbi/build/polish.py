"""Polish pages 09-11: hide auto titles, fit table columns, shorter category names."""
import csv, json, sys
from pathlib import Path
R = Path(sys.argv[1])
P = R / 'ProcureAI_FMCG.Report/definition/pages'
L = lambda v: {'expr': {'Literal': {'Value': v}}}
WIDTHS = {  # queryRef -> width
    'Invoice Risk Scores.invoice_id': 78, 'Supplier.supplier_name': 150, 'Invoice Risk Scores.invoice_date': 72,
    'Invoice Risk Scores.gross_amount': 78, 'Invoice Risk Scores.model_score': 46, 'Invoice Risk Scores.condition': 110,
    'Invoice Risk Scores.Rules Say': 46,
    'PO Delay Scores.po_id': 80, 'Warehouse.warehouse_name': 92, 'PO Delay Scores.promised_date': 78,
    'PO Delay Scores.p_pre': 48, 'PO Delay Scores.Delivery Outcome': 66,
    'Contract QA.question': 205, 'Contract QA.result': 92, 'Contract QA.answer': 205, 'Contract QA.citation': 80,
}
n = 0
for page in ('ReportSection09mdlinvoice', 'ReportSection10mdldelay', 'ReportSection11mdlcontract'):
    for vf in (P / page / 'visuals').glob('*/visual.json'):
        v = json.loads(vf.read_text(encoding='utf-8')); vis = v['visual']; t = vis['visualType']
        if t in ('actionButton', 'card'): continue
        vis.setdefault('visualContainerObjects', {})['title'] = [{'properties': {'show': L('false')}}]
        if t == 'tableEx':
            proj = vis['query']['queryState']['Values']['projections']
            if page.startswith('ReportSection10'):
                proj[:] = [p for p in proj if p['queryRef'] != 'PO Delay Scores.route_type']
                if 'filterConfig' in v:
                    v['filterConfig']['filters'] = [f for f in v['filterConfig']['filters'] if 'route_type' not in json.dumps(f['field'])]
            if page.startswith('ReportSection10'):
                WIDTHS['Supplier.supplier_name'] = 180
            objs = vis['objects']
            objs['values'][0]['properties']['wordWrap'] = L('true')
            objs['columnWidth'] = [{'properties': {'value': L(f'{WIDTHS[p["queryRef"]]}D')}, 'selector': {'metadata': p['queryRef']}}
                                   for p in proj if p['queryRef'] in WIDTHS]
            WIDTHS['Supplier.supplier_name'] = 150
        if t == 'clusteredBarChart' and page.startswith('ReportSection09'):
            vis['query']['sortDefinition'] = {'sort': [{'field': {'Measure': {'Expression': {'SourceRef': {'Entity': 'Invoice Risk Scores'}}, 'Property': 'Rules Caught %'}},
                                                         'direction': 'Ascending'}], 'isDefaultSort': False}
        if t in ('clusteredBarChart', 'clusteredColumnChart'):
            vis['objects']['categoryAxis'] = [{'properties': {'labelColor': {'solid': {'color': L("'#c6cfdb'")}}, 'fontSize': L('9D'),
                                                              'showAxisTitle': L('false'), 'maxMarginFactor': L('40L')}}]
        vf.write_text(json.dumps(v, ensure_ascii=False, indent=2), encoding='utf-8'); n += 1
SHORT = {'Bank detail change': 'Bank change', 'Exact duplicate': 'Exact duplicate', 'Missing PO': 'Missing PO',
         'Price over tolerance': 'Price > tolerance', 'Quantity over order': 'Qty > order', 'Near-duplicate': 'Near-duplicate',
         'Split below approval': 'Split bills', 'Price creep': 'Price creep',
         'Supplier load vs capacity': 'Supplier load', 'Promised vs quoted lead time': 'Promise vs quote', 'Festival calendar': 'Festivals',
         'Order size vs usual': 'Order size', 'Distance and route': 'Distance, route', 'Flood-risk history': 'Flood history'}
for f in ('invoice_condition_catch.csv', 'delay_drivers.csv'):
    p = R / 'model_results' / f
    rows = list(csv.reader(open(p, encoding='utf-8')))
    rows = [rows[0]] + [[SHORT.get(r[0], r[0])] + r[1:] for r in rows[1:]]
    with open(p, 'w', newline='', encoding='utf-8') as fh: csv.writer(fh).writerows(rows)
print('visuals updated', n)
