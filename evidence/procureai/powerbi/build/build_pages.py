"""Add pages 09-11 (model results) to the ProcureAI_FMCG report and extend the side menu on every page.

Usage: python build_pages.py <pbip folder>
"""
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
import bg_render as B  # noqa: E402

ROOT = Path(sys.argv[1])
REP = ROOT / 'ProcureAI_FMCG.Report'
PAGES_DIR = REP / 'definition' / 'pages'
RES = REP / 'StaticResources' / 'RegisteredResources'
SV = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.12.0/schema.json'
SP = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json'

pages_meta = json.loads((PAGES_DIR / 'pages.json').read_text(encoding='utf-8'))
OLD = pages_meta['pageOrder'][:9]
NEW = {9: ('ReportSection09mdlinvoice', '09 Invoice risk model', 'bg_09_invoice_model.png'),
       10: ('ReportSection10mdldelay', '10 Late-delivery model', 'bg_10_delay_model.png'),
       11: ('ReportSection11mdlcontract', '11 Contract assistant', 'bg_11_contract_assistant.png')}
ORDER = OLD + [NEW[i][0] for i in (9, 10, 11)]


def nid(*parts):
    return hashlib.sha1('/'.join(map(str, parts)).encode()).hexdigest()[:20]


def L(v):
    if isinstance(v, bool): s = 'true' if v else 'false'
    elif isinstance(v, int): s = f'{v}L'
    elif isinstance(v, float): s = f'{v}D'
    else: s = "'" + str(v).replace("'", "''") + "'"
    return {'expr': {'Literal': {'Value': s}}}


def D(v): return {'expr': {'Literal': {'Value': f'{v}D'}}}
def C(hexv): return {'solid': {'color': L(hexv)}}
def props(**kw): return {'properties': kw}
def MEAS(entity, name): return {'Measure': {'Expression': {'SourceRef': {'Entity': entity}}, 'Property': name}}
def COL(entity, name): return {'Column': {'Expression': {'SourceRef': {'Entity': entity}}, 'Property': name}}


def proj(f, display=None, active=False):
    k = 'Measure' if 'Measure' in f else 'Column'
    e, n = f[k]['Expression']['SourceRef']['Entity'], f[k]['Property']
    p = {'field': f, 'queryRef': f'{e}.{n}', 'nativeQueryRef': n}
    if display: p['displayName'] = display
    if active: p['active'] = True
    return p


def container(page, x, y, w, h, z, vtype, query=None, objects=None, alt='', filters=None, vco_extra=None):
    v = {'visualType': vtype}
    if query: v['query'] = query
    v['objects'] = objects or {}
    vco = {'general': [props(altText=L(alt))]} if alt else {}
    if vco_extra: vco.update(vco_extra)
    v['visualContainerObjects'] = vco
    v['drillFilterOtherVisuals'] = True
    out = {'$schema': SV, 'name': nid(page, vtype, x, y), 'position': {'x': x, 'y': y, 'z': z, 'height': h, 'width': w, 'tabOrder': z}, 'visual': v}
    if filters: out['filterConfig'] = {'filters': filters}
    return out


def f_in(entity, col, values):
    return {'name': nid('f', entity, col, *values), 'field': COL(entity, col), 'type': 'Categorical',
            'filter': {'Version': 2, 'From': [{'Name': 't', 'Entity': entity, 'Type': 0}],
                       'Where': [{'Condition': {'In': {'Expressions': [{'Column': {'Expression': {'SourceRef': {'Source': 't'}}, 'Property': col}}],
                                                       'Values': [[{'Literal': {'Value': f'{v}L' if isinstance(v, int) else "'" + v + "'"}}] for v in values]}}}]},
            'howCreated': 'User'}


def card(page, x, y, w, h, z, entity, measure, color, alt):
    return container(page, x, y, w, h, z, 'card', {'queryState': {'Values': {'projections': [proj(MEAS(entity, measure))]}}},
                     {'labels': [props(color=C(color), fontSize=D(20), fontFamily=L('Segoe UI Semibold'), labelDisplayUnits=D(1))],
                      'categoryLabels': [props(show=L(False))]}, alt)


