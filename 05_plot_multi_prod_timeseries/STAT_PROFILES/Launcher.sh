#!/bin/bash

#SBATCH --job-name=timeseries_stat_profile
#SBATCH -N1
#SBATCH --ntasks-per-node=16
#SBATCH --time=00:30:00
#SBATCH --mem=300gb
#SBATCH --account=OGS_test2528
#SBATCH --partition=g100_meteo_prod
#SBATCH --qos=qos_meteo

input_base=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/5_validation/STAT_PROFILES/
#. /g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/utils/profile.inc
source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate

echo "Job started at: $(date)"

variables=(ALK DIC pH pCO2 O2o)
#variables=(ALK)
cases=(V12C V13C RA QUID_V13C_dasatfloat)
#cases=(QUID_V13C_dasatfloat)
coast="coast"
stat="Mean"
min_depth=0
max_depth=10

depth_tag="${min_depth}-${max_depth}m_${coast}"

for var in "${variables[@]}"; do
  for case in "${cases[@]}"; do
    input_file="${input_base}/${case}/${var}.pkl"
    if [[ ! -f "${input_file}" ]]; then
      echo "WARNING: file mancante ${input_file}, skip"
      continue
    fi

    output_dir="${input_base}/${depth_tag}/${case}"
    mkdir -p "${output_dir}"
    output_file="${output_dir}/${case}_${var}.layer_${min_depth}_${max_depth}m.${stat}.csv"

    echo "Processing ${input_file} var=${var} where=${coast} stat=${stat}"
    python timeseries_at_surface_stat_profile.py \
      --input-file "${input_file}" \
      --output-file "${output_file}" \
      --var "${var}" \
      --coast "${coast}" \
      --stat "${stat}" \
      --min-depth "${min_depth}" \
      --max-depth "${max_depth}"
  done
done

echo "Job ended at: $(date)"
