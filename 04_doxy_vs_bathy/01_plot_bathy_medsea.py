import argparse

def argument():
    parser = argparse.ArgumentParser(description = '''
    plot of bathy of a meshmask.
    Input:  Model meshmask.nc
    Output: png 

    Method: using bitsea 
    ''', formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(   '--outdir','-o',
                                type = str,
                                required = True,
                                help = 'input dir validation tmp')

    parser.add_argument(   '--maskfile', '-m',
                                type = str,
                                default = None,
                                required = True,
                                help = '''model mask''')
    return parser.parse_args()
args = argument()

from bitsea.commons.utils import addsep
import numpy as np
import matplotlib.pyplot as plt
from bitsea.commons.mask import Mask
import matplotlib.colors as colors
from bitsea.commons.mask import FILL_VALUE
import pandas as pd

OUTDIR=addsep(args.outdir)
MASKFILE=args.maskfile
TheMask=Mask.from_file(MASKFILE)

bathy_map = TheMask.bathymetry()
# NaN in land 
bathy_plot = np.where(bathy_map == FILL_VALUE, np.nan, bathy_map)

if TheMask.grid.is_regular():
    x = TheMask.lon
    y = TheMask.lat
else:
    x = TheMask.xlevels
    y = TheMask.ylevels

#
SUB='alb'
df=pd.read_csv(OUTDIR + SUB + "_superfloat_oxy_at600m.csv")
#


#element of teh map
bounds = [0, 200, 600, 1000, 1500, 2000, 2500, 3000, 3500, 4000]
cmap = plt.get_cmap("viridis", len(bounds)-1)
norm = colors.BoundaryNorm(bounds, cmap.N, clip=True)


plt.figure(figsize=(14, 8))
pcm = plt.pcolormesh(x, y,bathy_plot,shading='auto',cmap=cmap,norm=norm)
cbar = plt.colorbar(pcm,boundaries=bounds,ticks=bounds, spacing='proportional')
cbar.set_label("Depth [m]")

plt.title('Bathymetry')
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.gca()
plt.savefig(OUTDIR + "/Med_sea_bathy.png")