def nav_button(page, idx, target, label):
    y = B.NAV_Y[idx] - 16
    return {'$schema': SV, 'name': nid(page, 'nav', idx), 'position': {'x': 12, 'y': y, 'z': 7000 + idx, 'height': 32, 'width': 168, 'tabOrder': 7000 + idx},
            'visual': {'visualType': 'actionButton', 'objects': {
                'icon': [{'properties': {'shapeType': L('blank')}, 'selector': {'id': 'default'}}],
                'outline': [props(show=L(False))], 'text': [props(show=L(False))],
                'fill': [{'properties': {'show': L(True), 'fillColor': C('#9cff1e'), 'transparency': D(100)}, 'selector': {'id': 'default'}},
                         {'properties': {'show': L(True), 'fillColor': C('#9cff1e'), 'transparency': D(88)}, 'selector': {'id': 'hover'}}]},
                'visualContainerObjects': {
                    'visualLink': [props(show=L(True), type=L('PageNavigation'), navigationSection=L(target))],
                    'visualTooltip': [props(show=L(True))], 'general': [props(altText=L(label))]},
                'drillFilterOtherVisuals': True}}


AX = lambda: [props(labelColor=C('#c6cfdb'), fontSize=D(9), showAxisTitle=L(False))]
VOFF = lambda: [props(show=L(False), gridlineShow=L(False))]
LAB = lambda: [props(show=L(True), color=C('#c6cfdb'), fontSize=D(8), labelDisplayUnits=D(1))]


def chart(page, x, y, w, h, z, vtype, roles, objects, alt, filters=None, sort=None):
    qs = {r: {'projections': [proj(f, d, active=(i == 0 and r == 'Category')) for i, (f, d) in enumerate(fs)]} for r, fs in roles.items()}
    q = {'queryState': qs}
    if sort: q['sortDefinition'] = {'sort': [{'field': sort[0], 'direction': sort[1]}], 'isDefaultSort': False}
    return container(page, x, y, w, h, z, vtype, q, objects, alt, filters)


def table(page, x, y, w, h, z, cols, alt, filters=None, sort=None):
    q = {'queryState': {'Values': {'projections': [proj(f, d) for f, d in cols]}}}
    if sort: q['sortDefinition'] = {'sort': [{'field': sort[0], 'direction': sort[1]}], 'isDefaultSort': False}
    objs = {'columnHeaders': [props(fontColor=C('#7f8ba0'), backColor=C('#0c1524'), fontSize=D(9))],
            'values': [props(fontColorPrimary=C('#e6ebf3'), backColorPrimary=C('#101a2b'), fontColorSecondary=C('#e6ebf3'),
                             backColorSecondary=C('#0e1828'), fontSize=D(9))],
            'grid': [props(gridVertical=L(False), gridHorizontalColor=C('#1d2940'), outlineColor=C('#1d2940'), rowPadding=D(3))],
            'total': [props(totals=L(False))]}
    return container(page, x, y, w, h, z, 'tableEx', q, objs, alt, filters)


def slicer(page, x, y, w, h, z, entity, col, alt):
    return container(page, x, y, w, h, z, 'slicer', {'queryState': {'Values': {'projections': [proj(COL(entity, col), active=True)]}}},
                     {'data': [props(mode=L('Dropdown'))], 'header': [props(show=L(False))],
                      'items': [props(fontColor=C('#f5f7fb'), background=C('#0c1524'), textSize=D(10))]}, alt)


def two_series(m1, c1, m2, c2):
    return [{'properties': {'fill': C(c1)}, 'selector': {'metadata': m1}}, {'properties': {'fill': C(c2)}, 'selector': {'metadata': m2}}]


LIME, TEAL, AMBER, BLUE, RED = '#9cff1e', '#45e4ce', '#ffc857', '#5b9bff', '#ff5b6e'
KX, KW, KY, KH = [212, 476, 740, 1004], 252, 104, 96
IRS, PDS, CQA = 'Invoice Risk Scores', 'PO Delay Scores', 'Contract QA'
DATA_NOTE = 'Pages 09–11 use the October 2026 rebuild data.'


def header(eyebrow, title, sub, note):
    return (f'<div class="eyebrow">{eyebrow}</div><div class="title">{title}</div><div class="sub">{sub}</div>'
            f'<div class="note" style="left:{1256 - 192 - 300}px;top:20px;width:300px;font-size:9.4px;line-height:1.45;font-style:italic;color:#aab4c5;text-align:right">{note}</div>')


