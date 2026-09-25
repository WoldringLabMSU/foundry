"""
Step 5 — Collect ipTM scores from AF3 output JSON files.

AF3 writes a *_summary_confidences.json per prediction containing
the ipTM. This script collects them into a single CSV for ranking.

Usage:
    python examples/c1q_binder_maturation/05_collect_af3_iptm.py \
        --af3_out_dir $SCRATCH/c1q_binder_maturation/af3_outputs \
        --out_csv     $SCRATCH/c1q_binder_maturation/af3_iptm_results.csv
"""

import argparse
import csv
import json
import os


def find_summary_jsons(af3_out_dir: str):
    """Recursively find AF3 *_summary_confidences.json files."""
    for root, _, files in os.walk(af3_out_dir):
        for fname in sorted(files):
            if fname.endswith("_summary_confidences.json"):
                yield os.path.join(root, fname)


def parse_summary(path: str) -> dict:
    with open(path) as f:
        data = json.load(f)
    return {
        "iptm":          data.get("iptm",          float("nan")),
        "ptm":           data.get("ptm",           float("nan")),
        "ranking_score": data.get("ranking_score", float("nan")),
        "fraction_disordered": data.get("fraction_disordered", float("nan")),
        "has_clash":     data.get("has_clash",     None),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--af3_out_dir", required=True)
    parser.add_argument("--out_csv",     required=True)
    args = parser.parse_args()

    rows = []
    for path in find_summary_jsons(args.af3_out_dir):
        design_id = os.path.basename(os.path.dirname(path))
        metrics = parse_summary(path)
        rows.append({"design_id": design_id, "summary_json": path, **metrics})

    rows.sort(key=lambda r: r["iptm"], reverse=True)

    os.makedirs(os.path.dirname(os.path.abspath(args.out_csv)), exist_ok=True)
    with open(args.out_csv, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["design_id", "iptm", "ptm", "ranking_score",
                        "fraction_disordered", "has_clash", "summary_json"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Collected {len(rows)} AF3 predictions → {args.out_csv}")
    if rows:
        print(f"Top design: {rows[0]['design_id']}  ipTM={rows[0]['iptm']:.3f}")


if __name__ == "__main__":
    main()
