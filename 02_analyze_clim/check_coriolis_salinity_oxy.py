#!/usr/bin/env python3
#import argparse
import os
import sys

import gsw
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from bitsea.basins import V2 as OGS
from bitsea.commons import timerequestors
from bitsea.instruments import bio_float
from bitsea.instruments.var_conversions import FLOATVARS

sys.path.append(os.path.abspath(".."))
from utils.basins_CA_new_bitsea import cross_Med_basins

def read_temp_psal(p):
    pres_t, temp, _ = p.read('TEMP')
    pres_s, sal, _ = p.read('PSAL')
    if (pres_t is None or temp is None or pres_s is None or sal is None
            or len(pres_t) < 5 or len(pres_s) < 5):
        pres_t, temp, _ = p.read('TEMP', read_adjusted=False)
        pres_s, sal, _ = p.read('PSAL', read_adjusted=False)
    return pres_t, temp, pres_s, sal

#parser = argparse.ArgumentParser(description='Ad hoc check for CORIOLIS float 6903266 cycle 341.')
#parser.add_argument('-o', '--outdir', required=True, help='Output directory.')
#args = parser.parse_args()

#OUTDIR = args.outdir
#os.makedirs(OUTDIR, exist_ok=True)

if OGS.atl in OGS.Pred.basin_list:
    OGS.Pred.basin_list.remove(OGS.atl)
SUBS = OGS.Pred.basin_list[:]

TI = timerequestors.TimeInterval(
    starttime='19500101',
    endtime='20280101',
    dateformat='%Y%m%d',
)

target_wmo = '6903266'
target_cycle = 341
profile = None

for basin in SUBS:
    for p in bio_float.FloatSelector(FLOATVARS['O2o'], TI, basin):
        if str(p._my_float.wmo) == target_wmo and int(p._my_float.cycle) == target_cycle:
            profile = p
            break
    if profile is not None:
        break

if profile is None:
    raise SystemExit(f'Profile {target_wmo} cycle {target_cycle} not found.')

pres_o, oxy_o, _ = profile.read(FLOATVARS['O2o'])
pres_t, temp, pres_s, sal = read_temp_psal(profile)

if len(pres_t) != len(sal):
    sal = np.interp(pres_t, pres_s, sal)
    pres_s = pres_t

if len(temp) != len(pres_o):
    temp = np.interp(pres_o, pres_t, temp)
if len(sal) != len(pres_o):
    sal = np.interp(pres_o, pres_s, sal)

pres_o = np.asarray(pres_o, dtype=float)
temp = np.asarray(temp, dtype=float)
sal = np.asarray(sal, dtype=float)
oxy_o = np.asarray(oxy_o, dtype=float)

sa = gsw.SA_from_SP(sal, pres_o, profile.lon, profile.lat)
ct = gsw.CT_from_t(sa, temp, pres_o)
rho = gsw.rho(sa, ct, pres_o)
oxy_orig = oxy_o * rho / 1000.0

sal_39 = np.full_like(sal, 39.0)
sa2 = gsw.SA_from_SP(sal_39, pres_o, profile.lon, profile.lat)
ct2 = gsw.CT_from_t(sa2, temp, pres_o)
rho2 = gsw.rho(sa2, ct2, pres_o)
oxy_39 = oxy_o * rho2 / 1000.0

df = pd.DataFrame({
    'pres': pres_o,
    'temp': temp,
    'sal_orig': sal,
    'oxy_orig_mmol_m3': oxy_orig,
    'sal_39': sal_39,
    'oxy_39_mmol_m3': oxy_39,
})
#df.to_csv(os.path.join(OUTDIR, 'profile_6903266_341_compare.csv'), index=False)

fig, ax = plt.subplots(figsize=(6, 8))
ax.plot(oxy_orig, pres_o, label='original salinity')
ax.plot(oxy_39, pres_o, label='salinity 39 psu')
ax.invert_yaxis()
ax.set_xlabel('Oxygen (mmol/m³)')
ax.set_ylabel('Pressure / depth')
ax.legend()
#fig.savefig(os.path.join(OUTDIR, 'profile_6903266_341_compare.png'), bbox_inches='tight')
