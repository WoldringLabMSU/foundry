#!/bin/bash
#SBATCH --job-name=c1q_af3_input
#SBATCH --output=%x_%A_%a.log
#SBATCH --time=1:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --array=0-7   # <-- set to (n_workers - 1)

# NOTE: This script only GENERATES the AF3 input JSON files.
# Running AF3 itself requires a separate AF3 installation or the AF3 server.
# See SETUP.md for details.

# ── Update these paths ────────────────────────────────────────────────────────
SCRATCH=/mnt/scratch/woldring          # <-- UPDATE
FOUNDRY_DIR=/mnt/home/woldring/foundry # <-- UPDATE
CONDA_ENV=foundry_clean
C1QA_FASTA=/path/to/c1qa.fasta         # <-- UPDATE (FASTA for C1qA chain)
C1QB_FASTA=/path/to/c1qb.fasta         # <-- UPDATE (FASTA for C1qB chain)
C1QC_FASTA=/path/to/c1qc.fasta         # <-- UPDATE (FASTA for C1qC chain)
# ─────────────────────────────────────────────────────────────────────────────

source ~/.bashrc
conda activate $CONDA_ENV
export PYTHONNOUSERSITE=1
unset PYTHONPATH

WORK=$SCRATCH/c1q_binder_maturation

python $FOUNDRY_DIR/examples/c1q_binder_maturation/04_make_af3_input.py \
    --mpnn_csv    $WORK/mpnn_designs/mpnn_sequences.csv \
    --c1qa_fasta  $C1QA_FASTA \
    --c1qb_fasta  $C1QB_FASTA \
    --c1qc_fasta  $C1QC_FASTA \
    --out_dir     $WORK/af3_inputs \
    --seeds       1 2 3 \
    --task_id     $SLURM_ARRAY_TASK_ID \
    --n_tasks     $SLURM_ARRAY_TASK_COUNT
