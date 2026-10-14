"""Report pages (PBIR) for ProcureAI Model Results: Home, Invoice risk, Late delivery,
Contract assistant, About. Canvas 1920 x 1080, dark theme matching the case-study site."""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pbi_helpers import *  # noqa: F401,F403  (visual builders and palette)

PAGES = [('home', 'Home'), ('invoice', 'Invoice risk'), ('delay', 'Late delivery'), ('contract', 'Contract assistant'), ('about', 'About')]
PID = {k: hashlib.sha1(('procureai-page-' + k).encode()).hexdigest()[:20] for k, _ in PAGES}
NAV = [('invoice', 'INVOICE RISK'), ('delay', 'LATE DELIVERY'), ('contract', 'CONTRACT ASSISTANT'), ('about', 'ABOUT')]
K1, K2, K3, K4, KW = 40, 512, 984, 1456, 424


def page_json(key, display, visuals):
    p = {'$schema': SCHEMA_P, 'name': PID[key], 'displayName': display, 'displayOption': 'FitToPage', 'height': 1080, 'width': 1920,
         'objects': {'background': [props(color=C(BG), transparency=D(0))], 'outspace': [props(color=C(BG), transparency=D(0))],
                     'displayArea': [props(verticalAlignment=L('Middle'))]}}
    return p, visuals


def top_bar(active):
    out = [nav_button(0, 0, 360, 80, '◆  PROCUREAI FMCG', PID['home'], fill=PANEL, text_color=INK, size=17, align='left', bold_font=True)]
    for i, (k, lab) in enumerate(NAV):
        out.append(nav_button(360 + i * 300, 0, 300, 80, lab, PID[k], active=(k == active)))
    out.append(textbox(1580, 22, 330, 40, [[T('Synthetic data · updated Oct 2026', 10, MUTED)]]))
    out.append(shape(0, 79, 1920, 1, LINE, z=500))
    return out


def info_box(x, y, w, h, head, lines, size=12):
    return [shape(x, y, w, h, PANEL, outline=LINE, radius=12, z=200),
            textbox(x + 22, y + 16, w - 44, h - 30, [[T(head, 15, LIME, True)]] + [[T(l, size, SOFT)] for l in lines], z=90000)]


TEST = lambda entity: f_in(entity, 'split', ['Test'])
pages = []

# ---------------- Home ----------------
v = [shape(0, 0, 1920, 1080, BG, z=10)]
v.append(textbox(120, 80, 1600, 100, [[T('PROCURE', 46, INK, True), T('AI', 46, LIME, True), T(' FMCG · model results', 30, SOFT, True)]]))
v.append(textbox(124, 180, 1600, 80, [[T('Which supplier invoices deserve a second look, which purchase orders will arrive late, and what does the contract say? '
                                          'Synthetic FMCG procurement data, Assam, 2024–2025.', 16, SOFT)]]))
v.append(kpi(120, 290, 410, 170, 'Invoice Model PR-AUC Hard', 'Invoice risk · gradient boosting', 'Invoice Model Callout'))
v.append(kpi(550, 290, 410, 170, 'Delay Order PR-AUC', 'Late delivery · logistic regression', 'Delay Order Callout'))
v.append(kpi(980, 290, 410, 170, 'Delay Pre PR-AUC', 'Late delivery · 3 days before', 'Delay Pre Callout'))
v.append(kpi(1410, 290, 390, 170, 'Contract Score', 'Contract assistant · BM25 search', 'Contract Callout'))
v.append(text_card(120, 480, 1680, 60, 'PR-AUC Explainer', size=11, color=SOFT))
tiles = [('invoice', 'Invoice risk  →', 'Model vs best hand-written rules, review queue'),
         ('delay', 'Late delivery  →', 'Order-time and pre-arrival scores, drivers, watch list'),
         ('contract', 'Contract assistant  →', '68 unseen questions, every answer with its citation'),
         ('about', 'About  →', 'How it was built, how to read it, limits')]
