#!/bin/bash

#SBATCH --job-name=04doxy
#SBATCH -N1 
#SBATCH --ntasks-per-node=16
#SBATCH --time=0:50:00
#SBATCH --mem=300gb
#SBATCH --account=OGS_test2528
#SBATCH --partition=g100_meteo_prod
#SBATCH --qos=qos_meteo


echo "Job started at: $(date)"

WORKDIR=04_doxy_vs_bathy
#source /g100/home/userexternal/camadio0/envs/py38_seaborn/bin/activate
source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate
export PYTHONPATH=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/bit.sea/src:$PYTHONPATH
export ONLINE_REPO=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/ONLINE/
OUTDIR=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/$WORKDIR/plots/

MASKFILE=/g100_work/OGS_test2528/camadio/Neccton_hindcast_ALL_SIMULATIONS_archieve/Neccton_hindcast1999_2022/wrkdir/MASKS/meshmask.nc

mkdir -p $OUTDIR $OUTDIR/Spatial_analysis $OUTDIR/Temporal_analysis
# 00 --> calcolo i csv no plots
#python -u 00_calculate_bathy_and_floatlife.py -o $OUTDIR -v O2o -m $MASKFILE #--basin alb

# 01 --> plots of bathy med
#python -u 01_plot_bathy_medsea.py -o $OUTDIR/Spatial_analysis  -m $MASKFILE

# 02 --> plot o2 vs trend
mkdir -p $OUTDIR/Spatial_analysis
deactivate 
source /g100/home/userexternal/camadio0/envs/py38_seaborn/bin/activate
#python -u 02_plot_basins_value_bathy_trend.py -i $OUTDIR -o $OUTDIR/Spatial_analysis # --basin alb

#exit 0

# 03 --> plot o2 vs float lifetime
#python -u 03_plot_basins_oxy_duration_subsets.py -p $OUTDIR -o $OUTDIR/Temporal_analysis #--basin alb  

# 04 GAM analysis
mkdir -p $OUTDIR/GAM/
python -u 04_GAM_model.py -p $OUTDIR -o $OUTDIR/GAM/ --basin alb   

echo "Job end  at: $(date)"


