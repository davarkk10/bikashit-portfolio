# Builds the PBIR report definition for Olist Delivery 360 (dark Case 4 theme)
import json, hashlib, itertools

SCHEMA_V = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.12.0/schema.json'
SCHEMA_P = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json'

# Case 4 site palette
BG, PANEL, PANEL2, LINE = '#070B14', '#101A2B', '#0C1524', '#263249'
INK, SOFT, MUTED = '#F5F7FB', '#C6CFDB', '#7F8BA0'
LIME, MINT = '#9CFF1E', '#45E4CE'
GOOD, BAD, AMBER, BLUE = '#5EAA12', '#8B7BFF', '#C9821F', '#2B9FC2'
M = '_Measures'
SEMI = "'''Segoe UI Semibold'', wf_segoe-ui_semibold, helvetica, arial, sans-serif'"
BOLD = "'''Segoe UI Bold'', wf_segoe-ui_bold, helvetica, arial, sans-serif'"

_counter = itertools.count()
def nid(seed=''):
    return hashlib.sha1(f'{seed}{next(_counter)}'.encode()).hexdigest()[:20]

def L(v):  # literal expression
    if isinstance(v, bool): s = 'true' if v else 'false'
    elif isinstance(v, int): s = f'{v}L'
    elif isinstance(v, float): s = f'{v}D'
    else: s = "'" + v.replace("'", "''") + "'"
    return {'expr': {'Literal': {'Value': s}}}
def D(v): return {'expr': {'Literal': {'Value': f'{v}D'}}}
def C(hexv): return {'solid': {'color': L(hexv)}}
def MEAS(name, entity=M): return {'Measure': {'Expression': {'SourceRef': {'Entity': entity}}, 'Property': name}}
def COLM(entity, prop): return {'Column': {'Expression': {'SourceRef': {'Entity': entity}}, 'Property': prop}}
def CM(name): return {'solid': {'color': {'expr': MEAS(name)}}}  # colour from measure
def qref(f):
    if 'Measure' in f: return f"{f['Measure']['Expression']['SourceRef']['Entity']}.{f['Measure']['Property']}"
    if 'Column' in f: return f"{f['Column']['Expression']['SourceRef']['Entity']}.{f['Column']['Property']}"
    a = f['Aggregation']['Expression']['Column']; return f"Min({a['Expression']['SourceRef']['Entity']}.{a['Property']})"
def proj(f, display=None, active=None):
    p = {'field': f, 'queryRef': qref(f), 'nativeQueryRef': (f.get('Measure') or f.get('Column') or {'Property': 'v'})['Property'] if 'Aggregation' not in f else f['Aggregation']['Expression']['Column']['Property']}
    if display: p['displayName'] = display
    if active: p['active'] = True
    return p
def props(**kw): return {'properties': kw}
def sel_meta(f): return {'metadata': qref(f)}
def sel_wild(f=None, opt=1):
    s = {'data': [{'dataViewWildcard': {'matchingOption': opt}}]}
    if f: s['metadata'] = qref(f)
    return s

def container(title=None, bg=True, border=True, shadow=False, pad=None, header=False, tooltip_page=None, title_measure=None, subtitle=None):
    o = {}
    if title or title_measure:
        tp = {'show': L(True), 'fontColor': C(INK), 'fontSize': D(12), 'fontFamily': L("'Segoe UI Semibold', wf_segoe-ui_semibold, helvetica, arial, sans-serif")}
        tp['text'] = {'expr': MEAS(title_measure)} if title_measure else L(title)
        o['title'] = [props(**tp)]
    else:
        o['title'] = [props(show=L(False))]
    if subtitle:
        o['subTitle'] = [props(show=L(True), text=L(subtitle), fontColor=C(MUTED), fontSize=D(9))]
    o['background'] = [props(show=L(bg), color=C(PANEL), transparency=D(0))]
    o['border'] = [props(show=L(border), color=C(LINE), radius=D(12))]
    o['dropShadow'] = [props(show=L(shadow))]
    o['visualHeader'] = [props(show=L(header))]
    if pad is not None: o['padding'] = [props(top=D(pad), bottom=D(pad), left=D(pad), right=D(pad))]
    if tooltip_page: o['visualTooltip'] = [props(show=L(True), type=L('Canvas'), section=L(tooltip_page))]
    return o

def visual(x, y, w, h, vtype, query=None, objects=None, vco=None, filters=None, z=None, sync=None, alt=None):
    v = {'visualType': vtype}
    if query: v['query'] = query
    if objects: v['objects'] = objects
    v['visualContainerObjects'] = vco or {}
    if alt: v['visualContainerObjects'].setdefault('general', [props(altText=L(alt))])
    if sync: v['syncGroup'] = {'groupName': sync, 'fieldChanges': True, 'filterChanges': True}
    v['drillFilterOtherVisuals'] = True
    name = nid(vtype)
    out = {'$schema': SCHEMA_V, 'name': name,
           'position': {'x': x, 'y': y, 'z': z if z is not None else 1000 + next(_counter), 'height': h, 'width': w, 'tabOrder': next(_counter)},
           'visual': v}
    if filters: out['filterConfig'] = {'filters': filters}
    return out

# ---------- filters ----------
def f_measure(mname, kind, value):
    # kind: 0 Equal, 1 GreaterThan, 2 GreaterThanOrEqual
    return {'name': nid('f'), 'field': MEAS(mname), 'type': 'Advanced',
            'filter': {'Version': 2, 'From': [{'Name': 'm', 'Entity': M, 'Type': 0}],
                       'Where': [{'Condition': {'Comparison': {'ComparisonKind': kind,
                                 'Left': {'Measure': {'Expression': {'SourceRef': {'Source': 'm'}}, 'Property': mname}},
                                 'Right': {'Literal': {'Value': f'{value}L'}}}}}]},
            'howCreated': 'User'}
