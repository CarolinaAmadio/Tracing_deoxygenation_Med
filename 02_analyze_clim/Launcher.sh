#!/bin/bash

#SBATCH --job-name=02_analyze_clim
#SBATCH -N1 
#SBATCH --ntasks-per-node=16
#SBATCH --time=0:50:00
#SBATCH --mem=300gb
#SBATCH --account=OGS_test2528
#SBATCH --partition=g100_meteo_prod
#SBATCH --qos=qos_meteo

#cd "$SLURM_SUBMIT_DIR"
#. ${BASEDIR:-/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med_ISSUE_01}/utils/profile.inc

echo "Job started at: $(date)"

BASEDIR=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med_ISSUE_01
NAMEDIR=02_analyze_clim
WORKDIR=${BASEDIR}/${NAMEDIR}

# Activate the Python virtual environment
#source /g100/home/userexternal/camadio0/envs/py38_seaborn/bin/activate
source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate
export PYTHONPATH=${BASEDIR}/bit.sea/src:$PYTHONPATH
export ONLINE_REPO=${BASEDIR}/ONLINE
export MASKFILE=/g100_work/OGS_test2528/camadio/Neccton_hindcast_ALL_SIMULATIONS_archieve/Neccton_hindcast1999_2022/wrkdir/MASKS/meshmask.nc

# hardcoded at 600m
for VAR in O2o N3n; do
	OUTDIR=${WORKDIR}/PLOTS/${VAR}
	mkdir -p "$OUTDIR"
	#python -u timeseries_at_depth.py -o "$OUTDIR/timeseries_at_depth/" -v $VAR  #  plots con dati a 600m coriolis and superfloat
	#python -u timeseries_qc_pres_sal_rho_line_trend.py -o "$OUTDIR/timeseries_qc_pres_sal_rho_line_trend/" -v $VAR
done 

for DEPTH in 25 100; do
    for VAR in P_l; do 
	mkdir -p ${WORKDIR}/PLOTS/${VAR}_at_${DEPTH}    
        python -u timeseries_layer.py --depth $DEPTH --variable $VAR --outdir ${WORKDIR}/PLOTS/${VAR}_at_${DEPTH}m
    done
done

exit 0

exit 0 

OUTDIR=${WORKDIR}/PLOTS/Hov/
source /g100/home/userexternal/camadio0/envs/py38_seaborn/bin/activate
python Hovmoeller_temp_sal_rho_doxy.py -o "$OUTDIR" #--basin alb

python create_pdf_hovmoeller.py -i "$OUTDIR/" -d superfloat -o "$OUTDIR/all_basins_superfloat.pdf"

echo "Job end  at: $(date)"

