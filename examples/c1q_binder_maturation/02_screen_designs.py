"""
Step 2 — Geometric screening of RFD3 designs.

For each CIF.gz in the RFD3 output directories:
  1. Clash detection   — flag any PTPRZ1 heavy atom within CLASH_DIST Å of
                         any C1q heavy atom (indicates bad packing).
  2. Hotspot contacts  — count PTPRZ1 heavy atoms within CONTACT_DIST Å of
                         the specified C1q hotspot residues.

Designs that pass (no clashes AND ≥ MIN_CONTACTS hotspot contacts) are written
to a filtered list for MPNN.

Ported and extended from Using_Foundry/05_screen_rfd3_designs.py.
BUG FIX: the original script README documented --target_chain B but the actual
YAML/PDB used chain C. Here all C1q chains (B, C, D) are checked explicitly via
--c1q_chains, eliminating the silent chain-mismatch drop.

Usage:
    python examples/c1q_binder_maturation/02_screen_designs.py \
        --rfd3_dirs $SCRATCH/c1q_binder_maturation/rfd3_conservative \
                    $SCRATCH/c1q_binder_maturation/rfd3_moderate \
                    $SCRATCH/c1q_binder_maturation/rfd3_aggressive \
        --out_csv   $SCRATCH/c1q_binder_maturation/screening_results.csv \
        --pass_list $SCRATCH/c1q_binder_maturation/passed_designs.txt \
        --ptprz1_chain A \
        --c1q_chains B C D \
        --hotspot_residues B:101-110 C:45-55 D:80-90
"""

import argparse
import csv
import gzip
import io
import os

import biotite.structure.io.pdbx as pdbx
import numpy as np

CLASH_DIST   = 1.8   # Å — PTPRZ1–C1q heavy-atom clash threshold
CONTACT_DIST = 4.5   # Å — hotspot contact threshold
MIN_CONTACTS = 3     # minimum hotspot contacts to pass


def read_cif_gz(path: str):
    if path.endswith(".gz"):
        with gzip.open(path, "rt") as fh:
            content = fh.read()
        cif = pdbx.CIFFile.read(io.StringIO(content))
    else:
        cif = pdbx.CIFFile.read(path)
    return pdbx.get_structure(cif, model=1)


def parse_hotspot_spec(specs: list[str]) -> dict[str, list[int]]:
    """Parse 'B:101-110' → {'B': [101,102,...,110]}"""
    hotspots: dict[str, list[int]] = {}
    for spec in specs:
        chain, res_range = spec.split(":")
        if "-" in res_range:
            lo, hi = res_range.split("-")
            residues = list(range(int(lo), int(hi) + 1))
        else:
            residues = [int(res_range)]
        hotspots.setdefault(chain, []).extend(residues)
    return hotspots


def screen_structure(
    structure,
    ptprz1_chain: str,
    c1q_chains: list[str],
    hotspot_residues: dict[str, list[int]],
) -> dict:
    binder = structure[structure.chain_id == ptprz1_chain]
    target = structure[np.isin(structure.chain_id, c1q_chains)]

    if binder.shape[0] == 0 or target.shape[0] == 0:
        return {"n_clashes": -1, "n_hotspot_contacts": -1, "passes": False,
                "error": "chain not found"}

    b_coords = binder.coord      # (N, 3)
    t_coords = target.coord      # (M, 3)

    # Pairwise distances — chunked to avoid OOM on large systems
    chunk = 512
    min_dist = np.inf
    n_clashes = 0
    for i in range(0, len(b_coords), chunk):
        b_chunk = b_coords[i:i + chunk]
        diffs = b_chunk[:, None, :] - t_coords[None, :, :]   # (chunk, M, 3)
        dists = np.sqrt((diffs ** 2).sum(-1))                 # (chunk, M)
        min_dist = min(min_dist, dists.min())
        n_clashes += int((dists < CLASH_DIST).any(axis=1).sum())

    # Hotspot contacts
    n_contacts = 0
    for chain, residues in hotspot_residues.items():
        hs_atoms = structure[
            (structure.chain_id == chain) &
            np.isin(structure.res_id, residues)
        ]
        if hs_atoms.shape[0] == 0:
            continue
        hs_coords = hs_atoms.coord
        for i in range(0, len(b_coords), chunk):
            b_chunk = b_coords[i:i + chunk]
            diffs = b_chunk[:, None, :] - hs_coords[None, :, :]
            dists = np.sqrt((diffs ** 2).sum(-1))
            n_contacts += int((dists < CONTACT_DIST).any(axis=1).sum())

    passes = (n_clashes == 0) and (n_contacts >= MIN_CONTACTS)
    return {
        "min_dist_A":         round(float(min_dist), 3),
        "n_clashes":          n_clashes,
        "n_hotspot_contacts": n_contacts,
        "passes":             passes,
    }


def iter_cif_gz(directories: list[str]):
    for d in directories:
        if not os.path.isdir(d):
            print(f"Warning: directory not found: {d}")
            continue
        for fname in sorted(os.listdir(d)):
            if fname.endswith(".cif.gz") or fname.endswith(".cif"):
                yield os.path.join(d, fname), f"{os.path.basename(d)}/{fname}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rfd3_dirs",        nargs="+", required=True)
    parser.add_argument("--out_csv",          required=True)
    parser.add_argument("--pass_list",        required=True,
                        help="Text file listing paths of passing designs (input to MPNN)")
    parser.add_argument("--ptprz1_chain",     default="A")
    parser.add_argument("--c1q_chains",       nargs="+", default=["B", "C", "D"])
    parser.add_argument("--hotspot_residues", nargs="+", default=[],
                        help="Format: CHAIN:START-END or CHAIN:RESNUM, e.g. B:101-110 C:45")
    args = parser.parse_args()

    hotspots = parse_hotspot_spec(args.hotspot_residues)
    os.makedirs(os.path.dirname(os.path.abspath(args.out_csv)), exist_ok=True)

    rows = []
    passing_paths = []

    for fpath, label in iter_cif_gz(args.rfd3_dirs):
        print(f"Screening {label} ...", end=" ", flush=True)
        try:
            structure = read_cif_gz(fpath)
            result = screen_structure(
                structure,
                ptprz1_chain=args.ptprz1_chain,
                c1q_chains=args.c1q_chains,
                hotspot_residues=hotspots,
            )
        except Exception as e:
            result = {"n_clashes": -1, "n_hotspot_contacts": -1, "passes": False, "error": str(e)}

        status = "PASS" if result["passes"] else "FAIL"
        print(status)
        row = {"source": label, "path": fpath, **result}
        rows.append(row)
        if result["passes"]:
            passing_paths.append(fpath)

    # Write CSV
    fieldnames = ["source", "path", "min_dist_A", "n_clashes", "n_hotspot_contacts", "passes"]
    with open(args.out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    # Write pass list
    with open(args.pass_list, "w") as f:
        f.writelines(p + "\n" for p in passing_paths)

    n_pass = len(passing_paths)
    n_total = len(rows)
    print(f"\nScreening complete: {n_pass}/{n_total} designs passed.")
    print(f"  Results   → {args.out_csv}")
    print(f"  Pass list → {args.pass_list}")


if __name__ == "__main__":
    main()
