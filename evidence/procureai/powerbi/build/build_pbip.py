"""Writes ProcureAI Model Results as a Power BI Project (.pbip) folder and a .pbit template.

Usage: python build_pbip.py <data folder with the CSVs> [output folder]
Default output: ../ProcureAI_Model_Results (next to this build folder)
"""
import json
import os
import shutil
import sys
import uuid
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import procure_model as MOD  # noqa: E402
import procure_report as R  # noqa: E402

NAME = 'ProcureAI_Model_Results'
DATA = sys.argv[1]
ROOT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, '..', NAME)
REP, SEM = f'{ROOT}/{NAME}.Report', f'{ROOT}/{NAME}.SemanticModel'
REPORT_JSON = {
    '$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json',
    'themeCollection': {'customTheme': {'name': R.THEME_NAME, 'reportVersionAtImport': {'visual': '1.8.95', 'report': '2.0.95', 'page': '1.3.95'},
                                        'type': 'RegisteredResources'}},
    'objects': {'outspacePane': [{'properties': {'expanded': {'expr': {'Literal': {'Value': 'false'}}}}}]},
    'resourcePackages': [{'name': 'RegisteredResources', 'type': 'RegisteredResources',
                          'items': [{'name': R.THEME_NAME, 'path': R.THEME_NAME, 'type': 'CustomTheme'}]}],
    'settings': {'useStylableVisualContainerHeader': True, 'exportDataMode': 'AllowSummarized', 'defaultDrillFilterOtherVisuals': True,
                 'allowChangeFilterTypes': True, 'useEnhancedTooltips': True}}
PAGES_JSON = {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json',
              'pageOrder': [R.PID[k] for k, _ in R.PAGES], 'activePageName': R.PID['home']}
VERSION_JSON = {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json', 'version': '2.0.0'}

README = r'''PROCUREAI FMCG - MODEL RESULTS (Power BI Project)
==================================================

1. Unzip so this folder is  C:\ProcureAI\   with the CSVs in  C:\ProcureAI\data\
2. Double-click  ProcureAI_Model_Results.pbip  (latest Power BI Desktop; File > Options > Preview features >
   "Power BI Project (.pbip) save option" and "Store reports using enhanced metadata format (PBIR)" switched on).
   The report opens with empty visuals: a project stores no data.
3. Home > Refresh. Loading takes under a minute.
   Data somewhere else? Home > Transform data > Edit parameters > DataFolder (full path ending with \) > OK > Apply changes.
4. Optional: File > Save as > ProcureAI_Model_Results.pbix for a single file, then publish.
   No PBIP support? Open ProcureAI_Model_Results.pbit instead (same model and pages); it asks for DataFolder.

Check after refresh (data\expected_values.json has the full list):
  Invoice risk:  model 92.6% of 1,546 flagged are real; best rules 74.6% of 1,707
  Late delivery: 66.8% of flagged POs (3 days before) arrive late; test late rate 36.9%
  Contract:      64 / 68, 0 wrong answers, 6 / 6 refusals

Pages: Home, Invoice risk, Late delivery, Contract assistant, About.
All data is synthetic. Rebuild everything with the scripts in evidence/procureai (see build/README.md).
'''


def w(path, obj, raw=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(obj if raw else json.dumps(obj, ensure_ascii=False, indent=2))


def plat(typ):
    return {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json',
            'metadata': {'type': typ, 'displayName': NAME},
            'config': {'version': '2.0', 'logicalId': str(uuid.uuid5(uuid.NAMESPACE_URL, f'procureai/{typ}'))}}


def write_pbip():
    if os.path.exists(ROOT):
        shutil.rmtree(ROOT)
    w(f'{ROOT}/{NAME}.pbip', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json',
                             'version': '1.0', 'artifacts': [{'report': {'path': f'{NAME}.Report'}}], 'settings': {'enableAutoRecovery': True}})
    w(f'{SEM}/.platform', plat('SemanticModel'))
    w(f'{SEM}/definition.pbism', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json',
                                  'version': '1.0', 'settings': {}})
    w(f'{SEM}/model.bim', MOD.model)
    w(f'{REP}/.platform', plat('Report'))
    w(f'{REP}/definition.pbir', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json',
                                 'version': '4.0', 'datasetReference': {'byPath': {'path': f'../{NAME}.SemanticModel'}}})
    d = f'{REP}/definition'
    w(f'{d}/version.json', VERSION_JSON)
    w(f'{d}/report.json', REPORT_JSON)
    w(f'{REP}/StaticResources/RegisteredResources/{R.THEME_NAME}', R.theme)
    w(f'{d}/pages/pages.json', PAGES_JSON)
    n = 0
    for pj, visuals in R.pages:
        w(f"{d}/pages/{pj['name']}/page.json", pj)
        for v in visuals:
            w(f"{d}/pages/{pj['name']}/visuals/{v['name']}/visual.json", v)
            n += 1
    w(f'{ROOT}/.gitignore', '**/.pbi/localSettings.json\n**/.pbi/cache.abf\n', raw=True)
    os.makedirs(f'{ROOT}/data', exist_ok=True)
    for f in sorted(os.listdir(DATA)):
        if f.endswith(('.csv', '.json')):
            shutil.copy(os.path.join(DATA, f), f'{ROOT}/data/{f}')
    w(f'{ROOT}/README.txt', README, raw=True)
    return n


