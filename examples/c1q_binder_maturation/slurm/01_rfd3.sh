#!/bin/bash
#SBATCH --job-name=c1q_rfd3
#SBATCH --output=%x_%j.log
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --partition=general-long-gpu

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
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

OUT_DIR=$SCRATCH/c1q_binder_maturation

python $FOUNDRY_DIR/examples/c1q_binder_maturation/01_rfd3_design.py \
    --out_dir     $OUT_DIR \
    --noise_level all \
    --n_batches   8 \
    --batch_size  2 \
    --seed        42
