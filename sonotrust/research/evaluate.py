"""Held-out evaluation; patient-bootstrap CI; robustness under blur/noise."""
import argparse
from pathlib import Path
import json
import numpy as np
import pandas as pd
import cv2
import torch
from PIL import Image
from src.data import load_metadata, prepare_image
from src.model import UNet


def metrics(pred, truth):
    p=(pred>=0.5).astype(bool)
    t=(truth>0).astype(bool)
    inter=np.logical_and(p,t).sum()
    dice=(2*inter+1e-6)/(p.sum()+t.sum()+1e-6)
    iou=(inter+1e-6)/(np.logical_or(p,t).sum()+1e-6)
    return float(dice), float(iou)


def patient_bootstrap_ci(table, col='dice', n=2000, seed=42):
    """Resample patients, not correlated images. Return percentile 95% CI."""
    per_patient=table.groupby('patient_id')[col].mean().to_numpy()
    rng=np.random.default_rng(seed)
    vals=[rng.choice(per_patient,size=len(per_patient),replace=True).mean() for _ in range(n)]
    return [float(np.percentile(vals,2.5)),float(np.percentile(vals,97.5))]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--data',default='data/BUSBRA')
    ap.add_argument('--out',default='results/baseline')
    args=ap.parse_args()
    out=Path(args.out)
    ckpt=torch.load(out/'best_model.pt',map_location='cpu',weights_only=True)
    dev=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    net=UNet(ckpt['base']).to(dev);net.load_state_dict(ckpt['state_dict']);net.eval()
    ids=set(json.loads((out/'splits.json').read_text())['test'])
    table=load_metadata(args.data)
    table=table[table['ID'].isin(ids)].reset_index(drop=True)
    assert len(table)==len(ids), 'Some held-out IDs could not be matched'
    rng=np.random.default_rng(42)
    rows=[]
    for _,rec in table.iterrows():
        gray=prepare_image(Image.open(rec['image_path']), ckpt['side'],ckpt['method'])
        target=np.asarray(Image.open(rec['mask_path']).convert('L').resize(
            (ckpt['side'],ckpt['side']),Image.Resampling.NEAREST))>0
        for condition in ['clean','blur','noise']:
            im=gray.copy()
            if condition=='blur':im=cv2.GaussianBlur(im,(7,7),2)
            if condition=='noise':
                im=np.clip(im.astype(float)+rng.normal(0,20,im.shape),0,255).astype(np.uint8)
            x=torch.from_numpy(im.copy()).float().to(dev)[None,None]/255.0
            with torch.no_grad():prob=torch.sigmoid(net(x))[0,0].cpu().numpy()
            d,i=metrics(prob,target)
            rows.append({'ID':rec['ID'],'patient_id':rec['patient_id'],'condition':condition,'dice':d,'iou':i})
    results=pd.DataFrame(rows)
    results.to_csv(out/'heldout_predictions.csv',index=False)
    report={}
    for condition,g in results.groupby('condition'):
        report[condition]={'image_mean_dice':float(g['dice'].mean()),
                           'image_mean_iou':float(g['iou'].mean()),
                           'patient_mean_dice':float(g.groupby('patient_id')['dice'].mean().mean()),
                           'patient_bootstrap_95ci_dice':patient_bootstrap_ci(g)}
    (out/'evaluation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    print('Test results saved:',out/'heldout_predictions.csv')


if __name__=='__main__':main()
