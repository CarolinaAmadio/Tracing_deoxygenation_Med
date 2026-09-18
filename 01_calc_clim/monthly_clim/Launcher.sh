#!/bin/bash

#SBATCH --job-name=MONclim
#SBATCH -N1 -n 1
#SBATCH --time=01:30:00
##SBATCH --mem=300gb
#SBATCH --account=OGS_test2528
##SBATCH --partition=g100_meteo_prod
#SBATCH --partition=g100_usr_prod
##SBATCH --qos=qos_meteo

#cd "$SLURM_SUBMIT_DIR"

BASEDIR=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med_ISSUE_01
. /${BASEDIR}/utils/profile.inc

echo "Job started at: $(date)"

NAMEDIR=01_calc_clim
WORKDIR=${BASEDIR}/${NAMEDIR}/monthly_clim

source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate
export PYTHONPATH=${BASEDIR}/bit.sea/src:$PYTHONPATH
export ONLINE_REPO=${BASEDIR}/ONLINE
export MASKFILE=/g100_work/OGS_test2528/camadio/Neccton_hindcast_ALL_SIMULATIONS_archieve/Neccton_hindcast1999_2022/wrkdir/MASKS/meshmask.nc

OUTDIR=${WORKDIR}
mkdir -p "$OUTDIR"
OUT=${OUTDIR}/PLOTS

mkdir -p "$OUT" "$OUT/CLIMA_FLOAT" "$OUT/SUPERFLOAT" "$OUT/CORIOLIS" "$OUT/MONTHLY_PROFILES"

#CDOM  and PH_IN_SITU_TOTAL --> only in CORIOLIS only RealTime

#for VARNAME in N3n P_l vosaline votemper PAR pH POC CDOM Ed_490 DOWNWELLING_PAR O2o; do
for VARNAME in PAR; do
    my_prex_or_die "python Month_Climfloat_netcdf_superfloat.py -o $OUT/SUPERFLOAT -v $VARNAME"
    my_prex_or_die "python Month_Climfloat_netcdf_Coriolis.py -o $OUT/CORIOLIS -v $VARNAME"
    my_prex_or_die "python compare_clima_doxy_monthly.py -i $OUT -o $OUT/CLIMA_FLOAT -v $VARNAME"
    my_prex_or_die "python plot_all_months.py --coriolis-dir $OUT/CORIOLIS --superfloat-dir $OUT/SUPERFLOAT --outdir $OUT/MONTHLY_PROFILES --var $VARNAME"
    #my_prex_or_die "python clim_visualizer_html_pdf.py -i $OUT/CLIMA_FLOAT -v $VARNAME"
done

exit 0


OUT=${OUTDIR}/PLOTS/CSV/
mkdir -p $OUT
#for VARNAME in O2o; do
#    my_prex_or_die "python Create_SUBcsv_date_profiles.py -o $OUT -v $VARNAME"
#done

OUT_hov=${OUTDIR}/PLOTS/HOVMOELLER/
mkdir -p $OUT_hov

my_prex_or_die "python plot_Howmoeller.py -i $OUT -o $OUT_hov --year-min 2012 --year-max 2016"

my_prex_or_die "python plot_Howmoeller.py -i $OUT -o $OUT_hov --year-min 2022 --year-max 2026"

DIR1=$OUT_hov/2012_2016
DIR2=$OUT_hov/2022_2026

my_prex_or_die "python plot_Howmoeller_diff.py --dir1 $DIR1 --dir2 $DIR2 --outdir $OUT_hov --sub nwm"

my_prex_or_die "python plot_Howmoeller_diff.py --dir1 $DIR1 --dir2 $DIR2 --outdir $OUT_hov --sub lev2"

exit 0

deactivate
source /g100/home/userexternal/camadio0/envs/py38_seaborn/bin/activate
python create_pdf_monthly_clim.py -i $OUT/MONTHLY_PROFILES

