import argparse
import os

from bitsea.commons.utils import addsep
import numpy as np
import pandas as pd
from bitsea.commons import timerequestors
from bitsea.instruments import superfloat as bio_float
from bitsea.instruments.var_conversions import FLOATVARS
from bitsea.basins import V2 as OGS
from bitsea.basins.basin import ComposedBasin
from bitsea.commons.mask import Mask


def argument():
    parser = argparse.ArgumentParser(description='''
    This script exports interpolated SUPERFLOAT profile CSVs for different Mediterranean sub-basins.
    **Input**: SUPERFLOAT profiles selected for a given variable (--variable) and monthly climatology.
    **Method**: For each sub-basin and month, profiles are interpolated on the model depth levels.
    **Output**:
     - CSV files with interpolated profile data and profile dates as column headers.
    ''', formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('--outdir', '-o',
                        type=str,
                        required=True,
                        help='directory where CSV files are written')

    parser.add_argument('--variable', '-v',
                        type=str,
                        default=None,
                        required=True,
                        help='model variable')
    return parser.parse_args()


args = argument()
OUTDIR = addsep(args.outdir)
os.makedirs(OUTDIR, exist_ok=True)
varmod = args.variable

TheMask = Mask.from_file(os.environ["MASKFILE"])
z_interp = TheMask.zlevels

if OGS.atl in OGS.Pred.basin_list:
    OGS.Pred.basin_list.remove(OGS.atl)

SUBS = OGS.Pred.basin_list[:]
print('_________________start__________________', flush=True)

MONTHS = np.arange(1, 13)

for mm in MONTHS:
    TI = timerequestors.Clim_month(mm)

    for ISUB in SUBS:
        print(f'_____________ {ISUB} _____________', flush=True)

        if ISUB.name == 'ion1':
            isub = ComposedBasin('ion4', [OGS.swm2, OGS.ion2, OGS.tyr2], 'Neighbors of ion1')
            Profilelist = bio_float.FloatSelector(FLOATVARS[varmod], TI, isub)
        elif ISUB.name == 'tyr1':
            isub = ComposedBasin('supertyr', [OGS.tyr2, OGS.tyr1], 'tyr1and2')
            Profilelist = bio_float.FloatSelector(FLOATVARS[varmod], TI, isub)
        else:
            Profilelist = bio_float.FloatSelector(FLOATVARS[varmod], TI, ISUB)

        if not Profilelist:
            continue

        print('number of profiles used', flush=True)
        print(len(Profilelist), flush=True)

        SERV_VAR = np.full((len(Profilelist), len(z_interp)), np.nan, dtype=np.float32)
        date_list = []
        ICONT = 0

        for PROFILE in Profilelist:
            Pres, Profile, Qc = PROFILE.read(var=FLOATVARS[varmod])
            Profile_interp = np.interp(z_interp, Pres, Profile, left=np.nan, right=np.nan)
            SERV_VAR[ICONT, :] = Profile_interp

            date_str = pd.to_datetime(PROFILE.time).strftime('%d-%m-%Y')
            date_list.append(date_str)
            ICONT += 1

        df = pd.DataFrame(SERV_VAR.T, index=z_interp, columns=date_list)
        df.index.name = 'depth_m'

        outfile = os.path.join(OUTDIR, f'{ISUB.name}_{varmod}_{mm:02d}_superfloat.csv')
        df.to_csv(outfile)
        print(f'Wrote {outfile}', flush=True)
