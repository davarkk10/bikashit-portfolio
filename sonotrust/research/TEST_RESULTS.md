# SonoTrust — held-out baseline results

Evaluated 14 October 2026: 375 images from 212 publisher Case groups.
The model weights were selected using validation Dice before test scoring.
10 epochs, raw grayscale input, 128×128, base width 8, seed 42, threshold 0.5.

| Condition | Case-mean Dice | 95% case-bootstrap CI | Image-mean Dice | Image-mean IoU |
|---|---:|---|---:|---:|
| Clean | 0.8141 | 0.7935–0.8338 | 0.8138 | 0.7150 |
| Gaussian blur | 0.6880 | 0.6559–0.7191 | 0.6946 | 0.5825 |
| Gaussian noise | 0.6944 | 0.6644–0.7219 | 0.6932 | 0.5753 |

Dice measures overlap with reference masks, not clinical diagnostic accuracy.
Case means give equal weight to each case rather than each image. Intervals
use 2,000 case-bootstrap resamples with seed 42. The JSON/CSV retain historical
patient_id key names; their grouping unit is the validated publisher Case ID.

Publisher Case metadata matches inferred filename groups one-to-one for all
1,875 images. Splits are case-disjoint (639 / 213 / 212 cases). These case
counts match the dataset’s published patient count; no patient identities are
used. Exact pixel duplicate audit passed; near duplicates remain unaudited.

23 of 375 clean test images have Dice below 0.5. Descriptive clean image means
are 0.8326 for 254 benign-labelled images and 0.7742 for 121 malignant-labelled
images. These are not classification metrics, and no subgroup inference or
fairness claim follows from them.

Blur uses a 7×7 Gaussian kernel with sigma 2. Noise adds Gaussian values with
sigma 20 on a 0–255 scale and clips. Perturbations occur after square resizing;
they are not a validated ultrasound acquisition or speckle simulation.

The webpage shows four examples selected by clean Dice near the 90th, 50th,
10th and 0th percentiles. Their displayed perturbations and predictions were
verified against the exact scored CSV rows. Selection is illustrative, not
an independent sample. Dataset examples are reproduced under LICENSE.txt with
attribution to Gómez-Flores et al., Medical Physics (2024), DOI 10.1002/mp.16812.

Limits: one internal split, one training seed, no external validation or
predictive uncertainty, distorted aspect ratio from square resizing, imperfect
annotations, no clinical validation. Test scores must not guide subsequent
hyperparameter selection. A raw/CLAHE comparison remains uncompleted.