def kpis(specs):
    return ''.join(B.kpi(KX[i], KY, KW, KH, lab, cap, col) for i, (lab, cap, col) in enumerate(specs))


def kpi_cards(page, specs):
    return [card(page, KX[i] + 8, KY + 30, KW - 16, 42, 1000 + i, ent, m, col, alt) for i, (ent, m, col, alt) in enumerate(specs)]


PAGES = {}
# ---------------- 09 Invoice risk model ----------------
k9 = [('PR-AUC · HARD CASES', 'best rules 0.19 · guessing ≈ 0.04', LIME), ('MODEL PRECISION', 'share of 1,546 model flags that are real', TEAL),
      ('RULES PRECISION', 'share of 1,707 rule flags that are real', AMBER), ('CONDITIONS IN TEST', '14,570 invoices from Jul 2025', BLUE)]
main9 = (header('09 · MODEL RESULTS · INVOICE RISK', 'Which invoices should the model send for review?',
                'Gradient-boosted model vs hand-written audit rules, tested once on invoices from Jul 2025 onward.',
                'Hard cases were designed for this test; real scores would be lower. ' + DATA_NOTE)
         + kpis(k9)
         + B.panel(212, 212, 420, 488, 'Share of each condition caught', 'best rules vs model · same review capacity')
         + B.panel(644, 212, 612, 296, 'Review queue', 'test invoices the model sends for review, highest score first')
         + B.insight(644, 520, 612, 180, TEAL, 'INSIGHT', 'Patterns a single-invoice rule cannot see',
                     'Price creep and split bills only show across months of a supplier\'s invoices or several bills on one PO. '
                     'The model catches <b>69%</b> of price creep and <b>88%</b> of split bills; the best rules catch 30% and 46%. '
                     'Rules still edge it on near-duplicates.<br><span style="font-size:9.4px;color:#8d99ad">Built with gradient-boosted decision trees (Python, scikit-learn).</span>',
                     big='0.86', bigcap='PR-AUC · RULES 0.19'))
p9 = NEW[9][0]
PAGES[9] = (main9, kpi_cards(p9, [(IRS, 'Invoice Model PR-AUC (hard cases)', LIME, 'Invoice model PR-AUC on hard cases'),
                                  (IRS, 'Model Precision', TEAL, 'Model precision'), (IRS, 'Rules Precision', AMBER, 'Rules precision'),
                                  (IRS, 'Invoice Test Conditions', BLUE, 'Conditions in test')]) + [
    chart(p9, 220, 262, 404, 430, 2000, 'clusteredBarChart',
          {'Category': [(COL('Invoice Condition Catch', 'condition'), 'Condition')],
           'Y': [(MEAS(IRS, 'Rules Caught %'), 'Best rules'), (MEAS(IRS, 'Model Caught %'), 'Model')]},
          {'dataPoint': two_series(f'{IRS}.Rules Caught %', AMBER, f'{IRS}.Model Caught %', LIME), 'labels': LAB(), 'valueAxis': VOFF(),
           'categoryAxis': AX(), 'legend': [props(show=L(True), position=L('Top'), labelColor=C('#c6cfdb'), fontSize=D(9))]},
          'Share of each condition caught by rules and model', sort=(MEAS(IRS, 'Model Caught %'), 'Descending')),
    table(p9, 652, 262, 596, 238, 3000,
          [(COL(IRS, 'invoice_id'), 'Invoice'), (COL('Supplier', 'supplier_name'), 'Supplier'), (COL(IRS, 'invoice_date'), 'Date'),
           (COL(IRS, 'gross_amount'), 'Gross'), (COL(IRS, 'model_score'), 'Score'), (COL(IRS, 'condition'), 'Condition'),
           (COL(IRS, 'Rules Say'), 'Rules')],
          'Review queue', filters=[f_in(IRS, 'split', ['Test']), f_in(IRS, 'model_flag', [1])], sort=(COL(IRS, 'model_score'), 'Descending'))])

