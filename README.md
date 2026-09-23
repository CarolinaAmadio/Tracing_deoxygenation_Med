# Tracing_deoxygenation_Med

Repository for tracing deoxygenation processes in the Mediterranean Sea.

## Repository structure

- `00_build_SUPERFLOAT/`
- `01_calc_clim/`
- `02_analyze_clim/`
- `03_calculate_NN_datasets/`
- `04_doxy_vs_bathy`
- `05_plot_multi_prod_timeseries/`
- `utils/`

## Workflow

The repository follows a sequential workflow:

```text
00_build_SUPERFLOAT --> from a CORIOLIS to a Quality Controlled Dataset (+ statistics in accepted/rejected O2o)
        ↓
01_calc_clim --> yearly and monthly climatologies (+ csv and png)
        ↓
02_analyze_clim --> analysis at depth of timeseries 
        ↓
03_calculate_NN_datasets --> build NN-dervied products (PPCON and CANYONMED)
        ↓
04_doxy_vs_bathy
        ↓
05_plot_multi_prod_timeseries
```

## Documentation

Additional documentation is available in:

- `docs/workflow.md`
- `docs/installation.md`
- `docs/directory_structure.md`
- `docs/outputs.md`
