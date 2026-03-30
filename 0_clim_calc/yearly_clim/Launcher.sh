#!/bin/bash

#SBATCH --job-name=YRclim
#SBATCH -N1 -n 1
#SBATCH --time=3:30:00
#SBATCH --mem=300gb
#SBATCH --account=OGS_test2528
#SBATCH --partition=g100_meteo_prod
#SBATCH --qos=qos_meteo

cd $SLURM_SUBMIT_DIR
. /g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/0_clim_calc/utils/profile.inc 

echo "Job started at: $(date)"

source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate
export PYTHONPATH=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/bit.sea/src:$PYTHONPATH
export ONLINE_REPO=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/ONLINE/

OUTDIR=
/g100_scratch/userexternal/camadio0/ARGOPY_TESTS/Climatologies_Argopy/bitsea_complement/CLIMATOLOGIES/SUPERFLOAT/

mkdir -p $OUTDIR $OUTDIR/FILES_and_FIGS $OUTDIR/CLIMAfloat/

OUT=$OUTDIR/FILES_and_FIGS/DOXY/
mkdir -p $OUT/CLIMA_FLOAT

for VARNAME in O2o; do
    my_prex_or_die "python Yr_Climfloat_netcdf_superfloat.py -o $OUT/SUPERFLOAT/ -v $VARNAME"
    my_prex_or_die "python Yr_Climfloat_netcdf_Coriolis.py -o $OUT/CORIOLIS/ -v $VARNAME"
    my_prex_or_die "python compare_clima_doxy.py -i $OUT/ -o $OUT/CLIMA_FLOAT/ -v $VARNAME"
    my_prex_or_die "python clim_visualizer_html_pdf.py -i $OUT/CLIMA_FLOAT/ -v $VARNAME"
    python test.py -i $OUT/CLIMA_FLOAT/
done


deactivate
source /g100/home/userexternal/camadio0/envs/py38_seaborn/bin/activate
for VARNAME in O2o; do
    python clim_visualizer_html_pdf.py -i $OUTDIR/CLIMAfloat/ -v $VARNAME
done
python test.py -i $OUT/CLIMA_FLOAT/

