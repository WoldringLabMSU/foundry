"""
Step 1 — RFD3 partial diffusion for PTPRZ1 interface maturation vs C1q gH.

Runs three partial-diffusion noise levels (conservative/moderate/aggressive)
and writes CIF.gz structures to the output directory.

Usage:
    python examples/c1q_binder_maturation/01_rfd3_design.py \
        --out_dir $SCRATCH/c1q_binder_maturation \
        --noise_level conservative        # or moderate / aggressive / all
        --n_batches 8
"""

import argparse
import os

from lightning.fabric import seed_everything
from rfd3.engine import RFD3InferenceConfig, RFD3InferenceEngine
from rfd3.inference.input_parsing import DesignInputSpecification

# ── Configuration — update to match your structure ───────────────────────────
COMPLEX_CIF = "/path/to/your/ptprz1_c1q_complex.cif"   # <-- UPDATE

PTPRZ1_CHAIN = "A"
C1QA_CHAIN   = "B"
C1QB_CHAIN   = "C"
C1QC_CHAIN   = "D"

PTPRZ1_LEN = 500   # <-- UPDATE (run check_chain_lengths.py)
C1QA_LEN   = 136   # <-- UPDATE
C1QB_LEN   = 136   # <-- UPDATE
C1QC_LEN   = 136   # <-- UPDATE

# PTPRZ1 residues at the binding interface with C1q gH
# (any PTPRZ1 residue with a heavy atom within 5 Å of any C1q atom)
INTERFACE_RESIDUES = []   # <-- UPDATE e.g. [45, 47, 50, 53, 78, 81]

# C1q hotspot residues spanning all three chains (A/B and B/C interface residues
# that make direct contacts with PTPRZ1 in the starting complex).
C1Q_HOTSPOTS = (
    f"{C1QA_CHAIN}<h1>-<h2>,{C1QA_CHAIN}<h3>,"   # <-- UPDATE with real residue numbers
    f"{C1QB_CHAIN}<h4>-<h5>,{C1QB_CHAIN}<h6>,"
    f"{C1QC_CHAIN}<h7>,{C1QC_CHAIN}<h8>"
)


def build_specs() -> dict:
    contig = (
        f"{PTPRZ1_CHAIN}1-{PTPRZ1_LEN},/0,"
        f"{C1QA_CHAIN}1-{C1QA_LEN},/0,"
        f"{C1QB_CHAIN}1-{C1QB_LEN},/0,"
        f"{C1QC_CHAIN}1-{C1QC_LEN}"
    )

    select_fixed_atoms = {
        f"{C1QA_CHAIN}1-{C1QA_LEN}": "ALL",
        f"{C1QB_CHAIN}1-{C1QB_LEN}": "ALL",
        f"{C1QC_CHAIN}1-{C1QC_LEN}": "ALL",
        f"{PTPRZ1_CHAIN}1-{PTPRZ1_LEN}": "BKBN",
    }

    unfixed_seq = ",".join(f"{PTPRZ1_CHAIN}{r}" for r in INTERFACE_RESIDUES)

    base = dict(
        input=COMPLEX_CIF,
        contig=contig,
        select_fixed_atoms=select_fixed_atoms,
        select_unfixed_sequence=unfixed_seq,
        select_hotspots=C1Q_HOTSPOTS,
        infer_ori_strategy="hotspots",
        plddt_enhanced=True,
        redesign_motif_sidechains=True,
    )

    return {
        "conservative": DesignInputSpecification(**base, partial_t=5.0),
        "moderate":     DesignInputSpecification(**base, partial_t=10.0),
        "aggressive":   DesignInputSpecification(**base, partial_t=15.0),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out_dir", required=True)
    parser.add_argument("--noise_level", default="all",
                        choices=["conservative", "moderate", "aggressive", "all"])
    parser.add_argument("--n_batches", type=int, default=8)
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    seed_everything(args.seed)

    specs = build_specs()
    if args.noise_level != "all":
        specs = {args.noise_level: specs[args.noise_level]}

    config = RFD3InferenceConfig(
        diffusion_batch_size=args.batch_size,
        low_memory_mode=True,
    )
    engine = RFD3InferenceEngine(**config)

    for name, spec in specs.items():
        out = os.path.join(args.out_dir, f"rfd3_{name}")
        print(f"\n── {name} (partial_t={spec.partial_t} Å) → {out}")
        engine.run(inputs=spec, out_dir=out, n_batches=args.n_batches)

    print("\nRFD3 complete.")


if __name__ == "__main__":
    main()
