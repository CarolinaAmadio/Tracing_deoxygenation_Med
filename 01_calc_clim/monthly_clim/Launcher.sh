#!/bin/bash

#SBATCH --job-name=MONclim
#SBATCH -N1 -n 1
#SBATCH --time=1:30:00
#SBATCH --mem=300gb
#SBATCH --account=OGS_test2528
#SBATCH --partition=g100_meteo_prod
#SBATCH --qos=qos_meteo

#cd $SLURM_SUBMIT_DIR
. /g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/utils/profile.inc 

echo "Job started at: $(date)"

source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate
export PYTHONPATH=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/00_new_SUPERFLOAT/bit.sea/src:$PYTHONPATH
export ONLINE_REPO=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/ONLINE/

OUTDIR=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/0_clim_calc/monthly_clim/
mkdir -p $OUTDIR
OUT=$OUTDIR/plots/ 

mkdir -p $OUT/ $OUT/CLIMA_FLOAT/ $OUT/SUPERFLOAT/ $OUT/CORIOLIS/

for VARNAME in O2o; do
    #my_prex_or_die "python Month_Climfloat_netcdf_Coriolis.py -o $OUT/CORIOLIS/ -v $VARNAME"
    #my_prex_or_die "python Month_Climfloat_netcdf_superfloat.py -o $OUT/SUPERFLOAT/ -v $VARNAME"
    #my_prex_or_die "python compare_clima_doxy_monthly.py -i $OUT/ -o $OUT/CLIMA_FLOAT/ -v $VARNAME --noqc"
    my_prex_or_die "python plot_all_months.py --coriolis-dir plots/CORIOLIS --superfloat-dir plots/SUPERFLOAT  --outdir plots/MONTHLY_PROFILES"
    #my_prex_or_die "python clim_visualizer_html_pdf.py -i $OUT/CLIMA_FLOAT/ -v $VARNAME"
done

exit 0


deactivate
source /g100/home/userexternal/camadio0/envs/py38_seaborn/bin/activate
#python create_pdf.py -i $OUT/CLIMA_FLOAT/
python create_pdf_monthly_clim.py -i plots/CLIMA_FLOAT/

