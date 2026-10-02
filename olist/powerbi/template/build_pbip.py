# Writes Olist Delivery 360 as a Power BI Project (.pbip) folder
import json, os, shutil, sys, uuid
sys.path.insert(0, os.path.dirname(__file__))
import build_model, build_report as R
from pack import theme, THEME_NAME

NAME = 'Olist_Delivery_360'
ROOT = f'/home/claude/olist_pbit/pbip/{NAME}'
REP, SEM = f'{ROOT}/{NAME}.Report', f'{ROOT}/{NAME}.SemanticModel'

def w(path, obj, raw=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(obj if raw else json.dumps(obj, ensure_ascii=False, indent=2))

def main():
    if os.path.exists(ROOT): shutil.rmtree(ROOT)
    w(f'{ROOT}/{NAME}.pbip', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json',
                             'version': '1.0', 'artifacts': [{'report': {'path': f'{NAME}.Report'}}],
                             'settings': {'enableAutoRecovery': True}})
    plat = lambda typ: {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json',
                        'metadata': {'type': typ, 'displayName': NAME}, 'config': {'version': '2.0', 'logicalId': str(uuid.uuid4())}}
    # semantic model
    w(f'{SEM}/.platform', plat('SemanticModel'))
    w(f'{SEM}/definition.pbism', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json',
                                  'version': '1.0', 'settings': {}})
    bim = dict(build_model.model); bim['name'] = 'SemanticModel'
    w(f'{SEM}/model.bim', bim)
    # report
    w(f'{REP}/.platform', plat('Report'))
    w(f'{REP}/definition.pbir', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json',
                                 'version': '4.0', 'datasetReference': {'byPath': {'path': f'../{NAME}.SemanticModel'}}})
    d = f'{REP}/definition'
    w(f'{d}/version.json', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json', 'version': '2.0.0'})
    w(f'{d}/report.json', {
        '$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json',
        'themeCollection': {'customTheme': {'name': THEME_NAME, 'reportVersionAtImport': {'visual': '1.8.95', 'report': '2.0.95', 'page': '1.3.95'}, 'type': 'RegisteredResources'}},
        'objects': {'outspacePane': [{'properties': {'expanded': {'expr': {'Literal': {'Value': 'false'}}}}}]},
        'resourcePackages': [{'name': 'RegisteredResources', 'type': 'RegisteredResources', 'items': [{'name': THEME_NAME, 'path': THEME_NAME, 'type': 'CustomTheme'}]}],
        'settings': {'useStylableVisualContainerHeader': True, 'exportDataMode': 'AllowSummarized', 'defaultDrillFilterOtherVisuals': True,
                     'allowChangeFilterTypes': True, 'useEnhancedTooltips': True}})
    w(f'{REP}/StaticResources/RegisteredResources/{THEME_NAME}', theme)
    w(f'{d}/pages/pages.json', {'$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json',
                               'pageOrder': [R.PID[k] for k, _ in R.PAGES], 'activePageName': R.PID['home']})
    n = 0
    for pj, visuals in R.pages:
        w(f"{d}/pages/{pj['name']}/page.json", pj)
        for v in visuals:
            w(f"{d}/pages/{pj['name']}/visuals/{v['name']}/visual.json", v); n += 1
    # data + readme
    shutil.copytree('/home/claude/olist_pbit/Olist_Delivery_360/data', f'{ROOT}/data')
    w(f'{ROOT}/README.txt', r'''OLIST DELIVERY 360 - Power BI Project (reference build)
=======================================================

1. Unzip so this folder is  C:\olist\Olist_Delivery_360\   (the data must be in  C:\olist\Olist_Delivery_360\data\ )
2. Double-click  Olist_Delivery_360.pbip  (latest Power BI Desktop).
   The report opens with empty visuals: a project stores no data.
3. Home > Refresh. Loading takes about a minute.
   If your data is in a different folder: Home > Transform data > Edit parameters > DataFolder
   (full path ending with a backslash) > OK > Apply changes.
4. File > Save as > Olist_Delivery_360_reference.pbix  if you want a single file.

Check: Data Checks page = 12 / 12 checks match SQL. Executive (2018, vs LY): 7.7% | 4.14 | 13.4% | 12.1

Data: Brazilian E-Commerce Public Dataset by Olist (Kaggle), CC BY-NC-SA 4.0.
''', raw=True)
    print('pbip written:', n, 'visuals')

if __name__ == '__main__':
    main()