for i, (k, t, sub) in enumerate(tiles):
    x = 120 + i * 425
    v.append(nav_button(x, 580, 405, 220, t, PID[k], fill=PANEL, text_color=INK, size=20, align='left', bold_font=True, border=LINE, radius=16))
    v.append(textbox(x + 22, 690, 360, 90, [[T(sub, 13, SOFT)]], z=90000))
v.append(kpi(120, 840, 410, 130, 'POs', 'Purchase orders modelled', callout_text='Jan 2024 – Dec 2025', color=BLUE, fmt_size=24))
v.append(kpi(550, 840, 410, 130, 'Invoices', 'Invoices scored', callout_text='Incl. the hard test cases', color=BLUE, fmt_size=24))
v.append(kpi(980, 840, 410, 130, 'Invoice Value', 'Invoice value', callout_text='Gross, INR', color=BLUE, fmt_size=24))
v.append(kpi(1410, 840, 390, 130, 'Suppliers', 'Suppliers', callout_text='10 categories, 6 Assam warehouses', color=BLUE, fmt_size=24))
v.append(textbox(120, 1000, 1680, 50, [[T('Synthetic data · built by Bikashit Baruah · github.com/davarkk10/bikashit-portfolio', 11, MUTED)]]))
pages.append(page_json('home', 'Home', v))

# ---------------- Invoice risk ----------------
v = top_bar('invoice')
v.append(kpi(K1, 100, KW, 150, 'Invoice Model PR-AUC Hard', 'PR-AUC on hard cases', 'Invoice Model Callout'))
v.append(kpi(K2, 100, KW, 150, 'Model Precision', 'Model: flagged that are real', 'Model Precision Callout'))
v.append(kpi(K3, 100, KW, 150, 'Rules Precision', 'Best rules: flagged that are real', 'Rules Precision Callout', color=AMBER))
v.append(kpi(K4, 100, KW, 150, 'Test Conditions', 'Real conditions in the test window', callout_text='14,570 invoices from Jul 2025', color=BLUE))
v.append(chart(40, 270, 1000, 400, 'clusteredBarChart',
               {'Category': [COLM('invoice_catch', 'condition')], 'Y': [MEAS('Rules Caught %'), MEAS('Model Caught %')]},
               title='Share of each condition caught: best rules vs model',
               subtitle='Rules: everything they flag · Model: its top 1,546 invoices (the review capacity)',
               objects={'categoryAxis': AXIS(), 'valueAxis': VAXIS(False), 'legend': LEGEND(), 'labels': LABELS(True, INK),
                        'dataPoint': [{'properties': {'fill': C(AMBER)}, 'selector': sel_meta(MEAS('Rules Caught %'))},
                                      {'properties': {'fill': C(GOOD)}, 'selector': sel_meta(MEAS('Model Caught %'))}]},
               sort=(MEAS('Model Caught %'), 'Descending')))
v += info_box(1060, 270, 820, 400, 'Built with', [
    'Gradient-boosted decision trees in Python (scikit-learn), trained on invoices to Mar 2025, chosen on Apr–Jun 2025, tested once on Jul 2025 onward.',
    "Signals: price over PO, quantity over order, a supplier's price drift over 120 days, several invoices on one PO near the ₹10 lakh approval limit, near-matching invoice numbers.",
    'Hard cases: bills split under the approval limit, months of price creep inside the 2% tolerance, resubmitted invoices with altered numbers. Each has a legitimate look-alike.',
    'Disclosure: the hard cases and look-alikes were designed for this test, so real scores would be lower.'], size=11)
