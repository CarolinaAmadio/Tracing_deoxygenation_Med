#!/bin/bash

#SBATCH --job-name=NN_Argopy
#SBATCH -N1 
#SBATCH --ntasks-per-node=16
#SBATCH --time=0:30:00
#SBATCH --mem=300gb
#SBATCH --account=OGS_test2528
#SBATCH --partition=g100_meteo_prod
#SBATCH --qos=qos_meteo

cd $SLURM_SUBMIT_DIR
. /g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/utils/profile.inc

echo "Job started at: $(date)"

# Activate the Python virtual environment
#source /g100/home/userexternal/camadio0/envs/py38_seaborn/bin/activate
source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate
export PYTHONPATH=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/bit.sea/src:$PYTHONPATH
export ONLINE_REPO=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/ONLINE/

OUTDIR=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/1_clim_analysis/DOXY_at_600m

mkdir -p $OUTDIR
python -u timeseries_at_depth.py -o $OUTDIR -v O2o
#python -u timeseries_at_depth_subplot.py -o $OUTDIR -v O2o

#python test.py 
