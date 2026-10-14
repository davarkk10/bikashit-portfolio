"""Static checks for the generated Power BI project (no Power BI Desktop needed).

1. Every JSON file parses.
2. Every table[column] and [measure] reference in DAX resolves; brackets and parentheses balance.
3. Every field a visual uses (Entity + Property) exists in the model.
4. sortByColumn targets and relationship columns exist; CSV headers match the column list.
5. Every page-navigation button points at a real page.

Usage: python check_pbip.py <pbip folder>
"""
import csv
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1]); name = root.name
errors = []
files = list(root.rglob('*.json')) + list(root.rglob('*.bim')) + list(root.rglob('*.pbip')) + list(root.rglob('*.pbir')) + list(root.rglob('*.pbism'))
for f in files:
    try:
        json.loads(f.read_text(encoding='utf-8'))
    except Exception as e:
        errors.append(f'JSON {f}: {e}')

bim = json.loads((root / f'{name}.SemanticModel/model.bim').read_text(encoding='utf-8'))['model']
cols = {t['name']: {c['name'] for c in t['columns']} for t in bim['tables']}
meas = {m['name'] for t in bim['tables'] for m in t.get('measures', [])}
ent_props = {t['name']: {c['name'] for c in t['columns']} | {m['name'] for m in t.get('measures', [])} for t in bim['tables']}

def check_dax(where, expr):
    body = re.sub(r'"[^"]*"', '""', expr)
    if body.count('(') != body.count(')'): errors.append(f'{where}: unbalanced parentheses')
    for t, c in re.findall(r"'?([A-Za-z_][\w ]*?)'?\[([^\]]+)\]", body):
        t = t.strip()
        if t and t in cols and c not in cols[t]: errors.append(f'{where}: {t}[{c}] not found')
        if t and t not in cols: errors.append(f'{where}: table {t} not found')
    for m in re.findall(r'(?<![\w\]\'])\[([^\]]+)\]', body):
        if m not in meas: errors.append(f'{where}: measure [{m}] not found')

for t in bim['tables']:
    for m in t.get('measures', []):
        check_dax(f"measure {m['name']}", m['expression'] if isinstance(m['expression'], str) else '\n'.join(m['expression']))
    for c in t['columns']:
        if c.get('type') == 'calculated': check_dax(f"column {t['name']}[{c['name']}]", c['expression'])
        if c.get('sortByColumn') and c['sortByColumn'] not in cols[t['name']]: errors.append(f"sortBy {t['name']}[{c['name']}]")
for r in bim['relationships']:
    for side in ('from', 'to'):
        if r[f'{side}Column'] not in cols.get(r[f'{side}Table'], ()): errors.append(f'relationship {r}')

data = root / 'data'
for t in bim['tables']:
    m = '\n'.join(t['partitions'][0]['source']['expression'])
    f = re.search(r'File.Contents\(Folder & "([^"]+)"\)', m)
    if f:
        with open(data / f.group(1), encoding='utf-8') as fh:
            header = next(csv.reader(fh))
        src = [c['sourceColumn'] for c in t['columns'] if c.get('type') != 'calculated']
        if header != src: errors.append(f"{t['name']}: CSV header {header} != columns {src}")

pages = {p.parent.name for p in (root / f'{name}.Report/definition/pages').glob('*/page.json')}
nvis = 0
for vf in (root / f'{name}.Report/definition/pages').glob('*/visuals/*/visual.json'):
    nvis += 1
    s = vf.read_text(encoding='utf-8')
    refs = []
    def walk(o, alias):
        if isinstance(o, dict):
            if isinstance(o.get('From'), list):
                alias = {**alias, **{f['Name']: f['Entity'] for f in o['From'] if 'Name' in f}}
            if 'Property' in o and isinstance(o.get('Expression'), dict) and 'SourceRef' in o['Expression']:
                sr = o['Expression']['SourceRef']
                refs.append((sr.get('Entity') or alias.get(sr.get('Source'), '?'), o['Property']))
            for v in o.values(): walk(v, alias)
        elif isinstance(o, list):
            for v in o: walk(v, alias)
    walk(json.loads(s), {})
    nref = globals().get('nref', 0) + len(refs); globals()['nref'] = nref
    for ent, prop in refs:
        if prop not in ent_props.get(ent, ()): errors.append(f'{vf.parent.name}: {ent}.{prop} not in model')
    for target in re.findall(r'"navigationSection": \{\s*"expr": \{\s*"Literal": \{\s*"Value": "\'([^\']+)\'"', s):
        if target not in pages: errors.append(f'{vf.parent.name}: navigates to missing page {target}')

print(f'{globals().get("nref", 0)} field references checked, {len(files)} JSON files, {len(bim["tables"])} tables, {len(meas)} measures, {len(pages)} pages, {nvis} visuals')
print('ERRORS:' if errors else 'All checks passed', *errors[:40], sep='\n  ')
sys.exit(1 if errors else 0)
