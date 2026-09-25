"""
Step 3 — MPNN sequence design on screened RFD3 backbones.

Reads a list of passing CIF.gz paths (from 02_screen_designs.py), runs
LigandMPNN on each backbone (designing only the PTPRZ1 chain), and writes
designed structures + sequences to the output directory.

Usage:
    # Single node (all passing designs):
    python examples/c1q_binder_maturation/03_mpnn_sequence_design.py \
        --pass_list $SCRATCH/c1q_binder_maturation/passed_designs.txt \
        --out_dir   $SCRATCH/c1q_binder_maturation/mpnn_designs

    # SLURM array (one task per design — see slurm/03_mpnn_array.sh):
    python examples/c1q_binder_maturation/03_mpnn_sequence_design.py \
        --pass_list $SCRATCH/c1q_binder_maturation/passed_designs.txt \
        --out_dir   $SCRATCH/c1q_binder_maturation/mpnn_designs \
        --task_id   $SLURM_ARRAY_TASK_ID \
        --n_tasks   $SLURM_ARRAY_TASK_COUNT
"""

import argparse
import csv
import os

import biotite.structure.io.pdbx as pdbx
import gzip, io
import numpy as np
from biotite.sequence import ProteinSequence
from biotite.structure import get_residue_starts
from mpnn.inference_engines.mpnn import MPNNInferenceEngine

PTPRZ1_CHAIN  = "A"
SEQS_PER_BACKBONE = 10
TEMPERATURE       = 0.1


def read_cif_gz(path: str):
    if path.endswith(".gz"):
        with gzip.open(path, "rt") as fh:
            content = fh.read()
        cif = pdbx.CIFFile.read(io.StringIO(content))
    else:
        cif = pdbx.CIFFile.read(path)
    return pdbx.get_structure(cif, model=1)


def extract_sequence(atom_array, chain: str) -> str:
    ch = atom_array[atom_array.chain_id == chain]
    if ch.shape[0] == 0:
        return ""
    starts = get_residue_starts(ch)
    seq = ""
    for res in ch.res_name[starts]:
        try:
            seq += ProteinSequence.convert_letter_3to1(res)
        except Exception:
            seq += "X"
    return seq


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pass_list", required=True,
                        help="Text file of passing CIF.gz paths (one per line)")
    parser.add_argument("--out_dir",   required=True)
    parser.add_argument("--seqs_per_backbone", type=int, default=SEQS_PER_BACKBONE)
    parser.add_argument("--temperature",       type=float, default=TEMPERATURE)
    parser.add_argument("--task_id",  type=int, default=None,
                        help="SLURM_ARRAY_TASK_ID (0-based). If set, process only this design.")
    parser.add_argument("--n_tasks",  type=int, default=None,
                        help="SLURM_ARRAY_TASK_COUNT. If set, chunk the pass_list.")
    args = parser.parse_args()

    with open(args.pass_list) as f:
        all_paths = [l.strip() for l in f if l.strip()]

    # SLURM array: each task processes a slice of the pass list
    if args.task_id is not None and args.n_tasks is not None:
        all_paths = all_paths[args.task_id::args.n_tasks]

    os.makedirs(args.out_dir, exist_ok=True)

    engine = MPNNInferenceEngine(
        model_type="ligand_mpnn",
        is_legacy_weights=True,
        out_directory=None,
        write_structures=False,
        write_fasta=False,
    )

    mpnn_cfg = {
        "batch_size":       args.seqs_per_backbone,
        "temperature":      args.temperature,
        "chains_to_design": [PTPRZ1_CHAIN],
        "remove_waters":    True,
    }

    records = []
    for path in all_paths:
        label = os.path.basename(path).replace(".cif.gz", "").replace(".cif", "")
        print(f"Running MPNN on {label} ...")
        try:
            atoms = read_cif_gz(path)
            outputs = engine.run(input_dicts=[mpnn_cfg], atom_arrays=[atoms])
            for i, out in enumerate(outputs):
                seq = extract_sequence(out.atom_array, PTPRZ1_CHAIN)
                design_id = f"{label}_mpnn{i:02d}"
                records.append({
                    "design_id":      design_id,
                    "source_backbone": path,
                    "ptprz1_sequence": seq,
                })
        except Exception as e:
            print(f"  WARNING: {label} failed — {e}")

    # Write sequences CSV
    out_csv = os.path.join(args.out_dir, "mpnn_sequences.csv")
    write_header = not os.path.exists(out_csv)
    with open(out_csv, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["design_id", "source_backbone", "ptprz1_sequence"])
        if write_header:
            writer.writeheader()
        writer.writerows(records)

    print(f"\nMPNN complete: {len(records)} sequences → {out_csv}")


if __name__ == "__main__":
    main()
