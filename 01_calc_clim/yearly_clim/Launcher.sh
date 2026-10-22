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

mkdir -p "$OUT" "$OUT/CLIMA_FLOAT" "$OUT/SUPERFLOAT" "$OUT/CORIOLIS"

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
# PAR                           X
# vosaline                      X
# votemper                      X
# DOWNWELLING_PAR               X
# Ed_490                        X
#
# Special cases:
# CDOM, PH_IN_SITU_TOTAL: BGC-Argo profiles available only from
# CORIOLIS in Real-Time mode.
# NH4 only emodnet
# https://docs.google.com/presentation/d/1tWnbnaO2rNb7gRKagPhm4MSdvIYfrdUSlJ5ro0UZ3fI/edit?slide=id.h7cec62ed0095a4c5_11_25#slide=id.h7cec62ed0095a4c5_11_25

mkdir -p $OUT/SUPERFLOAT/
for VARNAME in N3n P_l POC vosaline votemper PAR Ed_490 DOWNWELLING_PAR O2o; do
    my_prex_or_die "python Yr_Climfloat_netcdf_superfloat.py -o $OUT/SUPERFLOAT -v $VARNAME"
    #my_prex_or_die "python compare_clima_doxy.py -i $OUT -o $OUT/CLIMA_FLOAT -v $VARNAME"
    #my_prex_or_die "python clim_visualizer_html_pdf.py -i $OUT/CLIMA_FLOAT -v $VARNAME"
done

mkdir -p $OUT/PPCON/
for VARNAME in N3n P_l POC; do # P_l POC; do
    my_prex_or_die "python Yr_Climfloat_netcdf_ppcon.py -o $OUT/PPCON -v $VARNAME"
done

#exit 0

#mkdir -p $OUT/CANYONMED/
#for VARNAME in N1p DIC N5s ALK pH; do
#for VARNAME in N3n; do
#    my_prex_or_die "python Yr_Climfloat_netcdf_canyonmed.py -o $OUT/CANYONMED/ -v $VARNAME"
#done

#exit 0
	
mkdir -p $OUT/CLIMA_FLOAT_NEW/
for VARNAME in P_l O2o POC; do
    #my_prex_or_die "python compare_climatologies.py -i $OUT -o $OUT/CLIMA_FLOAT_NEW/ -v $VARNAME"
    my_prex_or_die "python clim_visualizer_html_pdf.py -i $OUT/CLIMA_FLOAT_NEW/ -v $VARNAME"
done


exit 0

deactivate
source /g100/home/userexternal/camadio0/envs/py38_seaborn/bin/activate
python create_pdf.py -i $OUT/CLIMA_FLOAT

