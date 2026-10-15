import json, re, sys, glob
from pathlib import Path
root = Path(sys.argv[1]); D = root / 'ProcureAI_FMCG.SemanticModel/definition'
ent = {}; meas = set(); errs = []
for f in (D / 'tables').glob('*.tmdl'):
    s = f.read_text(encoding='utf-8')
    tn = re.match(r"table ('([^']+)'|(\S+))", s); tn = tn.group(2) or tn.group(3)
    names = set()
    for m in re.finditer(r"^\t(column|measure) ('([^']+)'|([^\s=]+))", s, re.M):
        n = m.group(3) or m.group(4); names.add(n)
        if m.group(1) == 'measure': meas.add(n)
    ent[tn] = names
# DAX refs in new tables
for f in (D / 'tables').glob('*.tmdl'):
    s = f.read_text(encoding='utf-8')
    for line in re.findall(r"^\t(?:measure|column) .*? = (.*)$", s, re.M):
        body = re.sub(r'"[^"]*"', '""', line)
        if body.count('(') != body.count(')'): errs.append(f'{f.name}: parens: {line[:60]}')
        for t, c in re.findall(r"'([^']+)'\[([^\]]+)\]", body):
            if c not in ent.get(t, ()): errs.append(f'{f.name}: {t}[{c}]')
        for m in re.findall(r"(?<![\]'\w])\[([^\]]+)\]", body):
            if m not in meas: errs.append(f'{f.name}: [{m}]')
rel = (D / 'relationships.tmdl').read_text(encoding='utf-8')
for side in re.findall(r"(?:from|to)Column: ('([^']+)'|(\w+))\.(\w+)", rel):
    t = side[1] or side[2]
    if side[3] not in ent.get(t, ()): errs.append(f'rel {t}.{side[3]}')
pages = json.loads((root / 'ProcureAI_FMCG.Report/definition/pages/pages.json').read_text())['pageOrder']
nref = 0
for vf in glob.glob(str(root / 'ProcureAI_FMCG.Report/definition/pages/*/visuals/*/visual.json')):
    v = json.loads(open(vf, encoding='utf-8').read())
    def walk(o, alias):
        global nref
        if isinstance(o, dict):
            if isinstance(o.get('From'), list): alias = {**alias, **{x['Name']: x['Entity'] for x in o['From']}}
            if 'Property' in o and isinstance(o.get('Expression'), dict) and 'SourceRef' in o['Expression']:
                sr = o['Expression']['SourceRef']; e = sr.get('Entity') or alias.get(sr.get('Source'))
                nref += 1
                if o['Property'] not in ent.get(e, ()): errs.append(f'{vf.split("/pages/")[1]}: {e}.{o["Property"]}')
            for x in o.values(): walk(x, alias)
        elif isinstance(o, list):
            for x in o: walk(x, alias)
    walk(v, {})
    link = v['visual'].get('visualContainerObjects', {}).get('visualLink')
    if link and link[0]['properties'].get('navigationSection'):
        t = link[0]['properties']['navigationSection']['expr']['Literal']['Value'].strip("'")
        if t not in pages: errs.append(f'nav to missing {t}')
for p in pages:
    pj = json.loads((root / f'ProcureAI_FMCG.Report/definition/pages/{p}/page.json').read_text(encoding='utf-8'))
    bg = pj['objects']['background'][0]['properties']['image']['image']['name']['expr']['Literal']['Value'].strip("'")
    if not (root / 'ProcureAI_FMCG.Report/StaticResources/RegisteredResources' / bg).exists(): errs.append(f'missing bg {bg}')
print(f'{len(ent)} tables, {len(meas)} measures, {len(pages)} pages, {nref} field refs')
print('ERRORS' if errs else 'All checks passed', *sorted(set(errs))[:30], sep='\n ')
