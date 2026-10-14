from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from PIL import Image
from audit_data import audit
from src.data import load_metadata


def dataset(tmp_path):
    root = tmp_path / 'BUSBRA'
    (root / 'Images').mkdir(parents=True)
    (root / 'Masks').mkdir()
    rows = []
    for n in range(1, 41):
        identifier = f'bus_{n:04d}-s'
        gray = np.full((16,16), n, dtype=np.uint8)
        mask = np.zeros((16,16), dtype=np.uint8)
        mask[4:12,4:12] = 255
        Image.fromarray(gray).save(root / 'Images' / f'{identifier}.png')
        Image.fromarray(mask).save(root / 'Masks' / f'mask_{n:04d}-s.png')
        rows.append({'ID':identifier, 'Pathology':'benign' if n%2 else 'malignant'})
    pd.DataFrame(rows).to_csv(root / '5-fold-cv.csv', index=False)
    return root


def test_audit_and_empty_mask(tmp_path):
    root = dataset(tmp_path)
    result = audit(root, tmp_path / 'audit')
    assert result['images'] == 40
    assert result['cross_split_exact_duplicate_count'] == 0
    Image.fromarray(np.zeros((16,16),dtype=np.uint8)).save(root/'Masks/mask_0001-s.png')
    with pytest.raises(ValueError, match='empty or full'):
        audit(root, tmp_path / 'bad')


def test_unknown_label_is_rejected(tmp_path):
    root = dataset(tmp_path)
    table = pd.read_csv(root / '5-fold-cv.csv')
    table.loc[0,'Pathology'] = 'unknown'
    table.to_csv(root / '5-fold-cv.csv',index=False)
    with pytest.raises(ValueError, match='Unknown pathology'):
        load_metadata(root)


def test_exact_duplicate_crossing_splits_is_rejected(tmp_path):
    from src.data import make_patient_splits
    root = dataset(tmp_path)
    splits = make_patient_splits(load_metadata(root))
    first = splits['train'].iloc[0]
    second = splits['test'].iloc[0]
    Path(second.image_path).write_bytes(Path(first.image_path).read_bytes())
    with pytest.raises(ValueError, match='Resolve leakage'):
        audit(root, tmp_path / 'leakage')


def test_publisher_case_validation(tmp_path):
    root = dataset(tmp_path)
    table = pd.read_csv(root / '5-fold-cv.csv')
    table['Case'] = range(1, 41)
    table[['ID','Case']].to_csv(root/'bus_data.csv',index=False)
    frame = load_metadata(root)
    assert 'Validated' in frame.attrs['grouping_source']
    table.loc[0,'Case'] = 2
    table[['ID','Case']].to_csv(root/'bus_data.csv',index=False)
    with pytest.raises(ValueError, match='do not match'):
        load_metadata(root)