# ---------------- 10 Late-delivery model ----------------
k10 = [('PR-AUC · ORDER TIME', 'supplier history alone 0.56', LIME), ('PR-AUC · 3 DAYS OUT', 'adds dispatch notice and warnings', TEAL),
       ('FLAGGED POs ARRIVING LATE', 'top 25% reviewed 3 days out', AMBER), ('LATE RATE · TEST', 'what guessing would score', BLUE)]
main10 = (header('10 · MODEL RESULTS · LATE DELIVERY', 'Which purchase orders will arrive late?',
                 'Logistic regression, scored when the PO is raised and again 3 days before the promised date. Tested on Jul–Dec 2025.',
                 'Delivery outcomes were re-simulated to add the drivers, with moderate effects. ' + DATA_NOTE)
          + kpis(k10)
          + B.panel(212, 212, 420, 236, 'Late rate by supplier load', 'open orders in the last 30 days vs capacity')
          + B.panel(212, 460, 420, 240, 'What drives the model', 'validation PR-AUC lost when the driver is removed')
          + B.panel(644, 212, 612, 236, 'Actual late rate vs predicted risk', 'test POs by order month')
          + B.panel(644, 460, 612, 240, 'Watch list', 'POs flagged 3 days out, highest risk first'))
p10 = NEW[10][0]
PAGES[10] = (main10, kpi_cards(p10, [(PDS, 'Delay PR-AUC (order time)', LIME, 'Late-delivery PR-AUC at order time'),
                                     (PDS, 'Delay PR-AUC (3 days out)', TEAL, 'Late-delivery PR-AUC 3 days out'),
                                     (PDS, 'Flagged PO Late % (3 days out)', AMBER, 'Flagged POs arriving late'),
                                     (PDS, 'Test PO Late %', BLUE, 'Late rate in test window')]) + [
    chart(p10, 220, 258, 404, 184, 2000, 'clusteredColumnChart',
          {'Category': [(COL(PDS, 'Supplier Load Band'), 'Supplier load')], 'Y': [(MEAS(PDS, 'PO Late %'), 'Late rate')]},
          {'dataPoint': [props(fill=C(RED))], 'labels': LAB(), 'valueAxis': VOFF(), 'categoryAxis': AX(), 'legend': [props(show=L(False))]},
          'Late rate by supplier load', sort=(COL(PDS, 'Supplier Load Band'), 'Ascending')),
    chart(p10, 220, 506, 404, 188, 2100, 'clusteredBarChart',
          {'Category': [(COL('Delay Drivers', 'driver'), 'Driver')], 'Y': [(MEAS(PDS, 'Delay Driver Importance'), 'PR-AUC lost')]},
          {'dataPoint': [props(fill=C(LIME))], 'labels': LAB(), 'valueAxis': VOFF(), 'categoryAxis': AX(), 'legend': [props(show=L(False))]},
          'Driver importance', sort=(MEAS(PDS, 'Delay Driver Importance'), 'Descending')),
    chart(p10, 652, 258, 596, 184, 2200, 'lineChart',
          {'Category': [(COL('Date', 'month_start'), 'Month')],
           'Y': [(MEAS(PDS, 'PO Late %'), 'Actual late rate'), (MEAS(PDS, 'Avg Predicted Late Risk'), 'Predicted risk')]},
          {'dataPoint': two_series(f'{PDS}.PO Late %', RED, f'{PDS}.Avg Predicted Late Risk', TEAL),
           'lineStyles': [props(strokeWidth=D(3), showMarker=L(True))],
           'valueAxis': [props(labelColor=C('#7f8ba0'), fontSize=D(8), gridlineColor=C('#1d2940'), showAxisTitle=L(False))],
           'categoryAxis': [props(labelColor=C('#7f8ba0'), fontSize=D(8), showAxisTitle=L(False))],
           'legend': [props(show=L(True), position=L('Top'), labelColor=C('#c6cfdb'), fontSize=D(9))]},
          'Actual late rate vs predicted risk by month', filters=[f_in(PDS, 'split', ['Test'])], sort=(COL('Date', 'month_start'), 'Ascending')),
    table(p10, 652, 506, 596, 188, 3000,
          [(COL(PDS, 'po_id'), 'PO'), (COL('Supplier', 'supplier_name'), 'Supplier'), (COL('Warehouse', 'warehouse_name'), 'Warehouse'),
           (COL(PDS, 'route_type'), 'Route'), (COL(PDS, 'promised_date'), 'Promised'), (COL(PDS, 'p_pre'), 'Risk'),
           (COL(PDS, 'Delivery Outcome'), 'Outcome')],
          'Watch list', filters=[f_in(PDS, 'split', ['Test']), f_in(PDS, 'flag_pre', [1])], sort=(COL(PDS, 'p_pre'), 'Descending'))])

