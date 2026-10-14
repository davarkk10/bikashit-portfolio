# Shared PBIR helpers (adapted from the Olist Delivery 360 builder in olist/powerbi/template)
import json, hashlib, itertools

SCHEMA_V = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.12.0/schema.json'
SCHEMA_P = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json'

# ProcureAI case-study palette (dark green-black with teal accent)
BG, PANEL, PANEL2, LINE = '#07110F', '#10211D', '#0B1815', '#24413A'
INK, SOFT, MUTED = '#EEF6F2', '#C2D4CD', '#8FA49C'
LIME, MINT = '#46E8BD', '#9BF7DC'          # LIME = accent (kept name for the shared helpers)
GOOD, BAD, AMBER, BLUE = '#46E8BD', '#FF8A7A', '#FFCB66', '#5B9BE8'
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

