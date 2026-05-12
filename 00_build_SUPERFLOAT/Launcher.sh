#!/bin/bash

#SBATCH --job-name=fix_qc
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

WORKDIR=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/00_new_SUPERFLOAT/

VARNAME='O2o'   # O2o:DOX
DATE_start=19990101
DATE_end=20261231

source /g100_work/OGS23_PRACE_IT/COPERNICUS/py_env_3.9.18_new/bin/activate
export ONLINE_REPO=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/ONLINE/

# preparo il dataset
export PYTHONPATH=$WORKDIR/bit.sea/src
OUTDIR=/g100_scratch/userexternal/camadio0/Tracing_deoxygenation_Med/ONLINE/SUPERFLOAT/
mkdir -p $OUTDIR

cd $WORKDIR/bit.sea/src/bitsea/Float/ || exit 1
#my_prex "python superfloat_chla.py -s $DATE_start -e $DATE_end -o $OUTDIR -f"
#my_prex "python superfloat_oxygen.py  -s $DATE_start -e $DATE_end -o $OUTDIR -O $OUTDIR -f"
#my_prex "python superfloat_nitrate.py -s $DATE_start -e $DATE_end -o $OUTDIR -f"
#my_prex "python superfloat_par.py -s $DATE_start -e $DATE_end -o $OUTDIR -f"
my_prex "python superfloat_ph.py -s $DATE_start -e $DATE_end -o $OUTDIR -f"
my_prex "python superfloat_bbp700.py -s $DATE_start -e $DATE_end -o $OUTDIR -f"
my_prex "python superfloat_kd490.py -s $DATE_start -e $DATE_end -o $OUTDIR -f"
my_prex "python dump_index.py -i $OUTDIR -o ${OUTDIR}/Float_Index.txt -t superfloat" 
exit 0


exit 0
## plot figs 
cd $SLURM_SUBMIT_DIR
for NAME_TEST in fix_qc; do
#for NAME_TEST in master fix_qc to_test; do
	OUTDIR_fig=DOXY_FIGS_$NAME_TEST/
	mkdir -p $OUTDIR_fig
	
	OUTDIR=$WORKDIR/ONLINE/SUPERFLOAT_$NAME_TEST/
	ln -s $OUTDIR $WORKDIR/ONLINE/SUPERFLOAT
	my_prex "python -u timeseries_at_depth.py -o $OUTDIR_fig -v $VARNAME"
	rm $WORKDIR/ONLINE/SUPERFLOAT
done


echo "Job end at: $(date)"	
#python single_float_comparison_cor_superf.py
