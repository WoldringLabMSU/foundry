#!/bin/bash
#SBATCH --job-name=c1q_mpnn
#SBATCH --output=%x_%A_%a.log
#SBATCH --time=4:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --gres=gpu:1
#SBATCH --partition=general-long-gpu
#SBATCH --array=0-7   # <-- set to (n_workers - 1); each worker processes 1/N of pass_list

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

WORK=$SCRATCH/c1q_binder_maturation

python $FOUNDRY_DIR/examples/c1q_binder_maturation/03_mpnn_sequence_design.py \
    --pass_list         $WORK/passed_designs.txt \
    --out_dir           $WORK/mpnn_designs \
    --seqs_per_backbone 10 \
    --temperature       0.1 \
    --task_id           $SLURM_ARRAY_TASK_ID \
    --n_tasks           $SLURM_ARRAY_TASK_COUNT
