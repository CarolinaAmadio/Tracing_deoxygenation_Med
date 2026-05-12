#!/bin/bash

#SBATCH --job-name=buildCANYON
#SBATCH -N1 
#SBATCH --ntasks-per-node=16
#SBATCH --time=1:30:00
#SBATCH --mem=300gb
#SBATCH --account=OGS_test2528
#SBATCH --partition=g100_meteo_prod
#SBATCH --qos=qos_meteo

cd $SLURM_SUBMIT_DIR
. /g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/utils/profile.inc

echo "Job started at: $(date)"

source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate
export ONLINE_REPO=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/ONLINE/


CORIOLIS=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/ONLINE/CORIOLIS/
INPUTDIR=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/2_calc_canyon/SUPERFLOAT/
OUTDIR=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/2_calc_canyon/CANYON_MED_QC/
mkdir -p $OUTDIR

my_prex_or_die "python -u prova_tmp.py -i $INPUTDIR -o $OUTDIR -c $CORIOLIS"

deactivate
source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate
export ONLINE_REPO=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/ONLINE/

cp -r $INPUTDIR/Float_index.txt $OUTDIR/
my_prex_or_die "python dump_index_canyonmed.py -i $OUTDIR -o ${OUTDIR}/Float_Index.txt -t canyonmed_float"
echo "Job finished at: $(date)"