v.append(textbox(40, 688, 260, 40, [[T('SHOW', 9, MUTED, True)]]))
v.append(slicer(110, 684, 700, 46, 'fact_invoice', 'condition_group', None))
v.append(chart(40, 740, 1840, 310, 'tableEx',
               {'Values': [COLM('fact_invoice', 'invoice_id'), COLM('dim_supplier', 'supplier_name'), COLM('fact_invoice', 'invoice_date'),
                           COLM('fact_invoice', 'gross_amount'), COLM('fact_invoice', 'model_score'), COLM('fact_invoice', 'condition'),
                           COLM('fact_invoice', 'Rules Say')]},
               title='Review queue: test invoices the model sends for review, highest score first',
               objects=matrix_objects(), filters=[TEST('fact_invoice'), f_in('fact_invoice', 'model_flag', [1])],
               sort=(COLM('fact_invoice', 'model_score'), 'Descending')))
pages.append(page_json('invoice', 'Invoice risk', v))

# ---------------- Late delivery ----------------
v = top_bar('delay')
v.append(kpi(K1, 100, KW, 150, 'Delay Order PR-AUC', 'PR-AUC when the PO is raised', 'Delay Order Callout'))
v.append(kpi(K2, 100, KW, 150, 'Delay Pre PR-AUC', 'PR-AUC 3 days before delivery', 'Delay Pre Callout'))
v.append(kpi(K3, 100, KW, 150, 'Flagged Late % (Pre)', 'Flagged POs that arrive late', 'Flagged Callout'))
v.append(kpi(K4, 100, KW, 150, 'Test Late %', 'Late rate, test window', 'Test Late Callout', color=BLUE))
v.append(chart(40, 270, 880, 380, 'lineChart',
               {'Category': [COLM('dim_date', 'Month Start')], 'Y': [MEAS('Late %'), MEAS('Avg Predicted Risk')]},
               title='Test window: actual late rate vs average predicted risk, by order month',
               objects={'categoryAxis': AXIS(), 'valueAxis': VAXIS(), 'legend': LEGEND(), 'labels': LABELS(False),
                        'dataPoint': [{'properties': {'fill': C(BAD)}, 'selector': sel_meta(MEAS('Late %'))},
                                      {'properties': {'fill': C(GOOD)}, 'selector': sel_meta(MEAS('Avg Predicted Risk'))}],
                        'lineStyles': [props(strokeWidth=D(2), showMarker=L(True), markerSize=D(4))]},
               filters=[TEST('fact_po')], sort=(COLM('dim_date', 'Month Start'), 'Ascending')))
v.append(chart(940, 270, 460, 380, 'clusteredColumnChart',
               {'Category': [COLM('fact_po', 'Load Band')], 'Y': [MEAS('Late %')], 'Tooltips': [MEAS('POs')]},
               title='Late rate by supplier load', subtitle='Open orders in the last 30 days vs supplier capacity',
               objects={'categoryAxis': AXIS(), 'valueAxis': VAXIS(False), 'labels': LABELS(True, INK), 'dataPoint': [props(fill=C(BAD))]},
               sort=(COLM('fact_po', 'Load Band'), 'Ascending')))
v.append(chart(1420, 270, 460, 380, 'clusteredBarChart',
               {'Category': [COLM('driver_importance', 'driver')], 'Y': [MEAS('Driver Importance')]},
               title='What drives the model', subtitle='Validation PR-AUC lost when each driver is removed',
               objects={'categoryAxis': AXIS(), 'valueAxis': VAXIS(False), 'labels': LABELS(True, INK), 'dataPoint': [props(fill=C(GOOD))]},
               sort=(MEAS('Driver Importance'), 'Descending')))
v.append(textbox(40, 668, 200, 40, [[T('ROUTE', 9, MUTED, True)]]))
v.append(slicer(110, 664, 620, 46, 'fact_po', 'route_type', None))
v.append(textbox(760, 668, 200, 40, [[T('WAREHOUSE', 9, MUTED, True)]]))
v.append(slicer(870, 664, 360, 46, 'dim_warehouse', 'warehouse_name', None, mode='dropdown'))
v.append(textbox(1250, 660, 630, 60, [[T('Built with logistic regression (scikit-learn). Gradient boosting tied on test and lost on validation, '
                                          'so the simpler model was kept. Delivery outcomes were re-simulated to add the drivers.', 10, MUTED)]]))