# ---------------- 11 Contract assistant ----------------
k11 = [('UNSEEN QUESTIONS RIGHT', '94.1% on the first and only run', LIME), ('WRONG ANSWERS GIVEN', 'answers are quoted, never generated', TEAL),
       ('UNANSWERABLE REFUSED', 'penalties, warranties, insurance', AMBER), ('QUESTIONS IN THE SET', 'everyday wording, locked before code', BLUE)]
main11 = (header('11 · MODEL RESULTS · CONTRACT ASSISTANT', 'Answers with a page citation, or no answer at all',
                 'BM25 search over 402 PDFs with a procurement thesaurus. 68 unseen questions, hash-locked before any code, run once.',
                 'The same person wrote the questions and the assistant. ' + DATA_NOTE)
          + kpis(k11)
          + B.panel(212, 212, 420, 236, 'Accuracy by question type', 'share answered or refused correctly')
          + B.insight(212, 460, 420, 240, TEAL, 'HOW IT WORKS', 'Cite the page, or say nothing',
                      '1. A document ID in the question limits the search to that PDF.<br>'
                      '2. BM25 ranks sentences; the thesaurus maps "price hike" to escalation.<br>'
                      '3. The best sentence is quoted with its [file, page] citation.<br>'
                      '4. If nothing answers, it refuses. The four misses were refusals.<br><br>'
                      '<span style="color:#8d99ad">Because answers are quoted sentences, the assistant cannot invent a clause. '
                      'Loosely worded policy questions are its weak spot (2 of 5).</span>')
          + B.panel(644, 212, 612, 488, 'Every unseen question and the answer given', 'filter by result'))
p11 = NEW[11][0]
PAGES[11] = (main11, kpi_cards(p11, [(CQA, 'Contract Score', LIME, 'Unseen questions right'), (CQA, 'Contract Wrong Answers', TEAL, 'Wrong answers'),
                                     (CQA, 'Contract Refusals Correct', AMBER, 'Unanswerable refused'), (CQA, 'Contract Questions', BLUE, 'Questions in the set')]) + [
    chart(p11, 220, 258, 404, 184, 2000, 'clusteredBarChart',
          {'Category': [(COL(CQA, 'question_type'), 'Type')], 'Y': [(MEAS(CQA, 'Contract Accuracy'), 'Accuracy')]},
          {'dataPoint': [props(fill=C(LIME))], 'labels': LAB(), 'valueAxis': VOFF(), 'categoryAxis': AX(), 'legend': [props(show=L(False))]},
          'Accuracy by question type', sort=(MEAS(CQA, 'Contract Accuracy'), 'Descending')),
    slicer(p11, 1060, 222, 188, 30, 2500, CQA, 'result', 'Filter by result'),
    table(p11, 652, 262, 596, 430, 3000,
          [(COL(CQA, 'question'), 'Question'), (COL(CQA, 'result'), 'Result'), (COL(CQA, 'answer'), 'Answer'), (COL(CQA, 'citation'), 'Citation')],
          'Every unseen question', sort=(COL(CQA, 'question_no'), 'Ascending'))])


def page_json(name, display, bg):
    img = {'image': {'name': L(bg), 'url': {'expr': {'ResourcePackageItem': {'PackageName': 'RegisteredResources', 'PackageType': 1, 'ItemName': bg}}},
                     'scaling': L('Fit')}}
    return {'$schema': SP, 'name': name, 'displayName': display, 'displayOption': 'FitToPage', 'height': 720, 'width': 1280,
            'objects': {'background': [props(image=img, transparency=D(0))], 'outspace': [props(color=C('#070b14'))]}}


