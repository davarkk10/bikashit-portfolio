"""Export reproducible, scored held-out illustrations; never change the model."""
from pathlib import Path
import json
import cv2
import numpy as np
import pandas as pd
import torch
from PIL import Image
from src.data import load_metadata,prepare_image
from src.model import UNet
from evaluate import metrics

root=Path('results/raw_first')
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--out',default='web_assets')
args=parser.parse_args()
output=Path(args.out)
output.mkdir(parents=True,exist_ok=True)
results=pd.read_csv(root/'heldout_predictions.csv')
clean=results.query("condition == 'clean'").sort_values(['dice','ID']).reset_index(drop=True)
indices=[int(round((len(clean)-1)*q)) for q in [0.9,0.5,0.1,0]]
selection=clean.iloc[indices].copy()
labels=['Strong overlap · 90th percentile','Typical overlap · median','Difficult case · 10th percentile','Lowest overlap · minimum']
selected=dict(zip(selection.ID,labels))
ck=torch.load(root/'best_model.pt',map_location='cpu',weights_only=True)
net=UNet(ck['base']).eval();net.load_state_dict(ck['state_dict'])
ids=set(json.loads((root/'splits.json').read_text())['test'])
frame=load_metadata('data/BUSBRA');frame=frame[frame.ID.isin(ids)].reset_index(drop=True)
rng=np.random.default_rng(42); examples=[]
for row in frame.itertuples():
    with Image.open(row.image_path) as image:
        gray=prepare_image(image,ck['side'],ck['method'])
    with Image.open(row.mask_path) as mask:
        truth=np.asarray(mask.convert('L').resize((ck['side'],ck['side']),Image.Resampling.NEAREST))>0
    entry={'id':row.ID,'selection':selected.get(row.ID),'conditions':{}}
    for condition in ['clean','blur','noise']:
        im=gray.copy()
        if condition=='blur': im=cv2.GaussianBlur(im,(7,7),2)
        if condition=='noise':im=np.clip(im.astype(float)+rng.normal(0,20,im.shape),0,255).astype(np.uint8)
        if row.ID not in selected: continue
        with torch.no_grad():prob=torch.sigmoid(net(torch.from_numpy(im.copy()).float()[None,None]/255.0))[0,0].numpy()
        dice,iou=metrics(prob,truth)
        expected=results[(results.ID==row.ID)&(results.condition==condition)].iloc[0]
        assert np.isclose(dice,expected.dice) and np.isclose(iou,expected.iou)
        base=f'{row.ID}-{condition}'
        Image.fromarray(im).save(output/f'{base}.png')
        rgb=np.stack([im]*3,axis=-1)
        pred=(prob>=.5).astype(np.uint8)
        for binary,color in [(truth.astype(np.uint8),(64,225,185)),(pred,(255,192,77))]:
            contours,_=cv2.findContours(binary,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(rgb,contours,-1,color,1)
        Image.fromarray(rgb).save(output/f'{base}-overlay.png')
        entry['conditions'][condition]={'image':f'assets/{base}.png','overlay':f'assets/{base}-overlay.png','dice':dice,'iou':iou}
    if row.ID in selected:examples.append(entry)
examples.sort(key=lambda r:indices[list(selection.ID).index(r['id'])],reverse=True)
summary=json.loads((root/'evaluation.json').read_text())
bins=np.histogram(clean.dice.to_numpy(),bins=np.linspace(0,1,11))[0].tolist()
patient=results.groupby(['condition','patient_id']).dice.mean().unstack('condition')
subgroups=[]
for name in ['benign','malignant']:
    named=set(frame.loc[frame.Pathology==name,'ID'])
    part=results[(results.ID.isin(named))&(results.condition=='clean')]
    subgroups.append({'name':name,'images':len(part),'image_mean_dice':part.dice.mean()})
payload={'summary':summary,'examples':examples,'histogram':bins,'subgroups':subgroups,'training':pd.read_csv(root/'training_history.csv').to_dict('records'),'test_images':len(clean),'test_cases':clean.patient_id.nunique(),'fraction_below_05':float((clean.dice<.5).mean()),'n_below_05':int((clean.dice<.5).sum()),'paired_case_delta':{condition:float((patient[condition]-patient['clean']).mean()) for condition in ['blur','noise']},'selection_protocol':'Four archived test examples selected by clean Dice at approximately the 90th, 50th, 10th and 0th percentiles. Same images and perturbation realizations as the scored evaluation.'}
(output/'results.json').write_text(json.dumps(payload,indent=2))
print(json.dumps({k:v for k,v in payload.items() if k not in ['training','examples','histogram']},indent=2))
