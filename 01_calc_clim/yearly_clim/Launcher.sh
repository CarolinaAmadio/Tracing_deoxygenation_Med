#!/bin/bash

#SBATCH --job-name=YRclim
#SBATCH -N1 -n 1
#SBATCH --time=06:30:00
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

mkdir -p "$OUT" "$OUT/CLIMA_FLOAT" "$OUT/SUPERFLOAT" "$OUT/CORIOLIS"


#CDOM  and PH_IN_SITU_TOTAL --> only in CORIOLIS only RealTime

#for VARNAME in N3n P_l vosaline votemper PAR pH CDOM BBP700 DOWN_IRRADIANCE490 DOWNWELLING_PAR O2o; do


for VARNAME in CDOM BBP700 DOWN_IRRADIANCE490 O2o; do
    my_prex_or_die "python Yr_Climfloat_netcdf_superfloat.py -o $OUT/SUPERFLOAT -v $VARNAME"
    my_prex_or_die "python Yr_Climfloat_netcdf_Coriolis.py -o $OUT/CORIOLIS -v $VARNAME"
    my_prex_or_die "python compare_clima_doxy.py -i $OUT -o $OUT/CLIMA_FLOAT -v $VARNAME"
    my_prex_or_die "python clim_visualizer_html_pdf.py -i $OUT/CLIMA_FLOAT -v $VARNAME"
done

exit 0

deactivate
source /g100/home/userexternal/camadio0/envs/py38_seaborn/bin/activate
python create_pdf.py -i $OUT/CLIMA_FLOAT

