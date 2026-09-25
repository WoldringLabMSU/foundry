"""
Step 4 — Generate AlphaFold3 input JSON files for PTPRZ1–C1q gH evaluation.

For each MPNN-designed PTPRZ1 sequence, creates one AF3 JSON input containing:
  - Chain 1: designed PTPRZ1 sequence
  - Chain 2: C1qA sequence (fixed)
  - Chain 3: C1qB sequence (fixed)
  - Chain 4: C1qC sequence (fixed)

Extended from Using_Foundry/16_make_af3_csv_input.py to support three target
chains (C1qA/B/C) instead of one.

AF3 input format: https://github.com/google-deepmind/alphafold3
Each JSON is valid input for the AF3 server (alphafoldserver.com) or a local
AF3 installation.

Usage:
    python examples/c1q_binder_maturation/04_make_af3_input.py \
        --mpnn_csv   $SCRATCH/c1q_binder_maturation/mpnn_designs/mpnn_sequences.csv \
        --c1qa_fasta /path/to/c1qa.fasta \
        --c1qb_fasta /path/to/c1qb.fasta \
        --c1qc_fasta /path/to/c1qc.fasta \
        --out_dir    $SCRATCH/c1q_binder_maturation/af3_inputs \
        --task_id    $SLURM_ARRAY_TASK_ID \
        --n_tasks    $SLURM_ARRAY_TASK_COUNT
"""

import argparse
import csv
import json
import os
import re


def read_fasta(path: str) -> str:
    """Return the concatenated sequence from a single-entry FASTA file."""
    seq = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(">"):
                continue
            seq.append(line)
    return "".join(seq)


def make_af3_json(
    name: str,
    ptprz1_seq: str,
    c1qa_seq: str,
    c1qb_seq: str,
    c1qc_seq: str,
    seeds: list[int] | None = None,
) -> dict:
    """Build an AF3-compatible JSON input dict for a 4-chain complex."""
    return {
        "name": name,
        "modelSeeds": seeds or [1],
        "sequences": [
            {"proteinChain": {"sequence": ptprz1_seq, "count": 1}},
            {"proteinChain": {"sequence": c1qa_seq,   "count": 1}},
            {"proteinChain": {"sequence": c1qb_seq,   "count": 1}},
            {"proteinChain": {"sequence": c1qc_seq,   "count": 1}},
        ],
    }


def sanitize_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]", "_", s)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mpnn_csv",   required=True,
                        help="CSV from 03_mpnn_sequence_design.py (columns: design_id, ptprz1_sequence)")
    parser.add_argument("--c1qa_fasta", required=True, help="FASTA file for C1qA")
    parser.add_argument("--c1qb_fasta", required=True, help="FASTA file for C1qB")
    parser.add_argument("--c1qc_fasta", required=True, help="FASTA file for C1qC")
    parser.add_argument("--out_dir",    required=True)
    parser.add_argument("--seeds",      nargs="+", type=int, default=[1, 2, 3],
                        help="AF3 model seeds (default: 1 2 3 for three predictions per design)")
    parser.add_argument("--task_id",  type=int, default=None,
                        help="SLURM_ARRAY_TASK_ID (0-based)")
    parser.add_argument("--n_tasks",  type=int, default=None,
                        help="SLURM_ARRAY_TASK_COUNT")
    args = parser.parse_args()

    c1qa_seq = read_fasta(args.c1qa_fasta)
    c1qb_seq = read_fasta(args.c1qb_fasta)
    c1qc_seq = read_fasta(args.c1qc_fasta)

    with open(args.mpnn_csv) as f:
        rows = list(csv.DictReader(f))

    # SLURM array chunking
    if args.task_id is not None and args.n_tasks is not None:
        rows = rows[args.task_id::args.n_tasks]

    os.makedirs(args.out_dir, exist_ok=True)

    for row in rows:
        design_id  = sanitize_name(row["design_id"])
        ptprz1_seq = row["ptprz1_sequence"].strip()

        if not ptprz1_seq:
            print(f"Warning: empty sequence for {design_id}, skipping.")
            continue

        af3_input = make_af3_json(
            name=design_id,
            ptprz1_seq=ptprz1_seq,
            c1qa_seq=c1qa_seq,
            c1qb_seq=c1qb_seq,
            c1qc_seq=c1qc_seq,
            seeds=args.seeds,
        )

        out_path = os.path.join(args.out_dir, f"{design_id}.json")
        with open(out_path, "w") as f:
            json.dump(af3_input, f, indent=2)

    n = len(rows)
    print(f"Wrote {n} AF3 JSON inputs → {args.out_dir}")
    print("\nTo run AF3 locally (adjust paths for your installation):")
    print(f"  python run_alphafold.py \\")
    print(f"    --json_path={args.out_dir}/<design>.json \\")
    print(f"    --output_dir=$SCRATCH/c1q_binder_maturation/af3_outputs \\")
    print(f"    --model_dir=/path/to/af3_weights")


if __name__ == "__main__":
    main()
