"""Plot recorded training behavior; no test data are used."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='results/raw_first')
    args = ap.parse_args()
    root = Path(args.out)
    history = pd.read_csv(root / 'training_history.csv')
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    axes[0].plot(history.epoch, history.train_loss, color='#0f766e', marker='o')
    axes[0].set(title='Learning from training images', xlabel='Epoch', ylabel='Training loss')
    axes[1].plot(history.epoch, history.val_dice, color='#0f766e', marker='o', label='Dice')
    axes[1].plot(history.epoch, history.val_iou, color='#64748b', marker='.', label='IoU')
    axes[1].set(title='Validation overlap', xlabel='Epoch', ylabel='Overlap score', ylim=(0,1))
    axes[1].legend(frameon=False)
    for ax in axes:
        ax.grid(alpha=0.2)
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('SonoTrust first baseline — validation results, not held-out test performance')
    fig.tight_layout()
    fig.savefig(root / 'learning_curves.png', dpi=160)
    plt.close(fig)
    print(root / 'learning_curves.png')


if __name__ == '__main__':
    main()
