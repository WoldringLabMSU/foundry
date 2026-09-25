"""
Print chain lengths from the input complex CIF/PDB.
Run this first to populate the chain lengths in inputs.yaml.

Usage:
    python examples/c1q_binder_maturation/check_chain_lengths.py \
        --input /path/to/ptprz1_c1q_complex.cif
"""

import argparse
import biotite.structure.io.pdbx as pdbx
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to input CIF or PDB")
    args = parser.parse_args()

    if args.input.endswith(".cif") or args.input.endswith(".cif.gz"):
        import gzip, io
        if args.input.endswith(".gz"):
            with gzip.open(args.input, "rt") as f:
                content = f.read()
            cif = pdbx.CIFFile.read(io.StringIO(content))
        else:
            cif = pdbx.CIFFile.read(args.input)
        s = pdbx.get_structure(cif, model=1)
    else:
        import biotite.structure.io.pdb as pdb_io
        pdb_file = pdb_io.PDBFile.read(args.input)
        s = pdb_file.get_structure(model=1)

    print(f"\nChain lengths in {args.input}:\n")
    for chain in np.unique(s.chain_id):
        chain_s = s[s.chain_id == chain]
        res_ids = np.unique(chain_s.res_id)
        print(f"  Chain {chain}: residues {res_ids[0]}–{res_ids[-1]}  (length {len(res_ids)})")

    print("\nUpdate inputs.yaml contig, select_fixed_atoms, and CHAIN ASSIGNMENT comment.")
    print("Suggested chain roles (verify against your structure):")
    chains = np.unique(s.chain_id)
    for i, c in enumerate(chains):
        roles = ["PTPRZ1 (binder)", "C1qA (target)", "C1qB (target)", "C1qC (target)"]
        role = roles[i] if i < len(roles) else "unknown"
        print(f"  Chain {c} → {role}")


if __name__ == "__main__":
    main()
