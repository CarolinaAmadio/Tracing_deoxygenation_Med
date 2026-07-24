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
- Installation example:
  ```bash
  git clone git@github.com:inogs/bit.sea.git
  cd bit.sea
  pip install .
  git checkout `origin/fix-qc-superfloat` 

- Recommended branch: `origin/fix-qc-superfloat`
- The output consists of a quality-controlled dataset.

### Philosophy
Variable-dependent and variable-independent quality controls are performed in this step.

For further details, see our audit:  
DOI: `10.5281/zenodo.17414473`

## 01_calc_clim

### Purpose
Compute climatological fields from the SUPERFLOAT dataset.
Yearly and monthly climatologies are computed in dedicated subdirectories with specific scripts.

### Main scripts
- `yearly_clim/Launcher.sh`
- `monthly_clim/Launcher.sh`

Calculation of climatologies:
- `Yr_Climfloat_netcdf_Coriolis.py`
- `Yr_Climfloat_netcdf_superfloat.py`
- `Month_Climfloat_netcdf_Coriolis.py`
- `Month_Climfloat_netcdf_superfloat.py`

Visualization of climatologies:
- `compare_clima_doxy.py`
- `compare_clima_doxy_monthly.py`
- `clim_visualizer_html_pdf.py`
- `create_pdf.py`

### Input
- SUPERFLOAT dataset
- (optionally CORIOLIS/BGC-Argo float profiles for the parallel Coriolis climatology scripts)

### Output
- Climatological fields
- Mean vertical profiles
- Intermediate statistics files
- NetCDF climatology files such as:
  - `yr_Avg_superfloat_dataset_<variable>.nc`
  - `yr_Std_superfloat_dataset_<variable>.nc`
  - `mm_Avg_superfloat_dataset_<variable>.nc`
  - `mm_Std_superfloat_dataset_<variable>.nc`

### Notes
- Climatologies are computed after the quality-control procedure performed in `00_build_SUPERFLOAT`.
- The `yearly_clim` and `monthly_clim` launchers write output into `0_clim_calc/yearly_clim/` and `0_clim_calc/monthly_clim/`.
- Outputs generated in this step are used by subsequent analysis modules.

### Philosophy
This module provides the reference climatological state used to evaluate temporal and spatial variability in the Mediterranean Sea.