def lit(v): return {'Literal': {'Value': f'{v}L' if isinstance(v, int) else "'" + v + "'"}}
def f_in(entity, prop, values, negate=False):
    cond = {'In': {'Expressions': [{'Column': {'Expression': {'SourceRef': {'Source': 'd'}}, 'Property': prop}}],
                   'Values': [[lit(v)] for v in values]}}
    if negate: cond = {'Not': {'Expression': cond}}
    return {'name': nid('f'), 'field': COLM(entity, prop), 'type': 'Categorical',
            'filter': {'Version': 2, 'From': [{'Name': 'd', 'Entity': entity, 'Type': 0}], 'Where': [{'Condition': cond}]},
            'howCreated': 'User'}

# ---------- building blocks ----------
def textbox(x, y, w, h, runs_list, z=None, align=None):
    paras = []
    for runs in runs_list:
        p = {'textRuns': [{'value': t, 'textStyle': st} for t, st in runs]}
        if align: p['horizontalTextAlignment'] = align
        paras.append(p)
    return visual(x, y, w, h, 'textbox', objects={'general': [props(paragraphs=paras)]},
                  vco={'title': [props(show=L(False))], 'background': [props(show=L(False))], 'border': [props(show=L(False))],
                       'dropShadow': [props(show=L(False))], 'visualHeader': [props(show=L(False))]}, z=z)
def T(text, size=12, color=INK, bold=False):
    st = {'fontSize': f'{size}pt', 'color': color, 'fontFamily': 'Segoe UI'}
    if bold: st['fontWeight'] = 'bold'
    return (text, st)

def shape(x, y, w, h, fill, outline=None, radius=None, z=None, text=None, tsize=14, tcolor=INK):
    sh = props(tileShape=L('rectangleRounded' if radius else 'rectangle'))
    if radius: sh['properties']['rectangleRoundedCurve'] = {'expr': {'Literal': {'Value': f'{radius}L'}}}
    objs = {'shape': [sh], 'fill': [props(show=L(True)), {'properties': {'fillColor': C(fill), 'transparency': D(0)}, 'selector': {'id': 'default'}}],
            'outline': [props(show=L(bool(outline)), lineColor=C(outline or fill), weight=D(1))]}
    if text:
        objs['text'] = [props(show=L(True)), {'properties': {'text': L(text), 'fontColor': C(tcolor), 'fontSize': D(tsize),
                        'horizontalAlignment': L('left'), 'fontFamily': L(BOLD.strip("'").replace("''", "'")) if False else {'expr': {'Literal': {'Value': BOLD}}}},
                        'selector': {'id': 'default'}}]
    return visual(x, y, w, h, 'shape', objects=objs,
                  vco={'background': [props(show=L(False))], 'title': [props(show=L(False))], 'border': [props(show=L(False))],
                       'dropShadow': [props(show=L(False))], 'visualHeader': [props(show=L(False))]}, z=z)

def nav_button(x, y, w, h, label, page_name, active=False, fill=PANEL2, text_color=SOFT, size=12, align='center', bold_font=False, border=None, radius=0):
    tcol = LIME if active else text_color
    fcol = '#1B2A42' if active else fill
    objs = {
        'icon': [props(show=L(False))],
        'text': [props(show=L(True)), {'properties': {'text': L(label), 'fontColor': C(tcol), 'fontSize': D(size),
                 'horizontalAlignment': L(align), 'fontFamily': {'expr': {'Literal': {'Value': BOLD if bold_font else SEMI}}}},
                 'selector': {'id': 'default'}},
                 {'properties': {'fontColor': C(LIME)}, 'selector': {'id': 'hover'}}],
        'fill': [props(show=L(True)), {'properties': {'fillColor': C(fcol), 'transparency': D(0)}, 'selector': {'id': 'default'}},
                 {'properties': {'fillColor': C('#1B2A42'), 'transparency': D(0)}, 'selector': {'id': 'hover'}}],
        'outline': [props(show=L(bool(border))), {'properties': {'lineColor': C(border or fcol), 'weight': D(1)}, 'selector': {'id': 'default'}}],
        'shape': [{'properties': {'tileShape': L('rectangleRounded' if radius else 'rectangle'),
                                  **({'rectangleRoundedCurve': {'expr': {'Literal': {'Value': f'{radius}L'}}}} if radius else {})},
                   'selector': {'id': 'default'}}],
        'shadow': [props(show=L(False))],
    }
    vco = {'title': [props(show=L(False))], 'background': [props(show=L(False))], 'visualHeader': [props(show=L(False))],
           'dropShadow': [props(show=L(False))]}
    if page_name:
        vco['visualLink'] = [props(show=L(True), type=L('PageNavigation'), navigationSection=L(page_name), tooltip=L(label.strip()))]
    return visual(x, y, w, h, 'actionButton', objects=objs, vco=vco)

