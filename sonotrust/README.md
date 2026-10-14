# SonoTrust — Project 5

Interactive case study: https://davarkk10.github.io/bikashit-portfolio/sonotrust/

A compact PyTorch U-Net for breast ultrasound lesion segmentation. This is an
educational, nonclinical research prototype. It predicts masks, not diagnoses.

## Executed baseline

375 held-out images from 212 publisher cases. Clean case-mean Dice 0.8141
(95% case-bootstrap CI 0.7935–0.8338). Blur: 0.6880; noise: 0.6944.
23 clean test images have Dice below 0.5. The validation-best weights were
frozen before test scoring. One internal split and training seed; no external
validation. Predictions shown on the page are archived, not live inference.

See `research/TEST_RESULTS.md` and `research/EXPERIMENT_PROTOCOL.md`. The
research package with checkpoint and notebook is under `assets/`.

## Data attribution

BUS-BRA: Gómez-Flores, Gregorio-Calas and Pereira, Medical Physics 51:3110–3123
(2024), DOI https://doi.org/10.1002/mp.16812. Official data:
https://zenodo.org/records/8231412. Selected anonymized examples reproduced
under the permission notice in `assets/BUS-BRA-LICENSE.txt`.
The full dataset is not committed. Implementation developed with AI coding assistance.
