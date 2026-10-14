# SonoTrust Research Plan for MAIA 2027

## Main hypothesis

Ultrasound preprocessing can change lesion-segmentation accuracy and robustness, and the optimal choice should be evaluated at the **patient** level with reproducible holdouts, not selected on test data.

## Research stages

| Stage | Deliverable | Core concepts | Status |
|---|---|---|---|
| 1 | Inspect BUS-BRA metadata & examples | ultrasound physics, image quality, EDA | completed on official archive; publisher Case grouping verified |
| 2 | Train raw-image U-Net | convolution, loss, segmentation | 10-epoch raw baseline trained and held-out test scored |
| 3 | Compare CLAHE to raw images | histogram processing, controlled trials | starter code ready |
| 4 | Test blur/noise & failure cases | robustness, distribution shift | completed for blur/noise; failure examples exported |
| 5 | Train a pathology-label CNN | transfer learning, imbalance, AUROC/PR-AUC | to do |
| 6 | Add calibration and predictive uncertainty | reliability, ensemble, ECE, risk-coverage | to do |
| 7 | External segmentation test | acquisition-site shift, generalization | to do |
| 8 | Full scientific report + demo | figures, literature review, ethics | to do |

## Proposed classification track (Stage 5)

Use a torchvision ResNet18 pretrained on ImageNet as a **baseline**, and a small custom CNN as a control. Train image-level benign-vs-malignant pathology classification using the same patient-disjoint splits as segmentation. Use only labels supported by the downloaded dataset. Evaluate AUROC, sensitivity, specificity, balanced accuracy, F1 and calibration. A segmentation-guided cropped-lesion classifier can be compared to full-image classification — use only **predicted** masks at inference, not expert test masks.

## Proposed uncertainty track (Stage 6)

Evaluate a deep ensemble (e.g. 3–5 independent seeds), variation in predicted segmentation masks and classification probabilities. Define an abstention/referral analysis using a risk–coverage plot; calibrate thresholds with the validation set. Confidence is not a clinical probability unless rigorously validated. Grad-CAM can provide only a visual attribution, not a proof of medically correct reasoning.

## Better robust validation (Stage 7)

Use an independently sourced compatible breast ultrasound dataset for external lesion segmentation (e.g. BUS-UCLM if its terms and annotation convention permit) and explicitly report selection criteria and annotation differences. Do not treat external classification scores as comparable unless pathology reference standards are comparable.

## Experimental report template

1. Problem and motivation: why segmentation and trustworthy medical AI matter.
2. Imaging physics: what ultrasound speckle is and why contrast/noise differ from photographic images.
3. Dataset provenance/ethics: access, licenses, class distribution, scanner information.
4. Leakage audit: patient/case IDs, near-duplicates, split integrity.
5. Methods: preprocessing; U-Net architecture; Dice+BCE loss; augmentation.
6. Results: validation learning curves, fixed-test Dice/IoU with 95% CI, subgroup failure analysis.
7. Ablation: raw versus CLAHE and (optional) no augmentation.
8. Robustness: performance shift under severity-controlled perturbations.
9. Limitations: no clinical validation, site shift, uncertain annotation quality, limited cohort.
10. Reproducibility: seed, environment, hyperparameters, data split IDs (non-identifying), Git tag.

## Theory checklist to be able to defend in interview

**Physics:** acoustic impedance, reflection, attenuation, time-of-flight, speckle formation.
**Image processing:** bit-depth, histogram, CLAHE, filtering, interpolation, contours.
**DL:** convolution kernel, skip connection, batch normalization, overfitting, gradient descent, class imbalance.
**Statistics:** sampling unit, data leakage, confounding, bootstrapping, sensitivity/specificity, confidence interval, calibration.
**Ethics:** nonclinical use, data governance, bias, distribution shift, model limitations.

## Timeboxed learning roadmap (optional)

Week 1: learn physics and understand paired image/mask data.
Week 2: run synthetic checks, then first real U-Net baseline.
Week 3: inspect mistakes; compare raw and CLAHE methods.
Week 4: test robustness and present results and limitations.
Weeks 5–6: add classification, uncertainty, then document methods.
Weeks 7–8: external validation and polished portfolio/case study, conditional on progress.

**Rule:** an independently understood experiment is more valuable than an oversized model you cannot explain.