v.append(chart(40, 730, 1840, 320, 'tableEx',
               {'Values': [COLM('fact_po', 'po_id'), COLM('dim_supplier', 'supplier_name'), COLM('dim_warehouse', 'warehouse_name'),
                           COLM('fact_po', 'route_type'), COLM('fact_po', 'promised_date'), COLM('fact_po', 'utilisation'),
                           COLM('fact_po', 'p_pre'), COLM('fact_po', 'Delivery')]},
               title='Watch list: test POs flagged 3 days before delivery (top 25%), highest risk first',
               objects=matrix_objects(), filters=[TEST('fact_po'), f_in('fact_po', 'flag_pre', [1])],
               sort=(COLM('fact_po', 'p_pre'), 'Descending')))
pages.append(page_json('delay', 'Late delivery', v))

# ---------------- Contract assistant ----------------
v = top_bar('contract')
v.append(kpi(K1, 100, KW, 150, 'Contract Score', 'Unseen questions answered correctly', 'Contract Callout'))
v.append(kpi(K2, 100, KW, 150, 'Wrong Answers', 'Wrong answers given', callout_text='Answers are quoted, never generated'))
v.append(kpi(K3, 100, KW, 150, 'Refusals Correct', 'Unanswerable questions refused', callout_text='Penalties, warranties, insurance…'))
v.append(kpi(K4, 100, KW, 150, 'Questions', 'Questions in the locked set', callout_text='Written before any code, run once', color=BLUE))
v.append(chart(40, 270, 600, 380, 'clusteredBarChart',
               {'Category': [COLM('contract_qa', 'question_type')], 'Y': [MEAS('Accuracy')], 'Tooltips': [MEAS('Questions')]},
               title='Accuracy by question type',
               objects={'categoryAxis': AXIS(), 'valueAxis': VAXIS(False), 'labels': LABELS(True, INK), 'dataPoint': [props(fill=C(GOOD))]},
               sort=(MEAS('Accuracy'), 'Descending')))
v += info_box(40, 670, 600, 380, 'Built with', [
    'BM25 search ranking in Python over 402 PDFs, split into sentences tagged with file and page.',
    'A procurement thesaurus maps everyday words ("price hike", "get out of") to contract terms.',
    'The best sentence is quoted with its [file, page] citation; if nothing answers, it refuses.',
    'Limit: the same person wrote the questions and the assistant.'], size=11)
v.append(textbox(660, 274, 120, 40, [[T('RESULT', 9, MUTED, True)]]))
v.append(slicer(740, 270, 1140, 46, 'contract_qa', 'result', None))
v.append(chart(660, 330, 1220, 720, 'tableEx',
               {'Values': [COLM('contract_qa', 'question'), COLM('contract_qa', 'result'), COLM('contract_qa', 'answer'), COLM('contract_qa', 'citation')]},
               title='Every unseen question and the answer given',
               objects=matrix_objects(), sort=(COLM('contract_qa', 'question_no'), 'Ascending')))
pages.append(page_json('contract', 'Contract assistant', v))

