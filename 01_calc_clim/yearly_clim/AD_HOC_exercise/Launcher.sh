#!/bin/bash

#SBATCH --job-name=YRclim
#SBATCH -N1 -n 1
#SBATCH --time=01:30:00
##SBATCH --mem=300gb
#SBATCH --account=OGS_test2528
##SBATCH --partition=g100_meteo_prod
#SBATCH --partition=g100_usr_prod
##SBATCH --qos=qos_meteo

#cd "$SLURM_SUBMIT_DIR"
. ${BASEDIR:-/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med_ISSUE_01}/utils/profile.inc

echo "Job started at: $(date)"

BASEDIR=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med_ISSUE_01
NAMEDIR=01_calc_clim
WORKDIR=${BASEDIR}/${NAMEDIR}/yearly_clim

source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate
export PYTHONPATH=${BASEDIR}/bit.sea/src:$PYTHONPATH
export ONLINE_REPO=${BASEDIR}/ONLINE
export MASKFILE=/g100_work/OGS_test2528/camadio/Neccton_hindcast_ALL_SIMULATIONS_archieve/Neccton_hindcast1999_2022/wrkdir/MASKS/meshmask.nc 

OUTDIR=${WORKDIR}
mkdir -p "$OUTDIR"
OUT=${OUTDIR}/PLOTS
DATESTART=20210301
DATEEND=20280101
SUB=swm1
VAR='O2o'

mkdir -p CLIM_SUB
#my_prex_or_die "python Yr_Climfloat_netcdf_superfloat_single_year.py -o CLIM_SUB -v $VAR --sub $SUB"
#echo my_prex_or_die "python compare_clima_vfinal.py -i CLIM_SUB -o CLIM_SUB -v $VAR"

python clim_visualizer_html_pdf.py -i /g100_work/OGS_test2528/internal-validation/pub/camadio/BGC_ARGO_CLIM/SUPERFLOAT_DATASET/O2o/period/ -v O2o

python clim_visualizer_html_pdf.py -i /g100_work/OGS_test2528/internal-validation/pub/camadio/BGC_ARGO_CLIM/SUPERFLOAT_DATASET/O2o/all_yrs/ -v O2o

exit 0
