# C1q Binder Maturation — HPC Setup

Goal: redesign PTPRZ1's binding interface against the C1q globular head
heterotrimer (C1qA/B/C) using RFD3 partial diffusion → MPNN → AF3 evaluation.

---

## Prerequisites

- MSU HPCC account with access to GPU nodes
- `foundry_clean` conda environment (see the affibody_vegfr2 SETUP_SUMMARY.md)
- Your PTPRZ1–C1q starting complex as a CIF file (4 chains: A=PTPRZ1, B=C1qA,
  C=C1qB, D=C1qC)
- FASTA files for C1qA, C1qB, and C1qC (needed for AF3 input generation)

---

## Step 0 — Clone and set up

Clone foundry into your scratch directory to avoid filling your 1 GB home quota:

```bash
# On the login node:
cd /mnt/scratch/woldring
git clone https://github.com/WoldringLabMSU/foundry.git
cd foundry
git checkout C1q_binder_maturation
```

Create the pipeline output directory alongside it:

```bash
mkdir -p /mnt/scratch/woldring/c1q_binder_maturation
```

---

## Step 1 — Populate placeholders

Before running any scripts, edit these files and fill in the `<-- UPDATE` lines:

### `examples/c1q_binder_maturation/01_rfd3_design.py`
- `COMPLEX_CIF` — absolute path to your PTPRZ1–C1q complex CIF
- `PTPRZ1_LEN`, `C1QA_LEN`, `C1QB_LEN`, `C1QC_LEN` — chain lengths
- `INTERFACE_RESIDUES` — PTPRZ1 residue numbers at the C1q interface
- `C1Q_HOTSPOTS` — hotspot residue ranges on chains B, C, D

To find chain lengths, run:

```bash
conda activate foundry_clean
export PYTHONNOUSERSITE=1
unset PYTHONPATH
cd /mnt/scratch/woldring/foundry
python examples/c1q_binder_maturation/check_chain_lengths.py \
    --structure /path/to/your/ptprz1_c1q_complex.cif
```

To find interface residues, open the complex in PyMOL and run:

```
select interface, (chain A) within 5.0 of (chain B or chain C or chain D)
```

Then note the residue numbers from the selection.

### `examples/c1q_binder_maturation/slurm/*.sh`
- `SCRATCH` — set to `/mnt/scratch/woldring`
- `FOUNDRY_DIR` — set to `/mnt/scratch/woldring/foundry`
- `C1QA_FASTA`, `C1QB_FASTA`, `C1QC_FASTA` — in `04_af3_array.sh`
- `--hotspot_residues` — in `02_screen.sh` (format: `B:101-110 C:45-55 D:80-90`)

---

## Step 2 — Run the pipeline

Submit jobs in order; each step depends on the previous one completing.

### Step 1: RFD3 partial diffusion

```bash
cd /mnt/scratch/woldring/foundry
sbatch examples/c1q_binder_maturation/slurm/01_rfd3.sh
```

Outputs (in `$SCRATCH/c1q_binder_maturation/`):
- `rfd3_conservative/` — ~16 CIF.gz structures (8 batches × 2)
- `rfd3_moderate/`
- `rfd3_aggressive/`

Monitor: `squeue -u $USER`  
Logs: `c1q_rfd3_<jobid>.log`

### Step 2: Geometric screening

```bash
sbatch examples/c1q_binder_maturation/slurm/02_screen.sh
```

Outputs:
- `screening_results.csv` — all designs with clash/contact metrics
- `passed_designs.txt` — paths of designs that passed (input to MPNN)

### Step 3: MPNN sequence design (array job)

```bash
# First check how many designs passed:
wc -l $SCRATCH/c1q_binder_maturation/passed_designs.txt

# Then set --array=0-(n_workers-1) in 03_mpnn_array.sh (default: 8 workers)
sbatch examples/c1q_binder_maturation/slurm/03_mpnn_array.sh
```

Outputs:
- `mpnn_designs/mpnn_sequences.csv` — all MPNN-designed sequences

### Step 4: Generate AF3 inputs (array job)

```bash
sbatch examples/c1q_binder_maturation/slurm/04_af3_array.sh
```

Outputs:
- `af3_inputs/<design_id>.json` — one AF3 input per design

### Run AF3

AF3 can be run via:
- **Local installation**: `python run_alphafold.py --json_path=<input.json> --output_dir=$SCRATCH/c1q_binder_maturation/af3_outputs --model_dir=/path/to/af3_weights`
- **AF3 server**: Upload JSONs to alphafoldserver.com (batch upload supported)
- **MSU ICER**: Check if AF3 is available as a module: `module spider alphafold`

### Step 5: Collect AF3 results

After AF3 runs complete:

```bash
conda activate foundry_clean
export PYTHONNOUSERSITE=1
unset PYTHONPATH

python examples/c1q_binder_maturation/05_collect_af3_iptm.py \
    --af3_out_dir $SCRATCH/c1q_binder_maturation/af3_outputs \
    --out_csv     $SCRATCH/c1q_binder_maturation/af3_iptm_results.csv
```

This produces a ranked CSV with ipTM, pTM, ranking_score, fraction_disordered,
and has_clash for every prediction.

---

## SLURM tips

- Default partition on MSU HPCC GPU nodes: `--partition=gpu` (or `gpu-v100`, `gpu-a100` — check with `sinfo`)
- Check your allocation: `sacctmgr show assoc where user=$USER format=account,partition,qos`
- Cancel a job: `scancel <jobid>`
- Check GPU usage during a run: `ssh <node> nvidia-smi` (node name from `squeue`)

---

## Interpreting results

| ipTM | Interpretation |
|------|----------------|
| ≥ 0.80 | Strong predicted binding |
| 0.70–0.79 | Moderate; worth experimental follow-up |
| < 0.70 | Unlikely to bind |

The top designs from `af3_iptm_results.csv` are candidates for experimental
validation (e.g., SPR, ITC, or cell-based binding assays).
