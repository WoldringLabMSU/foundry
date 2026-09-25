#!/bin/bash
#SBATCH --job-name=c1q_screen
#SBATCH --output=%x_%j.log
#SBATCH --time=2:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G

# ── Update these paths ────────────────────────────────────────────────────────
SCRATCH=/mnt/scratch/woldring
FOUNDRY_DIR=/mnt/scratch/woldring/foundry
CONDA_ENV=foundry_clean
# ─────────────────────────────────────────────────────────────────────────────

source ~/.bashrc
conda deactivate
conda deactivate
conda activate $CONDA_ENV
export PYTHONNOUSERSITE=1
unset PYTHONPATH

WORK=$SCRATCH/c1q_binder_maturation

python $FOUNDRY_DIR/examples/c1q_binder_maturation/02_screen_designs.py \
    --rfd3_dirs   $WORK/rfd3_conservative \
                  $WORK/rfd3_moderate \
                  $WORK/rfd3_aggressive \
    --out_csv     $WORK/screening_results.csv \
    --pass_list   $WORK/passed_designs.txt \
    --ptprz1_chain A \
    --c1q_chains   B C D \
    --hotspot_residues B:101-110 C:45-55 D:80-90   # <-- UPDATE with real hotspot residues