def slicer(x, y, w, h, entity, prop, sync, mode='tiles', default=None, single=False, filters=None, cols=None):
    objs = {'header': [props(show=L(False))],
            'items': [props(background=C('#1B2A42'), fontColor=C(INK), textSize=D(10.5), padding=D(3), outlineStyle=D(0),
                            fontFamily={'expr': {'Literal': {'Value': SEMI}}})]}
    if mode == 'dropdown':
        objs['data'] = [props(mode=L('Dropdown'))]
        objs['items'] = [props(background=C(PANEL2), fontColor=C(INK), textSize=D(10.5))]
    else:
        objs['data'] = [props(mode=L('Basic'))]
        objs['general'] = [props(orientation=D(1))]
    if single:
        objs['selection'] = [props(singleSelect=L(True), strictSingleSelect=L(True))]
    if default is not None:
        g = objs.setdefault('general', [props()])
        g[0]['properties']['filter'] = {'filter': {'Version': 2, 'From': [{'Name': 'd', 'Entity': entity, 'Type': 0}],
            'Where': [{'Condition': {'In': {'Expressions': [{'Column': {'Expression': {'SourceRef': {'Source': 'd'}}, 'Property': prop}}],
                                            'Values': [[lit(default)]]}}}]}}
    q = {'queryState': {'Values': {'projections': [proj(COLM(entity, prop), active=True)]}}}
    return visual(x, y, w, h, 'slicer', query=q, objects=objs,
                  vco={'title': [props(show=L(False))], 'background': [props(show=L(False))], 'border': [props(show=L(False))],
                       'dropShadow': [props(show=L(False))], 'visualHeader': [props(show=L(False))]},
                  filters=filters, sync=sync)

def kpi(x, y, w, h, measure, title, callout_measure=None, callout_text=None, color_measure=None, color=None, fmt_size=30):
    f = MEAS(measure)
    objs = {
        'value': [props(fontSize=D(fmt_size), fontColor=C(INK), fontFamily={'expr': {'Literal': {'Value': BOLD}}}), ],
        'label': [{'properties': {'show': L(True)}, 'selector': {'id': 'default'}}],
        'accentBar': [{'properties': {'show': L(True), 'width': D(6), 'color': C(color or GOOD)}, 'selector': {'id': 'default'}},
                      {'properties': {'position': L('Left')}, 'selector': sel_meta(f)}],
        'fillCustom': [props(show=L(False))],
        'outline': [props(show=L(False))],
    }
    if color_measure:
        objs['accentBar'].append({'properties': {'color': CM(color_measure)}, 'selector': sel_wild(f, 0)})
    if callout_measure:
        objs['label'].append({'properties': {'text': {'expr': MEAS(callout_measure)}}, 'selector': sel_wild(f, 0)})
    elif callout_text:
        objs['label'].append({'properties': {'text': L(callout_text)}, 'selector': sel_wild(f, 0)})
    objs['label'].append({'properties': {'position': L('belowValue'), 'color': C(SOFT), 'fontSize': D(11)}, 'selector': sel_meta(f)})
    q = {'queryState': {'Data': {'projections': [proj(f)]}}}
    vco = container(title=title, pad=6)
    vco['title'][0]['properties']['fontColor'] = C(MINT)
    vco['title'][0]['properties']['fontSize'] = D(13)
    return visual(x, y, w, h, 'cardVisual', query=q, objects=objs, vco=vco)

def text_card(x, y, w, h, measure, size=13, color=INK, bg=True):
    f = MEAS(measure)
    objs = {'value': [props(fontSize=D(size), fontColor=C(color), fontFamily={'expr': {'Literal': {'Value': SEMI}}})],
            'label': [props(show=L(False))], 'fillCustom': [props(show=L(False))], 'outline': [props(show=L(False))],
            'accentBar': [{'properties': {'show': L(bg), 'width': D(6), 'color': C(LIME), 'position': L('Left')}, 'selector': {'id': 'default'}}]}
    vco = container(bg=bg, border=bg, pad=4)
    return visual(x, y, w, h, 'cardVisual', query={'queryState': {'Data': {'projections': [proj(f)]}}}, objects=objs, vco=vco)

AXIS = lambda: [props(labelColor=C(SOFT), fontSize=D(9), showAxisTitle=L(False))]
VAXIS = lambda show=True: [props(show=L(show), labelColor=C(MUTED), fontSize=D(9), showAxisTitle=L(False), gridlineShow=L(True), gridlineColor=C(LINE), gridlineStyle=L('dotted'))]
LEGEND = lambda show=True: [props(show=L(show), labelColor=C(SOFT), fontSize=D(9), position=L('TopLeft'))]
LABELS = lambda show=True, color=SOFT: [props(show=L(show), color=C(color), fontSize=D(9))]

def chart(x, y, w, h, vtype, roles, title=None, objects=None, filters=None, sort=None, title_measure=None, subtitle=None, tooltip_page=None, alt=None):
    qs = {}
    for role, fields in roles.items():
        qs[role] = {'projections': [proj(f, active=(i == 0 and role in ('Category', 'Rows'))) for i, f in enumerate(fields)]}
    q = {'queryState': qs}
    if sort:
        q['sortDefinition'] = {'sort': [{'field': sort[0], 'direction': sort[1]}]}
    return visual(x, y, w, h, vtype, query=q, objects=objects or {}, filters=filters,
                  vco=container(title=title, title_measure=title_measure, subtitle=subtitle, tooltip_page=tooltip_page, pad=8), alt=alt)

def table_values(fields, sorts=None):
    return {'Values': fields}

