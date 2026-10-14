# First build — 14 October 2026

Implemented: strict metadata labels; image/mask geometry and binary-mask audit;
exact-duplicate cross-split check; fixed grouped 60/20/20 split documentation;
raw/CLAHE training examples; verified-checksum dataset download; guided Colab
notebook; training environment/config logging; plain-language starting guide.

Verified locally: six automated tests; synthetic audit of 120 images from 60
inferred groups; 12-epoch synthetic training; checkpoint loading; held-out
synthetic Dice/IoU and bootstrap evaluation with blur/noise conditions. The
model learned artificial shapes. These scores are software checks only, not
medical-image performance. The notebook code cells compile; the complete Colab
workflow has not been executed inside Colab. The optional Streamlit app has
not been launched during this build.

Official BUS-BRA archive downloaded and its published MD5 verified. Audit
passed: 1,875 images, 1,064 inferred case groups; 1,268 benign and 607 malignant
images; no empty/full masks, dimension mismatches or exact duplicate images.
Train/validation/test counts are 1,125 / 375 / 375 images, and
639 / 213 / 212 inferred case groups. The match to the published patient count
supports, but does not independently prove, filename-based patient grouping.

Pending:
controlled raw/CLAHE comparison; uncertainty and external
validation. Do not describe this package as clinically validated.

## First real-data baseline completed

Raw-image U-Net trained for 10 epochs on CPU at 128×128, base width 8, batch
size 8, seed 42. Best validation mean image Dice: 0.825039; corresponding
validation mean image IoU: 0.732065 (epoch 10). The saved checkpoint reloads and
produces the expected 128×128 pixel map. This is preliminary validation
performance, not test performance or a probability of a correct diagnosis.
The real test set has now been scored; see TEST_RESULTS.md. Filename groups
were verified one-to-one against publisher Case metadata on all records.

Included: `results/raw_first/best_model.pt`, training history, learning curves,
splits and experiment configuration; real-data audit tables and summary;
synthetic-only software-check logs. Original dataset images, masks and the
real-image preview panel are excluded from the distributable package.

## Held-out evaluation completed

375 images from 212 publisher cases. Clean case-mean Dice 0.814130; 95%
case-bootstrap interval 0.793540–0.833795. Image-mean Dice 0.813773;
image-mean IoU 0.715026. Case Dice under blur 0.688044 and noise 0.694432.
23 clean test images have Dice below 0.5. Scored weights remained frozen.

Current checks: seven automated tests passed after adding publisher Case
validation. The frozen split IDs remain identical to the trained experiment.