def write_pbit():
    u16 = lambda s: s.encode('utf-16-le')
    files = {
        'Version': u16('1.32'),
        'Settings': u16(json.dumps({'Version': 4, 'ReportSettings': {'IsRelationshipAutodetectionEnabled': False},
                                    'QueriesSettings': {'TypeDetectionEnabled': True, 'RelationshipImportEnabled': False, 'Version': '2.145.905.0'}},
                                   separators=(',', ':'))),
        'Metadata': u16(json.dumps({'Version': 5, 'AutoCreatedRelationships': [], 'CreatedFrom': 'Cloud', 'CreatedFromRelease': '2026.08'},
                                   separators=(',', ':'))),
        'DataModelSchema': u16(json.dumps(MOD.model, ensure_ascii=False, indent=2)),
        'Report/definition/version.json': json.dumps(VERSION_JSON).encode(),
        'Report/definition/report.json': json.dumps(REPORT_JSON, ensure_ascii=False).encode(),
        f'Report/StaticResources/RegisteredResources/{R.THEME_NAME}': json.dumps(R.theme, indent=2).encode(),
        'Report/definition/pages/pages.json': json.dumps(PAGES_JSON).encode(),
    }
    for pj, visuals in R.pages:
        base = f"Report/definition/pages/{pj['name']}"
        files[f'{base}/page.json'] = json.dumps(pj, ensure_ascii=False).encode()
        for v in visuals:
            files[f"{base}/visuals/{v['name']}/visual.json"] = json.dumps(v, ensure_ascii=False).encode()
    ct = ('<?xml version="1.0" encoding="utf-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="json" ContentType="" /><Override PartName="/Version" ContentType="" />'
          '<Override PartName="/Settings" ContentType="application/json" /><Override PartName="/Metadata" ContentType="application/json" />'
          '<Override PartName="/DataModelSchema" ContentType="" /></Types>')
    out = f'{ROOT}/{NAME}.pbit'
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('Version', files.pop('Version'))
        z.writestr('[Content_Types].xml', b'\xef\xbb\xbf' + ct.encode())
        for k in ['DataModelSchema', 'Settings', 'Metadata']:
            z.writestr(k, files.pop(k))
        for k, v in files.items():
            z.writestr(k, v)
    return out


if __name__ == '__main__':
    n = write_pbip()
    p = write_pbit()
    print('pbip written:', ROOT, '|', len(R.pages), 'pages,', n, 'visuals |', 'pbit:', os.path.getsize(p), 'bytes')
