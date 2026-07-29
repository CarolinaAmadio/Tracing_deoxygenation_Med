### Oxygen drift-correction pipeline (`superfloat_oxygen.py`)

Quality control and drift correction of dissolved-oxygen (DOXY) BGC-Argo
profiles are performed by
`bit.sea/src/bitsea/Float/superfloat_oxygen.py`, called from `Launcher.sh`.

**Algorithm (per BGC-Argo float, WMO):**
1. Interpolate DOXY at 600m and 800m (±20m) over the **entire** history of the float.
2. If the series spans **≥ 1 year**, fit Theil-Sen and RANSAC regressors at each
   depth on real elapsed time (`compute_float_trend`).
3. Classify the float using its annual drift rate (`TREND_per_YEAR`, mmol/m³/yr):
   - `< 2` → not significant, no correction (`DRIFT_CODE=0`)
   - `2 - 10` → drift correction applied (`DRIFT_CODE=1`)
   - `> 10` → anomalous drift, float rejected entirely (`DRIFT_CODE=-2`)
   - inconsistent sign / insufficient data → `DRIFT_CODE=-1`
4. For `DRIFT_CODE=1`, the correction is applied **progressively**: it grows
   linearly with time elapsed since the float's first profile, ramped from 0
   at the surface to the full value at 600m, then held constant below 600m.
5. Each profile is additionally validated against the EMODNET climatology of
   its Mediterranean sub-basin (`clim_check`); profiles whose offset exceeds
   `2 x stdev` (floored at 15) are rejected regardless of the drift outcome.
6. Optional diagnostic plots (enabled by default, `--make_plots`/`--no-make_plots`)
   compare the raw O2 timeseries (red) with the corrected QC_O2 timeseries
   (blue) at 600m/800m, saved to `PLOTS_DRIFT/<wmo>.png`.

**Per-profile report files** (written under the `-O/--outdiag` directory):

| File | Granularity | Content |
|---|---|---|
| `Floats_trend_by_wmo.csv` | one row per WMO | drift rate, estimators, `DRIFT_CODE` for the whole float |
| `Floats_accepted.csv` | one row per accepted profile | basin, `DRIFT_CODE`, `TREND_per_YEAR`, applied correction, climatology offset |
| `Floats_rejected.csv` | one row per rejected profile/float | `reject_reason` (`climatology_offset`, `drift_too_high`, `NoClimValue`) |
| `DataMode_and_Saturation_rejection_doxy.csv` | one row per rejected profile | upstream QC rejections (realtime status, missing data, saturation test) |

**Basin-level summary scripts** (aggregate the per-profile reports above by
Mediterranean sub-basin):
- `accepted_summary_by_basin.py` → `drift_summary_by_basin.csv`: counts of
  profiles by `DRIFT_CODE`, mean/std of the applied drift, floats with the
  strongest positive/negative drift.
- `rejection_summary_by_basin.py` → `rejection_summary_by_basin.csv`: counts
  of rejected/accepted profiles by basin, split by rejection cause (`RT`,
  `Saturation`, `PresNone`, `Clim_QC`, `Drift_too_high`, `NoClimValue`).
