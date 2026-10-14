# SonoTrust AI — Trustworthy Breast Ultrasound Segmentation

**A practical, educational starter project for a prospective European Master in Medical Image Analysis (MAIA) applicant.**

## Start here — guided first build

Open `SonoTrust_First_Run.ipynb` in Google Colab and follow it from the top.
Read `START_HERE.md` for a plain-language guide. The notebook first tests on
artificial shapes, then downloads the official dataset, audits it, and trains
a first raw-image model. The official dataset has passed the audit; the first raw model has been trained
and evaluated. See `TEST_RESULTS.md` for held-out results and limitations.

Stage 1 audit produces `image_audit.csv`, `audit_summary.json`, `splits.json`
and `training_examples.png`. It rejects invalid labels, non-binary/empty masks,
mismatched image-mask dimensions and exact duplicates crossing splits. It does
not detect all near duplicates or independently prove the patient-ID convention.

```
python download_data.py
python audit_data.py --data data/BUSBRA --out results/audit
```

## Research goal

Can a compact deep-learning model segment a breast lesion in ultrasound images, and does classical image enhancement improve its performance and robustness?

> This repo is **not clinically validated**. It must never be used for patient diagnosis, triage, screening or treatment.

### What is actually implemented here?

- A small, fully trainable **PyTorch U-Net** model for lesion segmentation.
- Two controlled pre-processing options: grayscale raw image and CLAHE enhancement.
- **Patient-grouped train/validation/test splits**, with programmatic disjointness checks.
- Seeded training, logged run configuration, and validation-best checkpointing.
- Test-set **Dice**, **intersection over union (IoU)**, **patient-level bootstrap confidence intervals**, and robustness experiments (blur and image noise).
- An optional Streamlit segmentation visualization demo.
- A synthetic-image software-check dataset and basic tests.

**Not yet implemented:** pathology classification, Grad-CAM, robust uncertainty estimation, multiple random seeds, external validation, statistical significance testing. These are research milestones in `RESEARCH_PLAN.md` — do not claim them as completed.

## Real dataset (download separately)

Dataset: BUS-BRA, Gómez-Flores et al., *Medical Physics* 51:3110–3123 (2024), DOI 10.1002/mp.16812.

Official download: https://zenodo.org/records/8231412

Extract `BUSBRA.zip` so these exist:

```
data/BUSBRA/5-fold-cv.csv
data/BUSBRA/Images/bus_0001-l.png    <-- illustration; actual files in original ZIP
data/BUSBRA/Masks/mask_0001-l.png
```

Refer to the actual downloaded names. The loader uses `data/BUSBRA` or `data` when it contains the nested `BUSBRA` directory.

BUS-BRA contains approximately 1,875 images from 1,064 patients, original lesion masks and per-image labels. Observe the dataset's permissions, attribution and original terms. **Do not commit patient images or dataset files to GitHub.**

### Setup

You need Python 3.10+ (prefer 3.11), working PyTorch, and optionally an NVIDIA GPU or a Google Colab GPU.

```
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

If PyTorch GPU is not detected, consult the installation selector at https://pytorch.org/get-started/locally/ .

### First verify the project using artificial images

```
python make_synthetic_data.py
pytest -q
python train.py --data data/synthetic/BUSBRA --out results/smoke --side 64 --base 4 --batch-size 8 --epochs 2
python evaluate.py --data data/synthetic/BUSBRA --out results/smoke
```

These shapes are **fake**. The results only verify that the program runs; they are **not medical image research results**.

### Train on real medical images

```
python train.py --data data/BUSBRA --out results/raw --method raw --epochs 25
python train.py --data data/BUSBRA --out results/clahe --method clahe --epochs 25
```

Both runs share the same seed and patient splits. Then evaluate *only once per frozen final model*:

```
python evaluate.py --data data/BUSBRA --out results/raw
python evaluate.py --data data/BUSBRA --out results/clahe
```

Inspect `training_history.csv`, `heldout_predictions.csv` and `evaluation.json` in each result directory. Do not select new hyperparameters after viewing test results; use the validation set for selection.

### Open the research demo

```
streamlit run app.py
```

Paste `results/raw/best_model.pt` as the checkpoint path.

## Research integrity

- Grouped splits use an inferred `bus_XXXX` identifier. **The groups were verified one-to-one against the publisher Case column in bus_data.csv.** If it does not, replace the grouping code with an explicitly verified patient identifier.
- Image masks are resized with **nearest neighbor interpolation**, while images use bilinear interpolation.
- Results vary with hardware, seeds and data condition. No results are claimed in advance.
- Confidence intervals summarize sampling variability, **not** clinical safety or predictive uncertainty.
- The current blur/noise are general perturbations rather than fully physics-faithful ultrasound simulation; investigate speckle-aware tests before writing a paper.
- Images are for educational and nonclinical use. No upload of real patient data to third-party tools.

## Suggested GitHub exhibits

Include a short research summary, original dataset citation, methodology diagram, honest results with confidence intervals, validation curves, failure cases, robustness plot and 2-minute demo video. Never add data you lack redistribution rights to publish.

## Reading

- MAIA curriculum: https://maiamaster.udg.edu/courses/
- BUS-BRA official data: https://zenodo.org/records/8231412
- BUS-BRA original paper: https://doi.org/10.1002/mp.16812
- PyTorch tutorials: https://docs.pytorch.org/tutorials/
