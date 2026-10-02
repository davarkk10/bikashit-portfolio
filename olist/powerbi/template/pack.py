import json, zipfile, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import build_model, build_report as R

OUT = '/home/claude/olist_pbit/Olist_Delivery_360/Olist_Delivery_360.pbit'
THEME_NAME = 'Olist_Delivery_360_Case4_dark.json'

theme = {
    'name': 'Olist Delivery 360 (Case 4 dark)',
    'dataColors': [R.GOOD, R.BAD, R.AMBER, R.BLUE, R.MINT, R.LIME, '#B4A9FF', '#9BD16A'],
    'good': R.GOOD, 'neutral': R.AMBER, 'bad': R.BAD,
    'maximum': R.BAD, 'center': '#4B4F7A', 'minimum': R.PANEL,
    'foreground': R.INK, 'foregroundNeutralSecondary': R.SOFT, 'foregroundNeutralTertiary': R.MUTED,
    'background': R.PANEL, 'backgroundLight': '#1B2A42', 'backgroundNeutral': R.LINE,
    'tableAccent': R.LIME, 'hyperlink': R.LIME, 'visitedHyperlink': R.MINT,
    'textClasses': {
        'callout': {'fontSize': 28, 'fontFace': 'Segoe UI Bold', 'color': R.INK},
        'title': {'fontSize': 12, 'fontFace': 'Segoe UI Semibold', 'color': R.INK},
        'header': {'fontSize': 12, 'fontFace': 'Segoe UI Semibold', 'color': R.INK},
        'label': {'fontSize': 10, 'fontFace': 'Segoe UI', 'color': R.SOFT},
    },
    'visualStyles': {
        '*': {'*': {
            'background': [{'show': True, 'color': {'solid': {'color': R.PANEL}}, 'transparency': 0}],
            'border': [{'show': True, 'color': {'solid': {'color': R.LINE}}, 'radius': 12}],
            'dropShadow': [{'show': False}],
            'title': [{'show': True, 'fontColor': {'solid': {'color': R.INK}}, 'fontSize': 12, 'fontFamily': 'Segoe UI Semibold'}],
            'subTitle': [{'fontColor': {'solid': {'color': R.MUTED}}}],
            'categoryAxis': [{'labelColor': {'solid': {'color': R.SOFT}}, 'titleColor': {'solid': {'color': R.MUTED}}}],
            'valueAxis': [{'labelColor': {'solid': {'color': R.MUTED}}, 'titleColor': {'solid': {'color': R.MUTED}},
                           'gridlineColor': {'solid': {'color': R.LINE}}}],
            'legend': [{'labelColor': {'solid': {'color': R.SOFT}}}],
            'labels': [{'color': {'solid': {'color': R.INK}}}],
            'visualHeader': [{'foreground': {'solid': {'color': R.SOFT}}, 'background': {'solid': {'color': R.PANEL}}}],
        }},
        'page': {'*': {'background': [{'color': {'solid': {'color': R.BG}}, 'transparency': 0}],
                       'outspace': [{'color': {'solid': {'color': R.BG}}}]}},
        'filterCard': {'*': {'backgroundColor': [{'solid': {'color': R.PANEL}}], 'foregroundColor': [{'solid': {'color': R.INK}}]}},
    },
}

def u16(s): return s.encode('utf-16-le')

def main():
    files = {}
    files['Version'] = u16('1.32')
    files['Settings'] = u16(json.dumps({'Version': 4, 'ReportSettings': {'IsRelationshipAutodetectionEnabled': False},
                                        'QueriesSettings': {'TypeDetectionEnabled': True, 'RelationshipImportEnabled': False, 'Version': '2.145.905.0'}}, separators=(',', ':')))
    files['Metadata'] = u16(json.dumps({'Version': 5, 'AutoCreatedRelationships': [], 'CreatedFrom': 'Cloud', 'CreatedFromRelease': '2026.08'}, separators=(',', ':')))
    files['DataModelSchema'] = u16(json.dumps(build_model.model, ensure_ascii=False, indent=2))
    files['Report/definition/version.json'] = json.dumps({'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json', 'version': '2.0.0'}).encode()
    report = {
        '$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json',
        'themeCollection': {'customTheme': {'name': THEME_NAME, 'reportVersionAtImport': {'visual': '1.8.95', 'report': '2.0.95', 'page': '1.3.95'}, 'type': 'RegisteredResources'}},
        'objects': {'outspacePane': [{'properties': {'expanded': {'expr': {'Literal': {'Value': 'false'}}}}}]},
        'resourcePackages': [{'name': 'RegisteredResources', 'type': 'RegisteredResources',
                              'items': [{'name': THEME_NAME, 'path': THEME_NAME, 'type': 'CustomTheme'}]}],
        'settings': {'useStylableVisualContainerHeader': True, 'exportDataMode': 'AllowSummarized', 'defaultDrillFilterOtherVisuals': True,
                     'allowChangeFilterTypes': True, 'useEnhancedTooltips': True},
    }
    files['Report/definition/report.json'] = json.dumps(report, ensure_ascii=False).encode()
    files[f'Report/StaticResources/RegisteredResources/{THEME_NAME}'] = json.dumps(theme, indent=2).encode()
    order = [R.PID[k] for k, _ in R.PAGES]
    files['Report/definition/pages/pages.json'] = json.dumps({'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json',
                                                             'pageOrder': order, 'activePageName': R.PID['home']}).encode()
    nvis = 0
    for pj, visuals in R.pages:
        base = f"Report/definition/pages/{pj['name']}"
        files[f'{base}/page.json'] = json.dumps(pj, ensure_ascii=False).encode()
        for v in visuals:
            files[f"{base}/visuals/{v['name']}/visual.json"] = json.dumps(v, ensure_ascii=False).encode()
            nvis += 1
    ct = ('<?xml version="1.0" encoding="utf-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="json" ContentType="" /><Override PartName="/Version" ContentType="" />'
          '<Override PartName="/Settings" ContentType="application/json" /><Override PartName="/Metadata" ContentType="application/json" />'
          '<Override PartName="/DataModelSchema" ContentType="" /></Types>')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('Version', files.pop('Version'))
        z.writestr('[Content_Types].xml', b'\xef\xbb\xbf' + ct.encode())
        for k in ['DataModelSchema', 'Settings', 'Metadata']:
            z.writestr(k, files.pop(k))
        for k, v in files.items():
            z.writestr(k, v)
    print('wrote', OUT, os.path.getsize(OUT), 'bytes;', len(R.pages), 'pages;', nvis, 'visuals')

if __name__ == '__main__':
    main()
