import argparse
import os
import pandas as pd
from bitsea.basins import V2 as OGS
from bitsea.commons.utils import addsep


def argument():
    parser = argparse.ArgumentParser(
        description='Create a rejection summary table by basin for SUPERFLOAT quality checks.')
    parser.add_argument('--indir', '-i',
                        type=str,
                        default='/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/ONLINE/SUPERFLOAT/',
                        help='Input directory containing Floats_rejected.csv, Floats_accepted.csv, DataMode_and_Saturation_rejection_doxy.csv')
    parser.add_argument('--out', '-o',
                        type=str,
                        default='/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/0_clim_calc/rejection_summary_by_basin.csv',
                        help='Output CSV file path')
    return parser.parse_args()


def read_csv_safe(path, required_columns):
    df = pd.read_csv(path, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    for col in required_columns:
        if col not in df.columns:
            df[col] = pd.NA
    return df


def normalize_string_series(series):
    return series.fillna('').astype(str).str.strip().str.lower()


def count_reason(df, basin_name, reason_key):
    basin_mask = normalize_string_series(df['basin']) == basin_name.strip().lower()
    reason_mask = normalize_string_series(df['reasons']) == reason_key.strip().lower()
    return int((basin_mask & reason_mask).sum())


def main():
    args = argument()
    indir = addsep(args.indir)
    out_csv = args.out

    rejected_path = os.path.join(indir, 'Floats_rejected.csv')
    accepted_path = os.path.join(indir, 'Floats_accepted.csv')
    reasons_path = os.path.join(indir, 'DataMode_and_Saturation_rejection_doxy.csv')

    for path in (rejected_path, accepted_path, reasons_path):
        if not os.path.exists(path):
            raise FileNotFoundError(f'Input file not found: {path}')

    df_rej = read_csv_safe(rejected_path, ['basin'])
    df_acc = read_csv_safe(accepted_path, ['basin'])
    df_reasons = read_csv_safe(reasons_path, ['basin', 'reasons'])

    basins = [sub.name for sub in OGS.Pred.basin_list if 'atl' not in sub.name]

    summary = []
    for basin_name in basins:
        basin_key = basin_name.strip().lower()

        rej_sub = df_rej[normalize_string_series(df_rej['basin']) == basin_key]
        acc_sub = df_acc[normalize_string_series(df_acc['basin']) == basin_key]

        row = {
            'basin': basin_name,
            'RT': count_reason(df_reasons, basin_name, 'RT'),
            'Saturation': count_reason(df_reasons, basin_name, 'SaturationTest'),
            'PresNone': count_reason(df_reasons, basin_name, 'PresNone'),
            'Clim_QC': int(len(rej_sub)),
            'Accepted': int(len(acc_sub)),
        }
        summary.append(row)

    out_df = pd.DataFrame(summary).set_index('basin')
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    out_df.to_csv(out_csv, index=True)

    print(f'Saved summary to: {out_csv}')
    print(out_df)


if __name__ == '__main__':
    main()