def matrix_objects(bar_measures=(), gradient_measure=None, font_color=None):
    o = {
        'columnHeaders': [props(fontColor=C(MUTED), backColor=C(PANEL), fontSize=D(9.5), fontFamily={'expr': {'Literal': {'Value': SEMI}}}, wordWrap=L(True))],
        'rowHeaders': [props(fontColor=C(INK), backColor=C(PANEL), fontSize=D(10))],
        'values': [props(fontColorPrimary=C(INK), backColorPrimary=C(PANEL), fontColorSecondary=C(INK), backColorSecondary=C(PANEL2), fontSize=D(10))],
        'grid': [props(gridHorizontal=L(True), gridHorizontalColor=C(LINE), gridVertical=L(False), rowPadding=D(5), outlineColor=C(LINE))],
        'total': [props(fontColor=C(INK), backColor=C(PANEL2))],
        'subTotals': [props(fontColor=C(INK), backColor=C(PANEL2))],
    }
    for bm in bar_measures:
        o['values'].append({'properties': {'dataBars': {'positiveColor': C(GOOD), 'negativeColor': C(BAD), 'axisColor': C(LINE),
                            'reverseDirection': L(False), 'hideText': L(False)}}, 'selector': sel_meta(MEAS(bm))})
    if gradient_measure:
        fm = MEAS(gradient_measure)
        o['values'].append({'properties': {'backColor': {'solid': {'color': {'expr': {'FillRule': {'Input': fm, 'FillRule': {'linearGradient2': {
            'min': {'color': {'Literal': {'Value': f"'{PANEL}'"}}}, 'max': {'color': {'Literal': {'Value': f"'{BAD}'"}}},
            'nullColoringStrategy': {'strategy': {'Literal': {'Value': "'asZero'"}}}}}}}}}}}, 'selector': sel_wild(fm, 1)})
    if font_color:
        fm, cm = font_color
        o['values'].append({'properties': {'fontColorPrimary': CM(cm), 'fontColorSecondary': CM(cm)}, 'selector': sel_wild(MEAS(fm), 1)})
    return o

# ---------- page assembly ----------
PAGES = [('home', 'Home'), ('exec', 'Executive'), ('delivery', 'Delivery'), ('customer', 'Customer'),
         ('seller', 'Seller'), ('checks', 'Data Checks'), ('about', 'About'), ('tt', 'TT State')]
PID = {k: hashlib.sha1(('page' + k).encode()).hexdigest()[:20] for k, _ in PAGES}
NAV = [('exec', 'EXECUTIVE'), ('delivery', 'DELIVERY'), ('customer', 'CUSTOMER'), ('seller', 'SELLER'), ('checks', 'DATA CHECKS'), ('about', 'ABOUT')]

def top_bar(active):
    out = [nav_button(0, 0, 360, 80, '◆  OLIST DELIVERY 360', PID['home'], fill=PANEL, text_color=INK, size=17, align='left', bold_font=True)]
    for i, (k, lab) in enumerate(NAV):
        out.append(nav_button(360 + i * 260, 0, 260, 80, lab, PID[k], active=(k == active)))
    out.append(shape(0, 79, 1920, 1, LINE, z=500))
    return out

SLICER_NAMES = {}
def filter_panel(page):
    out = [shape(40, 100, 330, 950, PANEL, outline=LINE, radius=14, z=100)]
    out.append(textbox(60, 112, 290, 36, [[T('⛉  FILTERS', 14, LIME, True)]]))
    out.append(textbox(60, 156, 290, 26, [[T('SELECT BENCHMARK (BM)', 9, MUTED, True)]]))
    s_bm = slicer(64, 182, 282, 46, 'dim_bm', 'Benchmark', 'bm', default='vs LY', single=True)
    out.append(textbox(60, 240, 290, 26, [[T('YEAR', 9, MUTED, True)]]))
    s_year = slicer(64, 266, 282, 50, 'dim_date', 'Year', 'year', default=2018, single=True, filters=[f_in('dim_date', 'Year', [2017, 2018])])
    out.append(textbox(60, 328, 290, 26, [[T('QUARTER', 9, MUTED, True)]]))
    s_q = slicer(64, 354, 282, 46, 'dim_date', 'Quarter', 'quarter')
    out.append(textbox(60, 414, 290, 26, [[T('MONTH', 9, MUTED, True)]]))
    s_m = slicer(64, 440, 282, 40, 'dim_date', 'Month', 'month', mode='dropdown')
    out.append(textbox(60, 494, 290, 26, [[T('CUSTOMER REGION', 9, MUTED, True)]]))
    s_r = slicer(64, 520, 282, 40, 'dim_state', 'Region', 'region', mode='dropdown')
    out.append(textbox(60, 574, 290, 26, [[T('CUSTOMER STATE', 9, MUTED, True)]]))
    s_s = slicer(64, 600, 282, 40, 'dim_state', 'State', 'state', mode='dropdown')
    out += [s_bm, s_year, s_q, s_m, s_r, s_s]
    SLICER_NAMES[page] = {'year': s_year['name'], 'quarter': s_q['name'], 'month': s_m['name']}
    out.append(textbox(60, 668, 290, 190, [
        [T('Abbreviations', 10, INK, True)],
        [T('BM = Benchmark · LY = same dates last year', 9, SOFT)],
        [T('pp = percentage points', 9, SOFT)],
        [T('Late = delivered after the promised date', 9, SOFT)],
        [T('Targets are illustrative goals; BM shows n/a when last year has under 300 orders', 9, SOFT)]]))
    out.append(text_card(64, 880, 282, 44, 'Last Data Date', size=10, color=SOFT, bg=False))
    out.append(textbox(60, 930, 290, 100, [
        [T('Olist public data (CC BY-NC-SA 4.0)', 9, MUTED)],
        [T('Built by Bikashit Baruah', 10, LIME, True)]]))
    return out

def page_json(key, display, visuals, width=1920, height=1080, ptype=None, interactions=None, hidden=False):
    p = {'$schema': SCHEMA_P, 'name': PID[key], 'displayName': display, 'displayOption': 'FitToPage' if not ptype else 'ActualSize',
         'height': height, 'width': width,
         'objects': {'background': [props(color=C(BG), transparency=D(0))],
                     'outspace': [props(color=C(BG), transparency=D(0))],
                     'displayArea': [props(verticalAlignment=L('Middle'))]}}
    if ptype: p['type'] = ptype
    if hidden: p['visibility'] = 'HiddenInViewMode'
    if interactions: p['visualInteractions'] = interactions
    return p, visuals

