"""Compact U-Net baseline suitable for laptops/Colab (binary segmentation)."""
import torch
from torch import nn
import torch.nn.functional as F


class DoubleConv(nn.Module):
    def __init__(self, cin, cout):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv2d(cin, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
            nn.Conv2d(cout, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True))

    def forward(self, x):
        return self.layers(x)


class UNet(nn.Module):
    def __init__(self, base=16):
        super().__init__()
        self.enc1 = DoubleConv(1, base)
        self.enc2 = DoubleConv(base, base * 2)
        self.enc3 = DoubleConv(base * 2, base * 4)
        self.bottleneck = DoubleConv(base * 4, base * 8)
        self.pool = nn.MaxPool2d(2)
        self.dec3 = DoubleConv(base * 12, base * 4)
        self.dec2 = DoubleConv(base * 6, base * 2)
        self.dec1 = DoubleConv(base * 3, base)
        self.head = nn.Conv2d(base, 1, 1)

    def forward(self, x):
        a = self.enc1(x)
        b = self.enc2(self.pool(a))
        c = self.enc3(self.pool(b))
        d = self.bottleneck(self.pool(c))
        d = self.dec3(torch.cat([F.interpolate(d, size=c.shape[2:], mode='bilinear', align_corners=False), c], dim=1))
        d = self.dec2(torch.cat([F.interpolate(d, size=b.shape[2:], mode='bilinear', align_corners=False), b], dim=1))
        d = self.dec1(torch.cat([F.interpolate(d, size=a.shape[2:], mode='bilinear', align_corners=False), a], dim=1))
        return self.head(d)  # logits, NOT probabilities


def loss_fn(logits, target):
    probs = torch.sigmoid(logits)
    overlap = (probs * target).sum(dim=(1, 2, 3))
    dice_loss = 1 - ((2 * overlap + 1) / (probs.sum((1, 2, 3)) + target.sum((1, 2, 3)) + 1)).mean()
    return 0.5 * nn.functional.binary_cross_entropy_with_logits(logits, target) + 0.5 * dice_loss


@torch.no_grad()
def batch_scores(logits, target):
    pred = (torch.sigmoid(logits) >= 0.5).float()
    intersection = (pred * target).sum((1, 2, 3))
    union = (pred + target - pred * target).sum((1, 2, 3))
    dice = (2 * intersection + 1e-6) / (pred.sum((1, 2, 3)) + target.sum((1, 2, 3)) + 1e-6)
    iou = (intersection + 1e-6) / (union + 1e-6)
    return dice.cpu().numpy(), iou.cpu().numpy()
