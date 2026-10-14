# Initial experiment protocol

Dataset: official BUS-BRA archive, MD5 1f8b2be6476d58fc97bfb5e5a1ea9bab.
Task: binary lesion segmentation. Model: compact U-Net, base width 8, 128×128
input, batch size 8, 10 epochs, seed 42. Optimizer: AdamW, learning rate 0.001.
Loss: equal-weight BCE and soft Dice. Training augmentation: shared image/mask
horizontal flip; occasional image-only Gaussian blur. Checkpoint selection:
best mean image-level validation Dice. Prediction threshold: 0.5.

Grouped split: case prefix inferred from filename, seed 42; 1,125 training,
375 validation and 375 test images. The inferred filename groups have now been validated one-to-one against the
publisher bus_data.csv Case column. Exact pixel duplicate check passed; near duplicates are not
fully audited. Images resize bilinearly; masks use nearest neighbor. Both are
square-resized, which can distort original aspect ratio; document this limitation.

Initial raw baseline is a feasibility run. Planned controlled comparison:
train CLAHE with identical settings and splits, using local contrast limit 2.0,
8×8 tiles. The real test set was scored on 14 October 2026 at the user’s request. The raw baseline is now an observed test result. Do not use these test scores
to tune subsequent models.
Any changes informed by validation must be applied consistently to both arms
and documented. Do not tune after examining test performance.

Primary eventual endpoint: mean per-case Dice with a case-bootstrap 95% CI.
Secondary endpoints: image mean Dice, IoU, blur/noise robustness. Bootstrap
is sampling variability, not predictive uncertainty or clinical confidence.
Existing perturbations are general image noise/blur applied after preprocessing,
not a validated ultrasound acquisition simulation.