# ---------------- About ----------------
v = top_bar('about')
boxes = [
    (40, 100, 'What this is', ['Model results for ProcureAI FMCG, a procurement analytics case study on synthetic data for a fictional Assam FMCG company (2024–2025).',
                               'Three questions: which invoices deserve review, which POs will arrive late, and what the contract says.',
                               'A separate 9-page Power BI report covers spend and the three-way match.']),
    (980, 100, 'How it was built', ['Invoice risk: gradient-boosted decision trees vs hand-written audit rules.',
                                    'Late delivery: logistic regression vs each supplier\'s past late rate, scored at order time and 3 days before delivery.',
                                    'Contract assistant: BM25 search with a procurement thesaurus; answers quoted with citations.',
                                    'Train to Mar 2025, choose on Apr–Jun 2025, test once on Jul 2025 onward. Python, scikit-learn, Power BI.']),
    (40, 580, 'Reading the numbers', ['PR-AUC: 0-to-1 score for how well a model puts real problems at the top of the review list. Guessing scores the problem rate; 1.0 is perfect.',
                                      'Precision: of the items flagged, the share that are real. Recall: of the real items, the share flagged.',
                                      'Capacity: how many items a team can review (invoices: 1,546 in the test window; POs: the top 25%).']),
    (980, 580, 'Limits', ['All data is synthetic. Invoice hard cases and delivery drivers were designed for the test and are disclosed.',
                          'PR-AUC values come from the Python evaluation (model_results.csv); precision and recall are recomputed live from the scored rows.',
                          'Expected values after refresh are listed in data/expected_values.json.'])]
for x, y, head, lines in boxes:
    v += info_box(x, y, 900, 460, head, lines, size=13)
pages.append(page_json('about', 'About', v))

THEME_NAME = 'ProcureAI_dark.json'
theme = {
    'name': 'ProcureAI dark',
    'dataColors': [GOOD, BAD, AMBER, BLUE, MINT, '#B4A9FF', '#9BD16A', '#E58BC5'],
    'good': GOOD, 'neutral': AMBER, 'bad': BAD, 'maximum': BAD, 'center': '#2C5A4F', 'minimum': PANEL,
    'foreground': INK, 'foregroundNeutralSecondary': SOFT, 'foregroundNeutralTertiary': MUTED,
    'background': PANEL, 'backgroundLight': '#163029', 'backgroundNeutral': LINE,
    'tableAccent': LIME, 'hyperlink': LIME, 'visitedHyperlink': MINT,
    'textClasses': {'callout': {'fontSize': 28, 'fontFace': 'Segoe UI Bold', 'color': INK},
                    'title': {'fontSize': 12, 'fontFace': 'Segoe UI Semibold', 'color': INK},
                    'header': {'fontSize': 12, 'fontFace': 'Segoe UI Semibold', 'color': INK},
                    'label': {'fontSize': 10, 'fontFace': 'Segoe UI', 'color': SOFT}},
    'visualStyles': {
        '*': {'*': {
            'background': [{'show': True, 'color': {'solid': {'color': PANEL}}, 'transparency': 0}],
            'border': [{'show': True, 'color': {'solid': {'color': LINE}}, 'radius': 12}],
            'dropShadow': [{'show': False}],
            'title': [{'show': True, 'fontColor': {'solid': {'color': INK}}, 'fontSize': 12, 'fontFamily': 'Segoe UI Semibold'}],
            'subTitle': [{'fontColor': {'solid': {'color': MUTED}}}],
            'categoryAxis': [{'labelColor': {'solid': {'color': SOFT}}, 'titleColor': {'solid': {'color': MUTED}}}],
            'valueAxis': [{'labelColor': {'solid': {'color': MUTED}}, 'titleColor': {'solid': {'color': MUTED}}, 'gridlineColor': {'solid': {'color': LINE}}}],
            'legend': [{'labelColor': {'solid': {'color': SOFT}}}],
            'labels': [{'color': {'solid': {'color': INK}}}],
            'visualHeader': [{'foreground': {'solid': {'color': SOFT}}, 'background': {'solid': {'color': PANEL}}}]}},
        'page': {'*': {'background': [{'color': {'solid': {'color': BG}}, 'transparency': 0}], 'outspace': [{'color': {'solid': {'color': BG}}}]}},
        'filterCard': {'*': {'backgroundColor': [{'solid': {'color': PANEL}}], 'foregroundColor': [{'solid': {'color': INK}}]}},
    },
}

if __name__ == '__main__':
    print(len(pages), 'pages,', sum(len(v) for _, v in pages), 'visuals')