def no_time_filter(page, targets):
    s = SLICER_NAMES[page]
    return [{'source': s[k], 'target': t, 'type': 'NoFilter'} for t in targets for k in ('year', 'quarter', 'month')]

X1, X2, X3, X4, KW = 400, 777, 1154, 1531, 357
pages = []

# ---- Home ----
v = [shape(0, 0, 1920, 1080, BG, z=10)]
v.append(textbox(130, 110, 1500, 110, [[T('OLIST DELIVERY ', 48, INK, True), T('360', 48, LIME, True)]]))
v.append(textbox(134, 222, 1400, 90, [[T('Late deliveries, customer reviews and seller performance across 96,470 real Brazilian e-commerce orders (2016–2018)', 18, SOFT)]]))
tiles = [('exec', 'Executive  →', 'Headline KPIs vs last year or target'), ('delivery', 'Delivery  →', 'States, lanes, promise vs reality'),
         ('customer', 'Customer  →', 'Reviews and repeat buying'), ('seller', 'Seller  →', 'Who to coach first'),
         ('checks', 'Data Checks  →', '12 numbers checked against SQL'), ('about', 'About  →', 'Data, definitions, limits')]
for i, (k, t, sub) in enumerate(tiles):
    x = 140 + (i % 3) * 560; y = 380 + (i // 3) * 250
    v.append(nav_button(x, y, 520, 210, t, PID[k], fill=PANEL, text_color=INK, size=24, align='left', bold_font=True, border=LINE, radius=16))
    v.append(textbox(x + 26, y + 120, 470, 60, [[T(sub, 14, SOFT)]], z=90000))
v.append(textbox(140, 920, 1640, 50, [[T('Source: Olist public dataset (Kaggle, CC BY-NC-SA 4.0) · SQL in PostgreSQL & MySQL · Power BI · Built by Bikashit Baruah', 11, MUTED)]]))
pages.append(page_json('home', 'Home', v))

# ---- Executive ----
v = top_bar('exec') + filter_panel('exec')
v.append(kpi(X1, 100, KW, 150, 'Late %', 'Late %', 'Callout Late %', color_measure='COLOR Late %'))
v.append(kpi(X2, 100, KW, 150, 'Avg Review', 'Avg Review', 'Callout Avg Review', color_measure='COLOR Avg Review'))
v.append(kpi(X3, 100, KW, 150, 'Bad Review %', 'Bad Review %', 'Callout Bad Review %', color_measure='COLOR Bad Review %'))
v.append(kpi(X4, 100, KW, 150, 'Avg Days to Deliver', 'Avg Days to Deliver', 'Callout Avg Days', color_measure='COLOR Avg Days'))
v.append(text_card(400, 265, 1490, 50, 'Headline Insight', size=13))
trend = chart(400, 330, 880, 360, 'lineChart',
              {'Category': [COLM('dim_date', 'Month Start')], 'Y': [MEAS('Late %'), MEAS('Bad Review %')],
               'Tooltips': [MEAS('Delivered Orders'), MEAS('Late Orders')]},
              title='Trend: late % and bad-review % by month (Jan 2017 – Aug 2018)',
              objects={'categoryAxis': AXIS(), 'valueAxis': VAXIS(), 'legend': LEGEND(),
                       'dataPoint': [{'properties': {'fill': C(BAD)}, 'selector': sel_meta(MEAS('Late %'))},
                                     {'properties': {'fill': C(BLUE)}, 'selector': sel_meta(MEAS('Bad Review %'))}],
                       'lineStyles': [props(strokeWidth=D(2), showMarker=L(True), markerSize=D(4))],
                       'labels': LABELS(False)},
              filters=[f_in('dim_date', 'In Trend Window', [1])], sort=(COLM('dim_date', 'Month Start'), 'Ascending'),
              alt='Late % and bad-review % by month; both peak in Nov 2017 and Feb-Mar 2018')
v.append(trend)
v.append(chart(1300, 330, 590, 360, 'clusteredColumnChart',
               {'Category': [COLM('fact_delivery', 'delay_bucket')], 'Y': [MEAS('Bad Review %')]},
               title='Bad reviews by delivery timing', subtitle='Share of 1–2 star reviews',
               objects={'categoryAxis': AXIS(), 'valueAxis': VAXIS(False), 'labels': LABELS(True, INK),
                        'dataPoint': [{'properties': {'fill': CM('COLOR Bucket')}, 'selector': sel_wild()}]},
               sort=(COLM('fact_delivery', 'delay_bucket'), 'Ascending')))
v.append(chart(400, 710, 735, 340, 'pivotTable',
               {'Rows': [COLM('dim_state', 'State')], 'Values': [MEAS('Late %'), MEAS('Late % vs Brazil (pp)'), MEAS('Avg Days to Deliver'), MEAS('Share of Late Orders')]},
               title='Top 5 customer states by late %', objects=matrix_objects(bar_measures=['Late %']),
               filters=[f_measure('Show State Top5', 0, 1)], sort=(MEAS('Late %'), 'Descending')))
v.append(chart(1155, 710, 735, 340, 'pivotTable',
               {'Rows': [COLM('fact_order_seller', 'Lane')], 'Values': [MEAS('Order-Seller Pairs'), MEAS('Lane Late %'), MEAS('Lane Share of Late'), MEAS('Lane Avg Days Promised')]},
               title='Top 5 lanes by late orders', objects=matrix_objects(bar_measures=['Lane Late %']),
               filters=[f_measure('Show Lane Top5', 0, 1)], sort=(MEAS('Lane Share of Late'), 'Descending')))
pages.append(page_json('exec', 'Executive', v, interactions=no_time_filter('exec', [trend['name']])))

# ---- Delivery ----
v = top_bar('delivery') + filter_panel('delivery')
v.append(kpi(X1, 100, KW, 150, 'Late %', 'Late %', 'Callout Late %', color_measure='COLOR Late %'))
v.append(kpi(X2, 100, KW, 150, 'Avg Days to Deliver', 'Avg Days to Deliver', 'Callout Avg Days', color_measure='COLOR Avg Days'))
v.append(kpi(X3, 100, KW, 150, 'Promise Buffer (days)', 'Promise Buffer (days)', callout_text='Avg days promised − avg days taken', color=GOOD))
v.append(kpi(X4, 100, KW, 150, 'Seller Late Handover %', 'Seller Late Handover %', callout_text='Seller missed the ship-by date', color=BAD))
v.append(slicer(400, 265, 590, 50, 'dim_metric', 'Metric', None, default='Late %', single=True))
v.append(chart(400, 330, 590, 720, 'clusteredBarChart',
               {'Category': [COLM('dim_state', 'State')], 'Y': [MEAS('Metric Value')], 'Tooltips': [MEAS('Delivered Orders')]},
               title_measure='Metric Title',
               objects={'categoryAxis': AXIS(), 'valueAxis': VAXIS(False), 'labels': LABELS(True, INK),
                        'dataPoint': [props(fill=C(BAD))]},
               filters=[f_measure('Delivered Orders', 2, 200)], sort=(MEAS('Metric Value'), 'Descending'),
               tooltip_page=PID['tt']))
v.append(chart(1010, 265, 880, 420, 'pivotTable',
               {'Rows': [COLM('dim_seller', 'Seller Region')], 'Columns': [COLM('dim_state', 'Region')], 'Values': [MEAS('Lane Late %')]},
               title='Late % by lane: seller region (rows) × customer region (columns)',
               objects={**matrix_objects(gradient_measure='Lane Late %'), 'grid': [props(gridHorizontal=L(True), gridHorizontalColor=C(LINE), gridVertical=L(True), gridVerticalColor=C(LINE), rowPadding=D(14))]}))
v.append(chart(1010, 705, 420, 345, 'clusteredBarChart',
               {'Y': [MEAS('Late % After On-Time Handover'), MEAS('Late % After Late Handover')]},
               title='Where lateness starts', subtitle='Late % after the seller handed over on time vs late',
               objects={'categoryAxis': AXIS(), 'valueAxis': VAXIS(False), 'labels': LABELS(True, INK), 'legend': LEGEND(),
                        'dataPoint': [{'properties': {'fill': C(GOOD)}, 'selector': sel_meta(MEAS('Late % After On-Time Handover'))},
                                      {'properties': {'fill': C(BAD)}, 'selector': sel_meta(MEAS('Late % After Late Handover'))}]}))
v.append(text_card(1030, 990, 380, 44, 'Headline Insight', size=9, color=SOFT, bg=False))
v.append(chart(1450, 705, 440, 345, 'scatterChart',
               {'Category': [COLM('fact_order_seller', 'Lane')], 'X': [MEAS('Lane Avg Days Promised')], 'Y': [MEAS('Lane Late %')], 'Size': [MEAS('Order-Seller Pairs')]},
               title='Promise vs reality by lane (300+ orders)',
               objects={'categoryAxis': AXIS(), 'valueAxis': VAXIS(), 'categoryLabels': [props(show=L(True), color=C(SOFT), fontSize=D(8))],
                        'dataPoint': [props(fill=C(BAD))]},
               filters=[f_measure('Order-Seller Pairs', 2, 300)]))
pages.append(page_json('delivery', 'Delivery', v))

# ---- Customer ----
v = top_bar('customer') + filter_panel('customer')
v.append(kpi(X1, 100, KW, 150, 'Avg Review', 'Avg Review', 'Callout Avg Review', color_measure='COLOR Avg Review'))
v.append(kpi(X2, 100, KW, 150, 'Bad Review %', 'Bad Review %', 'Callout Bad Review %', color_measure='COLOR Bad Review %'))
v.append(kpi(X3, 100, KW, 150, 'Review Gap', 'Review Gap (stars)', callout_text='On-time minus late average review', color=BAD))
rep_kpi = kpi(X4, 100, KW, 150, 'Repeat Rate First Late', 'Came back (all years)', callout_text='First order late · 2.86% if on time', color=BAD)
v.append(rep_kpi)
v.append(chart(400, 270, 880, 380, 'clusteredColumnChart',
               {'Category': [COLM('fact_delivery', 'delay_bucket')], 'Y': [MEAS('Bad Review %')]},
               title='Bad-review % by delivery timing', subtitle='From 4 days late, about 2 in 3 reviews are 1–2 stars',
               objects={'categoryAxis': AXIS(), 'valueAxis': VAXIS(False), 'labels': LABELS(True, INK),
                        'dataPoint': [{'properties': {'fill': CM('COLOR Bucket')}, 'selector': sel_wild()}]},
               sort=(COLM('fact_delivery', 'delay_bucket'), 'Ascending')))
star_cols = {1: BAD, 2: '#B4A9FF', 3: MUTED, 4: '#9BD16A', 5: GOOD}
dp = []
for s, c in star_cols.items():
    dp.append({'properties': {'fill': C(c)}, 'selector': {'data': [{'scopeId': {'Comparison': {'ComparisonKind': 0,
              'Left': COLM('fact_delivery', 'review_score'), 'Right': {'Literal': {'Value': f'{s}L'}}}}}]}})
v.append(chart(1300, 270, 590, 380, 'hundredPercentStackedBarChart',
               {'Category': [COLM('fact_delivery', 'Delivery Status')], 'Series': [COLM('fact_delivery', 'review_score')], 'Y': [MEAS('Review Count')]},
               title='Star mix: late vs on time', subtitle='Share of reviews by star rating (1 = worst)',
               objects={'categoryAxis': AXIS(), 'valueAxis': VAXIS(False), 'legend': LEGEND(), 'labels': LABELS(True, '#070B14'), 'dataPoint': dp},
               filters=[f_in('fact_delivery', 'review_score', [1, 2, 3, 4, 5])]))
v.append(chart(400, 670, 880, 380, 'lineChart',
               {'Category': [COLM('fact_delivery', 'days_vs_promise')], 'Y': [MEAS('Avg Review')], 'Tooltips': [MEAS('Reviewed Orders')]},
               title='Average review by days vs promise', subtitle='Negative = early, 0 = promised date, positive = late',
               objects={'categoryAxis': AXIS(), 'valueAxis': VAXIS(), 'labels': LABELS(False),
                        'dataPoint': [props(fill=C(BLUE))], 'lineStyles': [props(strokeWidth=D(2), showMarker=L(True), markerSize=D(3))]},
               filters=[f_in('fact_delivery', 'In Review Window', [1])], sort=(COLM('fact_delivery', 'days_vs_promise'), 'Ascending')))
rep = chart(1300, 670, 590, 380, 'clusteredColumnChart',
            {'Y': [MEAS('Repeat Rate First On Time'), MEAS('Repeat Rate First Late')]},
            title='Did customers come back?', subtitle='All years · correlation only',
            objects={'categoryAxis': AXIS(), 'valueAxis': VAXIS(False), 'labels': LABELS(True, INK), 'legend': LEGEND(),
                     'dataPoint': [{'properties': {'fill': C(GOOD)}, 'selector': sel_meta(MEAS('Repeat Rate First On Time'))},
                                   {'properties': {'fill': C(BAD)}, 'selector': sel_meta(MEAS('Repeat Rate First Late'))}]})
v.append(rep)
pages.append(page_json('customer', 'Customer', v, interactions=no_time_filter('customer', [rep['name'], rep_kpi['name']])))

# ---- Seller ----
v = top_bar('seller') + filter_panel('seller')
v.append(kpi(X1, 100, KW, 150, 'Sellers 30+', 'Sellers (30+ orders)', callout_text='Sellers big enough to score', color=GOOD))
v.append(kpi(X2, 100, KW, 150, 'Seller Late Handover %', 'Seller Late Handover %', callout_text='Seller missed the ship-by date', color=BAD))
v.append(kpi(X3, 100, KW, 150, 'Worst Decile Share of Late', 'Worst-Decile Share', callout_text='Late orders from the worst 10% of sellers', color=BAD))
v.append(kpi(X4, 100, KW, 150, 'Late % After Late Handover', 'Late % After Late Handover', callout_text='Compare: late % after an on-time handover', color=BAD))
v.append(chart(400, 270, 735, 330, 'clusteredColumnChart',
               {'Category': [COLM('dim_seller', 'Seller Decile Label')], 'Y': [MEAS('Lane Late %')], 'Tooltips': [MEAS('Share of Late Pairs'), MEAS('Order-Seller Pairs')]},
               title='Late % by seller decile (D1 = worst)', subtitle='Deciles fixed on all-time data, sellers with 30+ orders',
               objects={'categoryAxis': AXIS(), 'valueAxis': VAXIS(False), 'labels': LABELS(True, INK),
                        'dataPoint': [{'properties': {'fill': CM('COLOR Decile')}, 'selector': sel_wild()}]},
               filters=[f_in('dim_seller', 'Seller Decile Label', ['Under 30 orders'], negate=True)],
               sort=(COLM('dim_seller', 'Seller Decile Label'), 'Ascending')))
v.append(chart(1155, 270, 735, 330, 'pivotTable',
               {'Rows': [COLM('dim_seller', 'Seller Region'), COLM('dim_seller', 'seller_state')],
                'Values': [MEAS('Order-Seller Pairs'), MEAS('Lane Late %'), MEAS('Seller Late Handover %'), MEAS('Seller Avg Review')]},
               title='Seller region scorecard', objects=matrix_objects(bar_measures=['Lane Late %'])))
v.append(textbox(400, 620, 120, 44, [[T('TOP N', 10, MUTED, True)]]))
v.append(slicer(480, 618, 420, 46, 'Top N', 'Top N', None, default=10, single=True))
v.append(chart(400, 680, 1490, 370, 'tableEx',
               {'Values': [COLM('dim_seller', 'Seller Short'), COLM('dim_seller', 'seller_city'), COLM('dim_seller', 'seller_state'),
                           MEAS('Seller Orders'), MEAS('Lane Late %'), MEAS('Seller Late Handover %'), MEAS('Seller Avg Review'), MEAS('Seller Risk')]},
               title='Top N sellers to coach (highest late %, 30+ orders)',
               objects=matrix_objects(bar_measures=['Lane Late %'], font_color=('Seller Risk', 'COLOR Seller Risk')),
               filters=[f_measure('Show In Top N', 0, 1)], sort=(MEAS('Lane Late %'), 'Descending')))
pages.append(page_json('seller', 'Seller', v))

# ---- Data Checks ----
v = top_bar('checks')
v.append(textbox(40, 100, 1220, 110, [[T('Every headline number reconciles to SQL', 26, INK, True)],
                                      [T('Power BI measures compared with saved PostgreSQL / MySQL query results (olist/results). No slicers apply on this page.', 12, SOFT)]]))
v.append(kpi(1280, 100, 610, 120, 'Checks Summary', 'Data checks', callout_text='Tolerance: rounding used in the SQL output', color=GOOD, fmt_size=22))
v.append(chart(40, 240, 1220, 560, 'tableEx',
               {'Values': [COLM('sql_check', 'Check No'), COLM('sql_check', 'Check'), COLM('sql_check', 'SQL Source'),
                           COLM('sql_check', 'SQL Value'), MEAS('PBI Value'), MEAS('Check Status')]},
               title='Reconciliation table', objects=matrix_objects(font_color=('Check Status', 'COLOR Check')),
               sort=(COLM('sql_check', 'Check No'), 'Ascending')))
v.append(shape(1280, 240, 610, 560, PANEL, outline=LINE, radius=12, z=200))
v.append(textbox(1300, 256, 570, 530, [
    [T('Data decisions', 15, LIME, True)],
    [T('• 547 orders had 2+ reviews → latest review kept', 11, SOFT)],
    [T('• 8 delivered orders had no delivery date → excluded', 11, SOFT)],
    [T('• 99,441 customer IDs = 96,096 people → repeat buying by person', 11, SOFT)],
    [T('• Payments match items + freight for 99.7% of orders', 11, SOFT)],
    [T('• Seller and lane measures count order–seller pairs (1.3% of orders have two sellers)', 11, SOFT)],
    [T('• Seller deciles: sellers with 30+ orders, ties broken by seller_id', 11, SOFT)],
    [T('• Repeat buying = bought again at a later time (same-second orders are one checkout)', 11, SOFT)],
    [T('• vs LY compares the same dates last year and shows n/a under 300 orders', 11, SOFT)],
    [T('• Targets on KPI cards are illustrative goals', 11, SOFT)]], z=90000))
v.append(shape(40, 820, 1850, 230, PANEL, outline=LINE, radius=12, z=200))
v.append(textbox(60, 836, 1800, 200, [
    [T('Model', 15, LIME, True)],
    [T('Star schema: dim_date, dim_state → fact_delivery (one row per delivered order) → fact_order_seller (one row per order × seller) ← dim_seller. first_order is 1:1 with fact_delivery.', 11, SOFT)],
    [T('Disconnected tables drive the switches: dim_bm (benchmark), dim_metric (metric), Top N, sql_check. Source: SQL views pbi_delivery, pbi_order_seller, pbi_seller, pbi_first_order.', 11, SOFT)]], z=90000))
pages.append(page_json('checks', 'Data Checks', v))

# ---- About ----
v = top_bar('about')
boxes = [
    (40, 100, 'What this is', ['A Power BI report on 96,470 real delivered orders from Olist, a Brazilian online marketplace (Sep 2016 – Aug 2018).',
                               'Question: how much does late delivery hurt customers, and where should a logistics team look first?']),
    (980, 100, 'Definitions', ['Late = delivered on a later calendar day than the date promised at purchase.', 'Bad review = 1 or 2 stars.',
                               'vs LY = same dates last year; n/a when last year has under 300 orders.',
                               'Targets (illustrative): late ≤ 5%, review ≥ 4.2, bad reviews ≤ 10%, ≤ 12 days.']),
    (40, 580, 'How it was built', ['SQL (PostgreSQL / MySQL) views → Power Query → star schema → DAX measures → checked against saved SQL results (Data Checks page).',
                                   'Source and SQL: github.com/davarkk10/bikashit-portfolio (folder olist).']),
    (980, 580, 'Limits', ['Correlation, not cause.', 'Brazil 2016–2018 only.', 'No carrier name in the data, so "delivery leg" means the time after the seller handed over.',
                          'Seller and lane numbers count order–seller pairs.'])]
for x, y, head, lines in boxes:
    v.append(shape(x, y, 900, 460, PANEL, outline=LINE, radius=12, z=200))
    v.append(textbox(x + 24, y + 20, 852, 420, [[T(head, 18, LIME, True)]] + [[T(l, 13, SOFT)] for l in lines], z=90000))
pages.append(page_json('about', 'About', v))

# ---- TT State (tooltip) ----
v = [shape(0, 0, 640, 360, PANEL, outline=LINE, z=10)]
v.append(visual(16, 12, 608, 50, 'cardVisual', query={'queryState': {'Data': {'projections': [proj({'Aggregation': {'Expression': COLM('dim_state', 'State'), 'Function': 3}})]}}},
                objects={'value': [props(fontSize=D(18), fontColor=C(LIME), fontFamily={'expr': {'Literal': {'Value': BOLD}}})],
                         'label': [props(show=L(False))], 'fillCustom': [props(show=L(False))], 'outline': [props(show=L(False))]},
                vco=container(bg=False, border=False, pad=0)))
v.append(kpi(16, 70, 296, 100, 'Late %', 'Late %', 'Callout Late %', color_measure='COLOR Late %', fmt_size=22))
v.append(kpi(328, 70, 296, 100, 'Avg Days to Deliver', 'Avg Days to Deliver', 'Callout Avg Days', color_measure='COLOR Avg Days', fmt_size=22))
v.append(chart(16, 182, 608, 166, 'lineChart', {'Category': [COLM('dim_date', 'Month Start')], 'Y': [MEAS('Late %')]},
               title='Late % by month', objects={'categoryAxis': AXIS(), 'valueAxis': VAXIS(False), 'dataPoint': [props(fill=C(BAD))]},
               filters=[f_in('dim_date', 'In Trend Window', [1])]))
pages.append(page_json('tt', 'TT State', v, width=640, height=360, ptype='Tooltip', hidden=True))
