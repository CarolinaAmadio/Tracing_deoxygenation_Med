#!/bin/bash

#SBATCH --job-name=Seasclim
#SBATCH -N1 -n 1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:40:00
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
WORKDIR=${BASEDIR}/${NAMEDIR}/seasonal_clim/

source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate
export PYTHONPATH=${BASEDIR}/bit.sea/src:$PYTHONPATH
export ONLINE_REPO=${BASEDIR}/ONLINE
export MASKFILE=/g100_work/OGS_test2528/camadio/Neccton_hindcast_ALL_SIMULATIONS_archieve/Neccton_hindcast1999_2022/wrkdir/MASKS/meshmask.nc 

OUTDIR=${WORKDIR}
mkdir -p "$OUTDIR"
OUT=${OUTDIR}/PLOTS

mkdir -p "$OUT" "$OUT/CLIMA_FLOAT" "$OUT/SUPERFLOAT" 

# Variable availability by data product
#
# Variable              SAT  BGC-ARGO  EMODNET  PPCON  CANYONMED
# --------------------------------------------------------------
# O2o                           X        X
# CHLA                   X      X        X       X
# N3N                           X        X       X       X
# POC                           X                X       X
# N1p                                    X               X
# DIC                                    X               X
# N5s                                    X               X
# ALK                                    X               X
# pH                                     X               X
# vosaline                      X
# votemper                      X
# DOWNWELLING_PAR               X
# DOWN_IRRADIANCE490            X
# Ed_490                        X
#
# Special cases:
# CDOM, PH_IN_SITU_TOTAL: BGC-Argo profiles available only from
# CORIOLIS in Real-Time mode.
# NH4 only emodnet
# https://docs.google.com/presentation/d/1tWnbnaO2rNb7gRKagPhm4MSdvIYfrdUSlJ5ro0UZ3fI/edit?slide=id.h7cec62ed0095a4c5_11_25#slide=id.h7cec62ed0095a4c5_11_25

mkdir -p $OUT/SUPERFLOAT/ $OUT/SUPERFLOAT/CSV $OUT/SUPERFLOAT/PNG
#for VARNAME in O2o N3n P_l POC vosaline votemper PAR Ed_490; do
#for VARNAME in N3n; do
    #my_prex_or_die "python \"$WORKDIR/Seasonal_Climfloat_netcdf_superfloat.py\" -o \"$OUT/SUPERFLOAT\" -v \"$VARNAME\" -w ${SLURM_CPUS_PER_TASK:-1}"
    #my_prex_or_die "python clim_visualizer_html_pdf.py -i $OUT/CLIMA_FLOAT -v $VARNAME"
#done


#mv $OUT/SUPERFLOAT/*csv  $OUT/SUPERFLOAT/CSV/ 
#mv $OUT/SUPERFLOAT/*png  $OUT/SUPERFLOAT/PNG

#exit 0

mkdir -p $OUT/PPCON/ $OUT/PPCON/CSV $OUT/PPCON/PNG
for VARNAME in N3n P_l POC; do # P_l POC; do
#for VARNAME in POC; do
    my_prex_or_die "python Seasonal_Climfloat_netcdf_ppcon.py -o $OUT/PPCON -v $VARNAME -w ${SLURM_CPUS_PER_TASK:-8}"
done

mv $OUT/PPCON/*csv  $OUT/PPCON/CSV/
mv $OUT/PPCON/*png  $OUT/PPCON/PNG/


mkdir -p $OUT/CANYONMED/ $OUT/CANYONMED/CSV $OUT/CANYONMED/PNG
for VARNAME in N3n N1p DIC N5s ALK pH; do
#for VARNAME in N3n; do
    my_prex_or_die "python Seasonal_Climfloat_netcdf_canyonmed.py -o $OUT/CANYONMED/ -v $VARNAME -w ${SLURM_CPUS_PER_TASK:-8}"
done

mv $OUT/CANYONMED/*csv  $OUT/CANYONMED/CSV/
mv $OUT/CANYONMED/*png  $OUT/CANYONMED/PNG/

exit 0

OUT_1=$OUT/CLIMA_FLOAT/
mkdir -p $OUT_1
for VARNAME in P_l O2o POC; do
#for VARNAME in N3n N1p DIC N5s ALK pH; do
#for VARNAME in POC; do
    my_prex_or_die "python compare_climatologies.py -i $OUT -o $OUT_1 -v $VARNAME"
    #my_prex_or_die "python clim_visualizer_html_pdf.py -i $OUT_1/ -v $VARNAME"
done


exit 0

deactivate
source /g100/home/userexternal/camadio0/envs/py38_seaborn/bin/activate
python create_pdf.py -i $OUT/CLIMA_FLOAT
