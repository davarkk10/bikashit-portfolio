# SonoTrust: your first medical imaging build

## What you are building

Give the computer a breast ultrasound image. It draws an outline around a
lesion. This task is **segmentation**: deciding which pixels belong inside the
region. It does not diagnose cancer. Benign/malignant labels are currently used
to balance data splits, not as model predictions.

Your research question is: **Does enhancing image contrast help the model draw
more accurate outlines, and does it still work when images become degraded?**

Your physics background is useful here: ultrasound forms images using sound,
and image quality depends on reflection, attenuation and interference.

## First session: use Google Colab

1. Unzip the project package on your computer or phone.
2. Open https://colab.research.google.com/ and upload `SonoTrust_First_Run.ipynb`.
3. Choose **Runtime → Change runtime type → T4 GPU**, if available.
4. Run the first notebook cell and upload the original project ZIP when asked.
5. Run the setup and artificial-data check cells in order.
6. Run the official-data download and audit cells.
7. Inspect the training-image panel before starting real training.

The notebook saves a results ZIP for download. Colab storage is temporary, so
download your results before closing the session. The results ZIP excludes the
source dataset and image preview panel; handle source images under their terms.

## Understand the image panel

| Panel | Meaning |
|---|---|
| Raw | Original grayscale image, resized for the model |
| CLAHE | Contrast enhanced locally; this may reveal detail or amplify noise |
| Reference outline | Dataset annotation the model tries to learn |

A **mask** is a black-and-white map: white pixels mark the lesion and black
pixels mark the background. A **U-Net** learns image features, then builds a
pixel map while reusing fine detail through skip connections.

## Why we split by case

Training data teach the model. Validation data help choose the best checkpoint.
Test data are reserved for the final experiment. If related views appear in
both training and testing, results may look better than they really are.
The code groups `bus_0001-l` and `bus_0001-r` under `bus_0001`. This is an
inferred case identifier: confirm the patient convention before describing
your results as patient-disjoint. Current proportions are approximately
60% training, 20% validation and 20% test.

## How success is measured

**Dice** measures overlap between a predicted mask and the reference mask.
One means perfect overlap; zero means no overlap. A Dice of 0.8 does not mean
an 80% probability of a correct diagnosis. **IoU** is intersection divided by
union. Confidence intervals summarize sampling variability across case groups.

## What is ready and what comes next

Ready: data audit, training-image preview, compact U-Net, raw/CLAHE modes,
training and evaluation scripts, guided notebook and synthetic software checks.

The official archive has passed the first audit: 1,875 image-mask pairs, 1,064
inferred case groups, and no exact pixel duplicates.

Next: independently review the verified case grouping and raw baseline,
inspect validation behavior, freeze the comparison protocol, train CLAHE with
the same settings, then evaluate both on held-out data. The first held-out baseline has now been scored: see `TEST_RESULTS.md`.
This is internal research performance, not clinical validation. Do not tune models using test scores.

Primary sources: https://zenodo.org/records/8231412 and
https://github.com/wgomezf/BUS-BRA. Cite Gómez-Flores et al., Medical Physics
(2024), DOI 10.1002/mp.16812 in any research using the dataset.
