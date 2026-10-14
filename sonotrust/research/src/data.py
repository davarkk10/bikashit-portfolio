"""Load BUS-BRA images, masks and metadata; split by patient, never by image."""
from pathlib import Path
import re
import random

import cv2
import numpy as np
import pandas as pd
from PIL import Image
from sklearn.model_selection import StratifiedGroupKFold
import torch
from torch.utils.data import Dataset


def patient_group(image_id: str) -> str:
    """BUS-BRA's bus_XXXX-l/r views share the bus_XXXX case identifier.

    Check this ID convention against the downloaded metadata before reporting
    patient-disjoint results. We deliberately reject unrecognized IDs.
    """
    match = re.match(r"^(bus_\d+)(?:[-_].*)?$", str(image_id), flags=re.I)
    if not match:
        raise ValueError(f"Unexpected BUS-BRA ID {image_id!r}; verify patient grouping.")
    return match.group(1).lower()


def load_metadata(data_dir):
    root = Path(data_dir)
    if not (root / "5-fold-cv.csv").exists() and (root / "BUSBRA" / "5-fold-cv.csv").exists():
        root = root / "BUSBRA"
    csv = root / "5-fold-cv.csv"
    if not csv.exists():
        raise FileNotFoundError(f"Expected {csv}. Extract the original BUSBRA.zip first.")
    df = pd.read_csv(csv)
    needed = {"ID", "Pathology"}
    if not needed.issubset(df.columns):
        raise ValueError(f"Missing columns {needed - set(df.columns)} in {csv}")
    df = df.copy()
    df["ID"] = df["ID"].astype(str).str.strip()
    df["Pathology"] = df["Pathology"].astype(str).str.lower().str.strip()
    if df.empty:
        raise ValueError("Metadata contains no image records.")
    unknown = sorted(set(df["Pathology"]) - {"benign", "malignant"})
    if unknown:
        raise ValueError(f"Unknown pathology labels {unknown}; audit rather than silently discard rows.")
    df["patient_id"] = df["ID"].map(patient_group)
    official_csv = root / "bus_data.csv"
    if official_csv.exists():
        official = pd.read_csv(official_csv, dtype={"Case": str})
        if not {"ID", "Case"}.issubset(official.columns) or official.ID.duplicated().any():
            raise ValueError("Publisher Case metadata must have unique ID and Case columns")
        official["ID"] = official["ID"].astype(str).str.strip()
        cases = official.set_index("ID")["Case"]
        df["publisher_case"] = df["ID"].map(cases)
        if df.publisher_case.isna().any():
            raise ValueError("Some image IDs have no publisher Case identifier")
        if df.groupby("patient_id").publisher_case.nunique().max() != 1 or df.groupby("publisher_case").patient_id.nunique().max() != 1:
            raise ValueError("Inferred filename groups do not match publisher Case metadata")
        # Retain identical group keys so previously frozen split IDs remain valid.
        df.attrs["grouping_source"] = "Validated one-to-one against bus_data.csv Case column"
    else:
        df.attrs["grouping_source"] = "Inferred filename groups; publisher metadata unavailable"
    df["label"] = (df["Pathology"] == "malignant").astype(int)
    df["image_path"] = df["ID"].map(lambda s: str(root / "Images" / (s + ".png")))
    df["mask_path"] = df["ID"].map(lambda s: str(root / "Masks" / ("mask_" + s.removeprefix("bus_") + ".png")))
    for _, record in df.iterrows():
        if not Path(record["image_path"]).exists() or not Path(record["mask_path"]).exists():
            raise FileNotFoundError(f"Image/mask pair missing for {record['ID']}: "
                                    f"{record['image_path']} / {record['mask_path']}")
    if df["ID"].duplicated().any():
        raise ValueError("Duplicate image ID in metadata. Audit the file first.")
    return df.reset_index(drop=True)


def make_patient_splits(df, seed=42):
    """Fixed, stratified GROUP split: ~60% train, 20% val, 20% test.

    Outer 5-fold selects test patients. Inner 4-fold selects validation patients.
    Existing publisher folds are not used; protocol must be stated in reporting.
    """
    outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    pool_idx, test_idx = next(outer.split(df, df["label"], df["patient_id"]))
    pool = df.iloc[pool_idx].reset_index(drop=True)
    inner = StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=seed + 1)
    train_idx, val_idx = next(inner.split(pool, pool["label"], pool["patient_id"]))
    splits = {"train": pool.iloc[train_idx].reset_index(drop=True),
              "val": pool.iloc[val_idx].reset_index(drop=True),
              "test": df.iloc[test_idx].reset_index(drop=True)}
    groups = {k: set(v["patient_id"]) for k, v in splits.items()}
    assert not(groups["train"] & groups["val"] or groups["train"] & groups["test"] or groups["val"] & groups["test"]), "Patient leakage!"
    return splits


def prepare_image(image: Image.Image, side=256, method="raw"):
    """Medical mask geometry is preserved; contrast enhancement affects image only."""
    img = np.asarray(image.convert("L").resize((side, side), Image.Resampling.BILINEAR), dtype=np.uint8)
    if method == "clahe":
        img = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(img)
    elif method != "raw":
        raise ValueError("method must be raw or clahe")
    return img


class UltrasoundDataset(Dataset):
    def __init__(self, metadata, side=256, method="raw", augment=False):
        self.frame = metadata.reset_index(drop=True)
        self.side = side
        self.method = method
        self.augment = augment

    def __len__(self):
        return len(self.frame)

    def __getitem__(self, index):
        rec = self.frame.iloc[index]
        image = prepare_image(Image.open(rec["image_path"]), self.side, self.method)
        mask = np.asarray(Image.open(rec["mask_path"]).convert("L").resize(
            (self.side, self.side), Image.Resampling.NEAREST), dtype=np.uint8)
        mask = (mask > 0).astype(np.float32)
        if self.augment:
            if random.random() < 0.5:
                image = np.fliplr(image)
                mask = np.fliplr(mask)
            if random.random() < 0.25:
                image = cv2.GaussianBlur(image, (3, 3), sigmaX=0.8)
        image = np.ascontiguousarray(image, dtype=np.float32) / 255.0
        mask = np.ascontiguousarray(mask, dtype=np.float32)
        return torch.from_numpy(image[None]), torch.from_numpy(mask[None])
