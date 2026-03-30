"""
Extract chain A amino acid sequences from RFD3 output CIF.gz files.

Scans three output subdirectories and writes a CSV with:
  - Column 1: source directory + filename
  - Column 2: affibody (chain A) amino acid sequence (one-letter code)

Usage:
    python extract_affibody_sequences.py
    python extract_affibody_sequences.py --outdir /mnt/home/woldring/foundry/outputs --out sequences.csv
"""

import argparse
import csv
import gzip
import io
import os

import biotite.structure.io.pdbx as pdbx
from biotite.sequence import ProteinSequence
from biotite.structure import get_residue_starts

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_OUTDIR = "/mnt/home/woldring/foundry/outputs"
DEFAULT_OUT    = os.path.join(
    os.path.dirname(__file__), "affibody_sequences.csv"
)

SUBDIRS = [
    "affibody_vegfr2/rfd3_conservative",
    "affibody_vegfr2/rfd3_moderate",
    "affibody_vegfr2_slim/rfd3_conservative",
]

AFFIBODY_CHAIN = "A"


def read_cif_gz(path: str):
    """Read a .cif.gz file and return a biotite AtomArray (model 1)."""
    with gzip.open(path, "rt") as fh:
        content = fh.read()
    cif_file = pdbx.CIFFile.read(io.StringIO(content))
    return pdbx.get_structure(cif_file, model=1)


def extract_sequence(atom_array) -> str:
    """Return one-letter amino acid sequence for chain A."""
    chain_a = atom_array[atom_array.chain_id == AFFIBODY_CHAIN]
    if chain_a.shape[0] == 0:
        return ""
    res_starts = get_residue_starts(chain_a)
    residues = chain_a.res_name[res_starts]
    seq = ""
    for res in residues:
        try:
            seq += ProteinSequence.convert_letter_3to1(res)
        except Exception:
            seq += "X"  # unknown residue
    return seq


def collect_sequences(outdir: str) -> list[tuple[str, str]]:
    records = []
    for subdir in SUBDIRS:
        dirpath = os.path.join(outdir, subdir)
        if not os.path.isdir(dirpath):
            print(f"Warning: directory not found, skipping: {dirpath}")
            continue

        files = sorted(
            f for f in os.listdir(dirpath) if f.endswith(".cif.gz")
        )
        print(f"  {subdir}: {len(files)} file(s) found")

        for fname in files:
            fpath = os.path.join(dirpath, fname)
            try:
                atoms = read_cif_gz(fpath)
                seq   = extract_sequence(atoms)
                label = f"{subdir}/{fname}"
                records.append((label, seq))
            except Exception as e:
                print(f"    WARNING: could not parse {fname}: {e}")

    return records


def main():
    parser = argparse.ArgumentParser(description="Extract affibody sequences from CIF.gz files.")
    parser.add_argument("--outdir", default=DEFAULT_OUTDIR,
                        help="Root outputs directory (default: /mnt/home/woldring/foundry/outputs)")
    parser.add_argument("--out", default=DEFAULT_OUT,
                        help="Output CSV path (default: affibody_sequences.csv)")
    args = parser.parse_args()

    print(f"Scanning: {args.outdir}")
    records = collect_sequences(args.outdir)

    with open(args.out, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["source", "sequence"])
        writer.writerows(records)

    print(f"\nWrote {len(records)} sequences → {args.out}")


if __name__ == "__main__":
    main()
