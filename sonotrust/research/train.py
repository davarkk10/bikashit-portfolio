"""Train U-Net on patient-separated BUS-BRA; save validation-best model."""
import argparse
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader
from src.data import load_metadata, make_patient_splits, UltrasoundDataset
from src.model import UNet, loss_fn, batch_scores


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', default='data/BUSBRA')
    ap.add_argument('--out', default='results/baseline')
    ap.add_argument('--epochs', type=int, default=20)
    ap.add_argument('--batch-size', type=int, default=8)
    ap.add_argument('--side', type=int, default=256)
    ap.add_argument('--base', type=int, default=16)
    ap.add_argument('--method', choices=['raw','clahe'], default='raw')
    ap.add_argument('--seed', type=int, default=42)
    args = ap.parse_args()
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    if args.epochs < 1 or args.batch_size < 1 or args.side < 16 or args.base < 1:
        raise ValueError('epochs, batch size and base must be positive; side must be at least 16')
    metadata = load_metadata(args.data)
    import platform
    (out/'run_config.json').write_text(json.dumps({**vars(args),
        'python':platform.python_version(), 'torch':str(torch.__version__),
        'numpy':np.__version__, 'device':'cuda' if torch.cuda.is_available() else 'cpu',
        'dataset_kind':'synthetic software check' if 'synthetic' in str(Path(args.data)) else 'real-data candidate; verify provenance',
        'grouping':'inferred filename case identifier; independent verification required'}, indent=2))
    splits = make_patient_splits(metadata, args.seed)
    manifest = {name: frame['ID'].tolist() for name, frame in splits.items()}
    (out/'splits.json').write_text(json.dumps(manifest, indent=2))
    for name, df in splits.items():
        print(f'{name}: {len(df)} images / {df.patient_id.nunique()} patients; malignant={df.label.mean():.1%}')
    loaders = {name: DataLoader(UltrasoundDataset(frame, side=args.side, method=args.method,
                                                  augment=(name=='train')),
                                batch_size=args.batch_size, shuffle=(name=='train'), num_workers=0)
               for name, frame in splits.items() if name!='test'}
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print('Device:', device)
    net = UNet(args.base).to(device)
    optim = torch.optim.AdamW(net.parameters(), lr=1e-3)
    history = []
    best = -1.0
    for epoch in range(1, args.epochs + 1):
        net.train()
        tr_losses=[]
        for x,y in loaders['train']:
            x,y=x.to(device),y.to(device)
            optim.zero_grad(set_to_none=True)
            loss=loss_fn(net(x),y)
            loss.backward()
            optim.step()
            tr_losses.append(float(loss.item()))
        net.eval()
        val_dice=[]; val_iou=[]
        with torch.no_grad():
            for x,y in loaders['val']:
                dice,iou=batch_scores(net(x.to(device)),y.to(device))
                val_dice.extend(dice.tolist()); val_iou.extend(iou.tolist())
        score = float(np.mean(val_dice))
        print(f'Epoch {epoch:02d}/{args.epochs} train loss={np.mean(tr_losses):.4f} val Dice={score:.4f} val IoU={np.mean(val_iou):.4f}')
        history.append({'epoch':epoch,'train_loss':np.mean(tr_losses),'val_dice':score,'val_iou':np.mean(val_iou)})
        if score > best:
            best = score
            torch.save({'state_dict':net.state_dict(), 'side':args.side,'base':args.base,
                        'method':args.method,'seed':args.seed,'best_val_dice':best},out/'best_model.pt')
    pd.DataFrame(history).to_csv(out/'training_history.csv',index=False)
    print('Saved validation-best weights to:',out/'best_model.pt')
    print('Next: python evaluate.py --data',args.data,'--out',args.out)


if __name__=='__main__': main()
