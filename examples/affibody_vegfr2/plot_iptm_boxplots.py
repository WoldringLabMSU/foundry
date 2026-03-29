"""
Box plots of ipTM values across affibody design targets.

Usage:
    python plot_iptm_boxplots.py
    python plot_iptm_boxplots.py --csv path/to/affibody_targets_ipTM.csv
    python plot_iptm_boxplots.py --csv affibody_targets_ipTM.csv --out iptm_boxplots.png
"""

import argparse
import os

import matplotlib.pyplot as plt
import pandas as pd

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_CSV = os.path.join(os.path.dirname(__file__), "affibody_targets_ipTM.csv")
DEFAULT_OUT = os.path.join(os.path.dirname(__file__), "iptm_boxplots.png")

# Column display labels (key = CSV column name, value = plot label)
COLUMN_LABELS = {
    "Target1":      "Target 1",
    "Target2":      "Target 2",
    "Target3":      "Target 3",
    "Target3_RFD3": "Target 3\n(RFD3)",
}


def load_data(csv_path: str) -> dict[str, list[float]]:
    df = pd.read_csv(csv_path)
    data = {}
    for col in COLUMN_LABELS:
        if col in df.columns:
            values = df[col].dropna().tolist()
            data[col] = values
        else:
            print(f"Warning: column '{col}' not found in {csv_path}, skipping.")
    return data


def plot_boxplots(data: dict, out_path: str):
    columns  = list(data.keys())
    values   = [data[c] for c in columns]
    labels   = [COLUMN_LABELS[c] for c in columns]

    fig, ax = plt.subplots(figsize=(7, 5))

    bp = ax.boxplot(
        values,
        patch_artist=True,
        notch=False,
        widths=0.5,
        medianprops=dict(color="black", linewidth=2),
        whiskerprops=dict(linewidth=1.5),
        capprops=dict(linewidth=1.5),
        flierprops=dict(marker="o", markersize=4, linestyle="none",
                        markerfacecolor="grey", markeredgecolor="grey", alpha=0.6),
    )

    # Colour each box differently
    colours = ["#4C72B0", "#55A868", "#C44E52", "#DD8452"]
    for patch, colour in zip(bp["boxes"], colours[: len(bp["boxes"])]):
        patch.set_facecolor(colour)
        patch.set_alpha(0.7)

    # Reference line at ipTM = 0.75
    ax.axhline(0.75, color="red", linestyle="--", linewidth=1.2)

    ax.set_xticks(range(1, len(labels) + 1))
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel("ipTM", fontsize=12)
    ax.set_title("ipTM Distributions Across Affibody Design Targets", fontsize=13)
    ax.set_ylim(0, 1)

    ax.yaxis.grid(True, linestyle="--", alpha=0.5)
    ax.set_axisbelow(True)

    # Annotate with n and median
    for i, (col, vals) in enumerate(zip(columns, values), start=1):
        median = pd.Series(vals).median()
        ax.text(i, 0.02, f"n={len(vals)}\nmed={median:.2f}",
                ha="center", va="bottom", fontsize=8, color="#333333")

    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    print(f"Saved: {out_path}")
    plt.show()


def main():
    parser = argparse.ArgumentParser(description="Plot ipTM box plots.")
    parser.add_argument("--csv", default=DEFAULT_CSV,
                        help="Path to ipTM CSV file (default: affibody_targets_ipTM.csv)")
    parser.add_argument("--out", default=DEFAULT_OUT,
                        help="Output image path (default: iptm_boxplots.png)")
    args = parser.parse_args()

    data = load_data(args.csv)
    if not data:
        raise ValueError("No data columns found — check your CSV column names.")
    plot_boxplots(data, args.out)


if __name__ == "__main__":
    main()
