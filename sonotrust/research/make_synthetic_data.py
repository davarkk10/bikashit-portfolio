"""Create fake shapes solely for testing the training software, NEVER for research scores."""
from pathlib import Path
import numpy as np
import pandas as pd
import cv2

rng=np.random.default_rng(22)
root=Path('data/synthetic/BUSBRA');(root/'Images').mkdir(parents=True,exist_ok=True);(root/'Masks').mkdir(parents=True,exist_ok=True)
rows=[]
for patient in range(1,61):
    label='malignant' if patient%2 else 'benign'
    for view in ['l','r']:
        case=f'bus_{patient:04d}-{view}'
        x,y=np.meshgrid(np.arange(96),np.arange(96))
        cx,cy=rng.integers(36,60,size=2)
        rx,ry=rng.integers(12,24,size=2)
        mask=(((x-cx)/rx)**2+((y-cy)/ry)**2<=1).astype(np.uint8)*255
        image=(rng.normal(115,15,(96,96))-(mask>0)*rng.integers(28,53)).clip(0,255).astype(np.uint8)
        cv2.imwrite(str(root/'Images'/f'{case}.png'),image)
        cv2.imwrite(str(root/'Masks'/f'mask_{case.removeprefix("bus_")}.png'),mask)
        rows.append({'ID':case,'Pathology':label,'kFold':(patient%5)+1})
pd.DataFrame(rows).to_csv(root/'5-fold-cv.csv',index=False)
print('Synthetic-only software-check dataset created at',root)
