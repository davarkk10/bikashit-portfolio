import pandas as pd
import torch
from src.data import patient_group, make_patient_splits
from src.model import UNet, loss_fn, batch_scores


def test_patient_grouping():
    assert patient_group('bus_0001-l') == patient_group('bus_0001-r')


def test_group_splits():
    rows=[]
    for i in range(60):
        for view in ('l','r'):
            rows.append({'ID':f'bus_{i:04d}-{view}','patient_id':f'bus_{i:04d}', 'label':int(i%2==0)})
    splits=make_patient_splits(pd.DataFrame(rows))
    for a,b in [('train','val'),('train','test'),('val','test')]:
        assert set(splits[a].patient_id).isdisjoint(set(splits[b].patient_id))


def test_model_and_loss():
    model=UNet(base=4)
    x=torch.rand(2,1,64,64)
    y=(torch.rand(2,1,64,64)>0.5).float()
    pred=model(x)
    assert pred.shape==y.shape
    assert torch.isfinite(loss_fn(pred,y))
    dice,iou=batch_scores(pred,y)
    assert all(0<=v<=1 for v in dice) and all(0<=v<=1 for v in iou)
