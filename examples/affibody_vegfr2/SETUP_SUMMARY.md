# Affibody-VEGFR2 Design Pipeline: HPC Setup Summary

## Goal
Use RFdiffusion3 (RFD3) partial diffusion to redesign interface residues on a 58-aa
affibody protein to improve binding affinity against VEGFR2. Starting from a known
affibody–VEGFR2 complex structure (`model.cif`).

---

## Files Created

| File | Purpose |
|------|---------|
| `examples/affibody_vegfr2/model.cif` | Starting affibody–VEGFR2 complex structure |
| `examples/affibody_vegfr2/inputs.yaml` | RFD3 input specs (3 noise levels) |
| `examples/affibody_vegfr2/affibody_vegfr2_design.ipynb` | End-to-end design notebook |
| `examples/affibody_vegfr2/affibody_vegfr2_design.py` | Script version (generated from notebook) |

### Design Parameters (confirmed from structure)
- **Chain A** — affibody, 58 residues
- **Chain B** — VEGFR2, 766 residues
- **Affibody interface residues** (unfixed sequence): `A6, A9, A10, A13-14, A17, A24-25, A27-28, A31, A35-36`
- **VEGFR2 hotspot residues**: `B131-135, B137, B164-165, B193-197, B213, B215-218, B253-257, B276, B286, B310-312`

---

## Steps Taken

### 1. Repository Setup
- Created branch `claude/affibody-vegfr2-design-bQu1b`
- Created `inputs.yaml` and `affibody_vegfr2_design.ipynb` with placeholder values
- Pushed to remote

### 2. Populating Correct Values
- User added `model.cif` to the branch via GitHub
- Merged updated foundry into the branch (pulled locally with `git pull --no-rebase`)
- Updated `COMPLEX_PDB` path to `/mnt/home/woldring/foundry/examples/affibody_vegfr2/model.cif`
- Updated affibody interface residues: `6, 9, 10, 13-14, 17, 24-25, 27-28, 31, 35-36`
- Updated VEGFR2 hotspot residues: `131-135, 137, 164-165, 193-197, 213, 215-218, 253-257, 276, 286, 310-312`
- Verified chain lengths by reading `model.cif` with biotite:
  - Chain A last residue: **58**
  - Chain B last residue: **766**
- Updated `VEGFR2_LEN` from placeholder 200 → **766** in both `inputs.yaml` and notebook

### 3. HPC Environment Setup
The HPC (MSU HPCC) had a system Python 3.11 module loaded that polluted `PYTHONPATH`,
preventing clean conda environment installs. Steps to resolve:

```bash
# Create a clean conda environment (Python 3.12 required by rc-foundry)
conda create -n foundry_clean python=3.12 --no-default-packages -y
conda activate foundry_clean

# Create activation hook to block system Python from interfering
mkdir -p /mnt/home/woldring/anaconda3/envs/foundry_clean/etc/conda/activate.d/
echo 'unset PYTHONPATH' > /mnt/home/woldring/anaconda3/envs/foundry_clean/etc/conda/activate.d/unset_pythonpath.sh

# Install foundry (must use PYTHONNOUSERSITE to avoid ~/.local conflicts)
unset PYTHONPATH
PYTHONNOUSERSITE=1 pip install "rc-foundry[all]"

# Download model checkpoints (~6 GB total)
PYTHONNOUSERSITE=1 /mnt/home/woldring/anaconda3/envs/foundry_clean/bin/foundry install base-models
```

Checkpoints installed to `~/.foundry/checkpoints/`:
- `rfd3_latest.ckpt` (2.7 GB)
- `rf3_foundry_01_24_latest_remapped.ckpt` (3.0 GB)
- `ligandmpnn_v_32_010_25.pt` (10.5 MB)
- `proteinmpnn_v_48_020.pt` (6.7 MB)

Added to `~/.bashrc` for persistent setup:
```bash
export PYTHONNOUSERSITE=1
export PATH="/mnt/home/woldring/anaconda3/envs/foundry_clean/bin:$PATH"
```

### 4. Notebook → Script Conversion
`nbconvert` was not installed by default; also the notebook lacked a kernelspec
so it initially exported as `.txt` instead of `.py`:

```bash
pip install nbconvert
# (kernelspec metadata was fixed in the notebook on the remote branch)
git pull origin claude/affibody-vegfr2-design-bQu1b
jupyter nbconvert --to script examples/affibody_vegfr2/affibody_vegfr2_design.ipynb
# → outputs affibody_vegfr2_design.py
```

### 5. SLURM Job Submission
Note: the compute nodes mount home as `/mnt/ffs24/home/woldring/` (not `/mnt/home/woldring/`).

```bash
sbatch <<EOF
#!/bin/bash --login
#SBATCH --job-name=affibody_vegfr2
#SBATCH --gres=gpu:1
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --output=affibody_vegfr2_%j.log

source ~/.bashrc
conda activate foundry_clean
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /mnt/ffs24/home/woldring/foundry
python examples/affibody_vegfr2/affibody_vegfr2_design.py
EOF
```

### 6. CUDA Out-of-Memory Fix
First run hit OOM on a 31.73 GB GPU because the system is large (824 residues total).
Fixed by:
- Reducing `diffusion_batch_size` from 8 → **2**
- Enabling `low_memory_mode=True` in `RFD3InferenceConfig`
- Increasing `n_batches` from 2 → **8** to keep total designs at 16 per noise level
- Adding `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` to SLURM script
- Increasing `--mem` to 64G

---

## How to Re-run After Any Changes

```bash
# On HPC — always do this first
conda activate foundry_clean
cd /mnt/home/woldring/foundry
git pull origin claude/affibody-vegfr2-design-bQu1b

# Regenerate script if notebook was changed
jupyter nbconvert --to script examples/affibody_vegfr2/affibody_vegfr2_design.ipynb

# Submit job
sbatch <<EOF
#!/bin/bash --login
#SBATCH --job-name=affibody_vegfr2
#SBATCH --gres=gpu:1
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --output=affibody_vegfr2_%j.log

source ~/.bashrc
conda activate foundry_clean
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /mnt/ffs24/home/woldring/foundry
python examples/affibody_vegfr2/affibody_vegfr2_design.py
EOF
```

Monitor progress:
```bash
squeue -u woldring
tail -f affibody_vegfr2_<JOBID>.log
```

---

## Expected Outputs

```
outputs/affibody_vegfr2/
├── rfd3_conservative/      # 16 designs, partial_t=5 Å  (side-chain remodelling)
├── rfd3_moderate/          # 16 designs, partial_t=10 Å (moderate backbone movement)
├── rfd3_aggressive/        # 16 designs, partial_t=15 Å (larger backbone changes)
├── top_10/
│   ├── rank01_<id>.cif     # Top 10 designs ranked by ipTM
│   └── ...
└── design_ranking.csv      # Full table: pLDDT, ipTM, pTM, bb_RMSD, clash flag
```

### Ranking Metrics
| Metric | Good threshold | Meaning |
|--------|---------------|---------|
| `plddt` | ≥ 0.80 | Per-residue confidence |
| `iptm` | ≥ 0.75 | Interface confidence — best predictor of binding |
| `ranking_score` | maximise | Overall model quality |
| `bb_rmsd_A` | 0.5–3.0 Å | Deviation from starting affibody backbone |
