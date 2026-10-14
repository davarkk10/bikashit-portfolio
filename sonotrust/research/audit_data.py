"""Stage 1: inspect paired images and masks without training or scoring models."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from src.data import load_metadata, make_patient_splits, prepare_image


def audit(data, out, seed=42):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    frame = load_metadata(data)
    splits = make_patient_splits(frame, seed)
    membership = {row.ID: name for name, part in splits.items() for row in part.itertuples()}
    records, seen, duplicates = [], {}, []
    for row in frame.itertuples():
        with Image.open(row.image_path) as im, Image.open(row.mask_path) as mask:
            if im.size != mask.size:
                raise ValueError(f'{row.ID}: image/mask dimensions differ: {im.size} / {mask.size}')
            gray = np.asarray(im.convert('L'))
            target = np.asarray(mask.convert('L'))
            if not set(np.unique(target)).issubset({0, 1, 255}):
                raise ValueError(f'{row.ID}: mask is not binary; inspect its annotation convention')
            area = float((target > 0).mean())
            if area == 0 or area == 1:
                raise ValueError(f'{row.ID}: empty or full mask needs review')
            digest = hashlib.sha256(str(gray.shape).encode() + gray.tobytes()).hexdigest()
            if digest in seen:
                previous = seen[digest]
                duplicates.append({'first': previous, 'second': row.ID,
                                   'cross_split': membership[previous] != membership[row.ID]})
            else:
                seen[digest] = row.ID
            records.append({'ID': row.ID, 'patient_id': row.patient_id,
                            'pathology': row.Pathology, 'split': membership[row.ID],
                            'width': im.width, 'height': im.height,
                            'lesion_area_fraction': area,
                            'mean_intensity': float(gray.mean()), 'pixel_sha256': digest})
    import pandas as pd
    pd.DataFrame(records).to_csv(out / 'image_audit.csv', index=False)
    summary = {
        'images': len(frame), 'inferred_case_groups': int(frame.patient_id.nunique()),
        'grouping_status': frame.attrs.get('grouping_source', 'Inferred case identifiers'),
        'pathology_images': frame.Pathology.value_counts().to_dict(),
        'seed': seed, 'split_protocol': '5-fold outer test, 4-fold inner validation; approximately 60/20/20',
        'splits': {name: {'images': len(part), 'inferred_case_groups': int(part.patient_id.nunique()),
                         'pathology_images': part.Pathology.value_counts().to_dict()}
                   for name, part in splits.items()},
        'exact_pixel_duplicates': duplicates,
        'cross_split_exact_duplicate_count': sum(d['cross_split'] for d in duplicates),
        'near_duplicate_check': 'not implemented; exact hashes do not exclude near duplicates',
        'source_metadata_sha256': hashlib.sha256(frame[['ID','Pathology']].to_csv(index=False).encode()).hexdigest(),
    }
    (out / 'audit_summary.json').write_text(json.dumps(summary, indent=2))
    (out / 'splits.json').write_text(json.dumps({k: v.ID.tolist() for k, v in splits.items()}, indent=2))
    # Show training examples only; reserve held-out data for final evaluation.
    examples = splits['train'].sample(n=min(4, len(splits['train'])), random_state=seed)
    fig, axes = plt.subplots(len(examples), 3, figsize=(10, 3 * len(examples)), squeeze=False)
    for i, row in enumerate(examples.itertuples()):
        with Image.open(row.image_path) as im, Image.open(row.mask_path) as mask:
            raw = prepare_image(im, 256, 'raw')
            enhanced = prepare_image(im, 256, 'clahe')
            truth = np.asarray(mask.convert('L').resize((256,256), Image.Resampling.NEAREST)) > 0
        axes[i,0].imshow(raw, cmap='gray', vmin=0, vmax=255)
        axes[i,1].imshow(enhanced, cmap='gray', vmin=0, vmax=255)
        axes[i,2].imshow(raw, cmap='gray', vmin=0, vmax=255)
        axes[i,2].contour(truth, levels=[0.5], colors=['#00d5a4'], linewidths=1.5)
        for ax, title in zip(axes[i], ['Raw', 'CLAHE', 'Reference outline']):
            ax.set_title(f'{row.ID} | {title}', fontsize=10)
            ax.axis('off')
    fig.suptitle('Training examples only — synthetic if run on data/synthetic', fontsize=13)
    fig.tight_layout(rect=(0,0,1,0.96))
    fig.savefig(out / 'training_examples.png', dpi=130)
    plt.close(fig)
    print(json.dumps(summary, indent=2))
    if summary['cross_split_exact_duplicate_count']:
        raise ValueError('Exact duplicate images cross splits. Resolve leakage before training.')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default='data/BUSBRA')
    parser.add_argument('--out', default='results/audit')
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    audit(args.data, args.out, args.seed)
