#!/bin/bash

#SBATCH --job-name=YRclim
#SBATCH -N1 -n 1
#SBATCH --time=00:30:00
#SBATCH --mem=300gb
#SBATCH --account=OGS_test2528
#SBATCH --partition=g100_meteo_prod
#SBATCH --qos=qos_meteo

#cd $SLURM_SUBMIT_DIR
#. /g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/utils/profile.inc 

echo "Job started at: $(date)"

source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate
export PYTHONPATH=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/00_new_SUPERFLOAT/bit.sea/src:$PYTHONPATH
export ONLINE_REPO=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/ONLINE/

INDIR=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/ONLINE/SUPERFLOAT/
OUTDIR=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/0_clim_calc/float_stat.csv

python rejection_summary_by_basin.py -i $INDIR -o $OUTDIR 