def main():
    labels = [t for _, t in B.NAV]
    # 1. backgrounds
    with sync_playwright() as p:
        b = p.chromium.launch()
        for i in range(12):
            B.render(B.page_html(i, '<div class="main" style="background:transparent"></div>'), Path(f'/tmp/side_{i}.png'), b,
                     clip={'x': 0, 'y': 0, 'width': 192, 'height': 720})
        B.render(f'<!doctype html><html><head><meta charset="utf-8"><style>{B.CSS} html,body{{background:transparent}}</style></head>'
                 '<body><div class="eyebrow" style="left:0;top:0">11</div></body></html>', Path('/tmp/digits_11.png'), b,
                 clip={'x': 0, 'y': 0, 'width': 21, 'height': 15})
        for i, (main_html, _) in PAGES.items():
            B.render(B.page_html(i, f'<div class="main">{main_html}</div>'), RES / NEW[i][2], b)
        b.close()
    global DIGITS
    DIGITS = Image.open('/tmp/digits_11.png').convert('RGBA').crop((0, 0, 42, 30))
    for i, pid in enumerate(OLD):
        pj = json.loads((PAGES_DIR / pid / 'page.json').read_text(encoding='utf-8'))
        bg = pj['objects']['background'][0]['properties']['image']['image']['url']['expr']['ResourcePackageItem']['ItemName']
        im = Image.open(RES / bg).convert('RGB')
        side = Image.open(f'/tmp/side_{i}.png').convert('RGB')
        im.paste(side.crop((0, 0, 384, 1440)), (0, 0))
        # header counter "NN / 08" -> "NN / 11": cover the old digits with the rows just above, then draw new ones
        strip = im.crop((500, 30, 542, 36)).resize((42, 30))
        im.paste(strip, (500, 38))
        im.paste(DIGITS, (505, 38), DIGITS)
        im.save(RES / bg, optimize=True)
    # 2. nav buttons on existing pages
    for i, pid in enumerate(OLD):
        vdir = PAGES_DIR / pid / 'visuals'
        for vf in vdir.glob('*/visual.json'):
            v = json.loads(vf.read_text(encoding='utf-8'))
            link = v['visual'].get('visualContainerObjects', {}).get('visualLink')
            if v['visual']['visualType'] == 'actionButton' and v['position']['x'] == 12 and link:
                tgt = link[0]['properties']['navigationSection']['expr']['Literal']['Value'].strip("'")
                j = ORDER.index(tgt)
                v['position']['y'], v['position']['height'] = B.NAV_Y[j] - 16, 32
                vf.write_text(json.dumps(v, ensure_ascii=False, indent=2), encoding='utf-8')
        for j in (9, 10, 11):
            nb = nav_button(pid, j, NEW[j][0], labels[j])
            (vdir / nb['name']).mkdir(exist_ok=True)
            (vdir / nb['name'] / 'visual.json').write_text(json.dumps(nb, ensure_ascii=False, indent=2), encoding='utf-8')
    # 3. new pages
    for i in (9, 10, 11):
        name, display, bg = NEW[i]
        d = PAGES_DIR / name
        (d / 'visuals').mkdir(parents=True, exist_ok=True)
        (d / 'page.json').write_text(json.dumps(page_json(name, display, bg), ensure_ascii=False, indent=2), encoding='utf-8')
        visuals = PAGES[i][1] + [nav_button(name, j, ORDER[j], labels[j]) for j in range(12) if j != i]
        for v in visuals:
            (d / 'visuals' / v['name']).mkdir(exist_ok=True)
            (d / 'visuals' / v['name'] / 'visual.json').write_text(json.dumps(v, ensure_ascii=False, indent=2), encoding='utf-8')
    # 4. page order + registered images
    pages_meta['pageOrder'] = ORDER
    (PAGES_DIR / 'pages.json').write_text(json.dumps(pages_meta, ensure_ascii=False, indent=2), encoding='utf-8')
    rj = json.loads((REP / 'definition' / 'report.json').read_text(encoding='utf-8'))
    items = rj['resourcePackages'][0]['items']
    for i in (9, 10, 11):
        if not any(it['name'] == NEW[i][2] for it in items):
            items.insert(-1, {'name': NEW[i][2], 'path': NEW[i][2], 'type': 'Image'})
    (REP / 'definition' / 'report.json').write_text(json.dumps(rj, ensure_ascii=False, indent=2), encoding='utf-8')
    print('pages:', len(ORDER), '| new visuals:', sum(len(PAGES[i][1]) for i in PAGES))


if __name__ == '__main__':
    main()
