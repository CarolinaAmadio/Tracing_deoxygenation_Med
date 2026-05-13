# Directory structure

## 00_build_SUPERFLOAT

### Purpose
Build the SUPERFLOAT dataset starting from the CORIOLIS dataset.

### Main script
- `Launcher.sh`

### Input
- CORIOLIS dataset

### Output
- SUPERFLOAT dataset (QCed dataset)

### Notes
- Requires the `bit.sea` repository:  
  `git@github.com:inogs/bit.sea.git`
- Recommended branch: `origin/fix-qc-superfloat`
- The output consists of a quality-controlled dataset.

### Philosophy
Variable-dependent and variable-independent quality controls are performed in this step.

For further details, see our audit:  
DOI: `10.5281/zenodo.17414473`
