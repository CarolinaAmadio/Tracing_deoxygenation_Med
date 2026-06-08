#!/usr/bin/env python3

import argparse
import pandas as pd

parser = argparse.ArgumentParser(
    description="Create a basin-level DRIFT_CODE summary from Floats_accepted.csv"
)
parser.add_argument(
    "--input_csv",
    type=str,
    nargs="?",
    default="/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/ONLINE/SUPERFLOAT/Floats_accepted.csv",
    help="Path to Floats_accepted.csv",
)
parser.add_argument(
    "--output_csv",
    type=str,
    default="/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/00_build_SUPERFLOAT/drift_summary_by_basin.csv",
    help="Path for the output summary CSV file",
)
args = parser.parse_args()

input_file = args.input_csv
output_file = args.output_csv

df = pd.read_csv(
    input_file,
    dtype={"DRIFT_CODE": str, "basin": str, "WMO": str},
    keep_default_na=True,
    na_values=["", "nan", "NaN"],
)

# Normalize basin and WMO strings
[df["basin"], df["WMO"]] = [
    df["basin"].astype(str).str.strip().str.lower(),
    df["WMO"].astype(str).str.strip(),
]

# Convert DRIFT_CODE to integer and normalize missing/invalid values to -1
df["DRIFT_CODE"] = (
    pd.to_numeric(df["DRIFT_CODE"], errors="coerce")
      .fillna(-1)
      .astype(int)
      .where(lambda x: x.isin([-1, 0, 1]), -1)
)

# Ensure trend values are numeric for averaging later
df["TREND_per_YEAR"] = pd.to_numeric(df.get("TREND_per_YEAR"), errors="coerce")

# Total number of profiles per basin
total_profiles = df.groupby("basin").size().rename("N_PROFILES")

# Count profiles by basin and drift code category
count_report = (
    df.groupby(["basin", "DRIFT_CODE"]).size()
      .unstack(fill_value=0)
      .reindex(columns=[-1, 0, 1], fill_value=0)
      .rename(columns={-1: "NO_CONDITION", 0: "NO_DRIFT", 1: "DRIFT_CAL"})
)

# Compute MAE (mean of absolute drift) and standard deviation for drift-calculation profiles only
drift_df = df[df["DRIFT_CODE"] == 1].copy()

mae_drift = (
    drift_df.groupby("basin")["TREND_per_YEAR"]
      .apply(lambda x: x.abs().mean())
      .rename("MAE_DRIFT")
)

std_drift = (
    drift_df.groupby("basin")["TREND_per_YEAR"]
      .std()
      .rename("STD_DRIFT")
)

# Pool WMO lists for positive and negative drift
positive_wmo = (
    df[(df["DRIFT_CODE"] == 1) & (df["TREND_per_YEAR"] > 0)]
      .groupby("basin")["WMO"]
      .unique()
      .apply(lambda arr: ";".join(sorted(x for x in arr if x and x.lower() != "nan")))
      .rename("WMO_POSITIVE_DRIFT")
)

negative_wmo = (
    df[(df["DRIFT_CODE"] == 1) & (df["TREND_per_YEAR"] < 0)]
      .groupby("basin")["WMO"]
      .unique()
      .apply(lambda arr: ";".join(sorted(x for x in arr if x and x.lower() != "nan")))
      .rename("WMO_NEGATIVE_DRIFT")
)

# Absolute maximum drift and corresponding WMO per basin
abs_max_drift = (
    drift_df.groupby("basin")["TREND_per_YEAR"]
      .apply(lambda x: x.abs().max())
      .rename("ABS_MAX_DRIFT")
)

_abs_max_rows = (
    drift_df.assign(ABS_TREND=drift_df["TREND_per_YEAR"].abs())
      .sort_values("ABS_TREND", ascending=False)
      .drop_duplicates(subset="basin")
      .set_index("basin")
)

abs_max_drift_wmo = _abs_max_rows["WMO"].rename("ABS_MAX_DRIFT_WMO")

abs_max_drift_cycle = (
    pd.to_numeric(_abs_max_rows["cycle"], errors="coerce")
      .rename("ABS_MAX_DRIFT_CYCLE")
)

report = (
    total_profiles
      .to_frame()
      .join(count_report)
      .join(mae_drift)
      .join(std_drift)
      .join(abs_max_drift)
      .join(abs_max_drift_wmo)
      .join(abs_max_drift_cycle)
      .join(positive_wmo)
      .join(negative_wmo)
      .fillna("")
)

# Insert DRIFT_CAL_PCT (%) after DRIFT_CAL
drift_cal_idx = report.columns.get_loc("DRIFT_CAL") + 1
report.insert(drift_cal_idx, "DRIFT_CAL_PCT",
              (report["DRIFT_CAL"].apply(pd.to_numeric, errors="coerce") /
               report["N_PROFILES"].apply(pd.to_numeric, errors="coerce") * 100
              ).round(1))

BASIN_ORDER = [
    "alb", "swm1", "swm2", "nwm",
    "tyr1", "tyr2",
    "adr1", "adr2",
    "aeg",
    "ion1", "ion2", "ion3",
    "lev1", "lev2", "lev3", "lev4",
]
report = report.reindex([b for b in BASIN_ORDER if b in report.index])

report.to_csv(output_file, index=True)
print(f"Saved basin drift summary to {output_file}")
