import argparse
def argument():
    parser = argparse.ArgumentParser(description = '''
    Executed usually just after float download, creates Float_Index.0.txt file,
    the Database of floats, opening NetCDF files to take
    * lon,lat,time, parameters *
    If there is an operational Float_Indexer.txt of infos previously stored, dump_index.py
    takes them and opens only the just downloaded files.
    ''', formatter_class=argparse.RawTextHelpFormatter)


    parser.add_argument(   '--inputdir','-i',
                                type = str,
                                required = True,
                                help = 'e.g. /gss/gss_work/DRES_OGS_BiGe/Observations/TIME_RAW_DATA/ONLINE/FLOAT_BIO/')
    parser.add_argument(   '--input_float_indexer','-f',
                                type = str,
                                required = False,
                                help = 'float indexer corrected file, like Float_Indexer.txt')
    parser.add_argument(   '--output_float_indexer','-o',
                                type = str,
                                required = True,
                                help = '''float indexer rough file as
                                /gss/gss_work/DRES_OGS_BiGe/Observations/TIME_RAW_DATA/ONLINE/FLOAT_BIO/Float_Indexer.0.txt''')
    parser.add_argument(   '--type','-t',
                                type = str,
                                required = True,
                                choices = ['canyonmed_float'])

    return parser.parse_args()

args = argument()


import netCDF4

import datetime
import os,glob
import numpy as np
from bitsea.commons.utils import addsep
import pandas as pd

from io import StringIO ## for Python 3


NOW=datetime.datetime.now()
mydtype= np.dtype([
          ('file_name','S200'),
          ('lat',np.float64),
          ('lon',np.float64),
          ('time','S17'),
          ('parameters','S400'),
          ('profile_avail','S200')]  
          ) #profile_avail options: I or P or B ==>>   I --> insitu || P --> ppcon reconstructed || B --> both are available 

FILELIST=[]
is_provided_indexer = False
if args.input_float_indexer is not None:
    if os.path.exists(args.input_float_indexer):
        INDEX_FILE=np.loadtxt(args.input_float_indexer,dtype=mydtype, delimiter=",",ndmin=1)
        FILELIST=INDEX_FILE['file_name'].tolist()
        is_provided_indexer = len(FILELIST) >0

if args.type=="canyonmed_float":
    VARLIST=['DOXY','NITRATE','CHLA', 'PSAL','TEMP','PH_IN_SITU_TOTAL', 'BBP700','BBP532', 'DOWNWELLING_PAR','CDOM','DOWN_IRRADIANCE380'       ,'DOWN_IRRADIANCE412'       ,'DOWN_IRRADIANCE490', 'PO4','DIC','SiOH4','AT']
    ppcon_vars=['CHLA_PPCON', 'NITRATE_PPCON','BBP700_PPCON']
    canyonmed_vars=['NO3_CANYONMED', 'PHOSPHATE_CANYONMED','DIC_CANYONMED','SiOH4_CANYONMED','AT_CANYONMED','PH_IN_SITU_TOTAL_CANYONMED' ]
    INSITUVAR= ['DOXY','PRES','PSAL','TEMP','BBP532', 'DOWNWELLING_PAR','CDOM','DOWN_IRRADIANCE380','DOWN_IRRADIANCE412'       ,'DOWN_IRRADIANCE490']
    NNmethod0= '_PPCON'
    NNmethod = '_CANYONMED'
 
import sys

def file_header_content(filename,VARLIST, avail_params=None):
    '''
    it takes variable list
    Returns
    - a string like
        6901765/MR6901765_024.nc 34.024883 24.519977 20150818-09:33:00 DOXY NITRATE CHLA PRES PSAL TEMP
    - None in case of error
    '''
    try:
        ncIN = netCDF4.Dataset(filename,'r')
    except:
        print ("Not valid NetDCF file: " + filename)
        return

    lon=float(ncIN.variables['LONGITUDE'][0])
    lat=float(ncIN.variables['LATITUDE'][0])


    ref  = np.array(ncIN.variables['REFERENCE_DATE_TIME']).tobytes().decode()
    juld = int (ncIN.variables['JULD'][0])
    d=datetime.datetime.strptime(ref,'%Y%m%d%H%M%S')
    Time =  d+datetime.timedelta(days=juld)
    split_path=filename.rsplit(os.sep)
    wmo = split_path[-2]
    basename=split_path[-1]
    relative_name=wmo + "/" + basename
    s="%s,%f,%f,%s," %(relative_name, lat, lon, Time.strftime('%Y%m%d-%H:%M:%S'))

    if avail_params is None:
        for var in VARLIST: 
            var0  = var + NNmethod0 # ppcon  
            varpp = var + NNmethod  # canyon

            if var in ncIN.variables.keys():
                s= s+" " + var   
            elif varpp in ncIN.variables.keys():
                s= s+" " + var
            elif var0 in ncIN.variables.keys():
                s= s+" " + var
            else:
                pass
        
        s= s + ", "        
        #ncIN.close()
    else:
        s=s+" " + avail_params
    
    print(filename)
    
    LIST_ATTR=[]
    if avail_params is None:
        for var in VARLIST:

            var0  = var + NNmethod0   # e.g. _PPCON
            varpp = var + NNmethod    # e.g. _CANYONMED

            has_insitu = var   in ncIN.variables
            has_ppcon  = var0  in ncIN.variables
            has_canyon = varpp in ncIN.variables

            if not has_insitu and not has_ppcon and not has_canyon: continue

            # --------------------------------------------------
            # 1) VARIABLES WITH TWO NN METHODS (e.g. NO3)
            #    PPCON and CANYON must always appear together
            # --------------------------------------------------
            if var in INSITUVAR:
                if has_insitu:
                   s += 'I'
                   LIST_ATTR.append(var+'_I')            
            elif var in ["NITRATE"]:   # extend if needed

                # If only one NN exists → ERROR
                if has_ppcon != has_canyon:
                    s += 'X'
                    csv_file = "nitrate_no_ppcon_or_canyonmed.csv"
                    if os.path.exists(csv_file):
                       df = pd.read_csv(csv_file)

                    else:
                       df = pd.DataFrame(columns=["filename"])
                    df.loc[len(df)] = filename
                    df = df.drop_duplicates()
                    df.to_csv(csv_file, index=False)

                # INSITU only
                elif has_insitu and not has_ppcon and not has_canyon:
                    s += "I"
                    LIST_ATTR.append(var+'_I')
                # Triple (INSITU + PPCON + CANYON)
                elif has_insitu and has_ppcon and has_canyon:
                    s += "T"
                    LIST_ATTR.append(var+'_T')

                # Derived only (PPCON + CANYON, no INSITU)
                elif not has_insitu and has_ppcon and has_canyon:
                    s += "D"
                    LIST_ATTR.append(var+'_D')
                else: 
                    print('has_ppcon '   +str( has_ppcon))
                    print('has_canyon: ' +str( has_canyon))
                    print('has_insitu: ' +str( has_insitu))
                    raise ValueError(f"check the NN reconstruction for {var}")

            # --------------------------------------------------
            # 2) VARIABLES WITH SINGLE NN (e.g. pH)
            #    INSITU + CANYON logic
            # --------------------------------------------------
            elif var in ["PH_IN_SITU_TOTAL"]:

                # INSITU only
                if has_insitu and not has_canyon:
                    s += "I"
                    LIST_ATTR.append(var+'_I')

                # Both INSITU and CANYON
                elif has_insitu and has_canyon:
                    s += "B"
                    LIST_ATTR.append(var+'_B')

                # CANYON only
                elif not has_insitu and has_canyon:
                    s += "C"
                    LIST_ATTR.append(var+'_C')

                else:
                    raise ValueError(f"problems with  NN reconstruction for {var}")
            # --------------------------------------------------
            # 3) VARIABLES WITH PPCON ONLY (e.g. CHLA, BBP700)
            #   ins + ppcon logica
            # --------------------------------------------------
            elif var in ["CHLA", "BBP700"]:

                # INSITU only
                if has_insitu and not has_ppcon:
                    s += "I"
                    LIST_ATTR.append(var+'_I')

                # Both INSITU and PPCON
                elif has_insitu and has_ppcon:
                    s += "B"
                    LIST_ATTR.append(var+'_B')

                # PPCON only
                elif not has_insitu and has_ppcon:
                    s += "P"
                    LIST_ATTR.append(var+'_P')

                else:
                    raise ValueError(f"iissue check the NN reconstruction for {var}")

            # --------------------------------------------------
            # 4) VARIABLES WITH CANYON ONLY (PO4, DIC, AT, SiOH4)
            # --------------------------------------------------
            elif var in ["PO4", "AT", "DIC", "SiOH4"]:

                # Only possible case: CANYON only
                if not has_insitu and has_canyon:
                    s += "C"
                    LIST_ATTR.append(var+'_C')
                # If INSITU exists for these → error (unexpected)
                elif has_insitu:
                    raise ValueError(
                        f"{var}: INSITU should not exist for this variable."
                    )

                else:
                    pass
            else:
                raise ValueError('Check type of {var}')
    ncIN.close()
    if len(s.split(",")[-2].strip().split()) == len(s.split(",")[-2].strip().split()):
        pass
    else: 
        raise ValueError(f"mismatch btw of variables in float index and flags")
    return s
    

def get_sensor_list(wmo,LINES):
    for line in LINES:
        if wmo in line:
            d=StringIO(line)
            A=np.loadtxt(d,dtype=mydtype,delimiter=',')
            return str(A['parameters'])
    else:
        print (wmo + " not in CORIOLIS")
        return 'DOXY NITRATE CHLA PRES PSAL TEMP'


LOC=addsep(args.inputdir)
FloatIndexer=args.output_float_indexer
DIRLIST=os.listdir(LOC)
HERE=os.getcwd()
os.chdir(LOC)

LINES=[]
for DIR in DIRLIST:
    dirpath=DIR
    filenames = glob.glob(dirpath + "/*nc")
    filenames.sort()
    for filename in filenames:
        #if filename == "1902605/SR1902605_001.nc":
        #    sys.exit('ddd')
        if filename[-4:]!='D.nc':
            if filename in FILELIST:
                ind=FILELIST.index(filename)
                timedist = NOW - datetime.datetime.strptime(INDEX_FILE['time'][ind][:8],"%Y%m%d")
                if timedist.days > 15:
                    line="%s,%f,%f,%s,%s" %(filename, INDEX_FILE['lat'][ind], INDEX_FILE['lon'][ind], INDEX_FILE['time'][ind], INDEX_FILE['parameters'][ind])
                    LINES.append(line+"\n")
                else:
                    line=file_header_content(filename,VARLIST,avail_params=None)
                    if line is not None:
                        if args.type=="lov": line = line.replace('SR_NO3_ADJUSTED','SR_NO3')
                        LINES.append(line+"\n")
            else:
                line=file_header_content(filename,VARLIST,avail_params=None)
                if line is not None:
                    if args.type=="lov": line = line.replace('SR_NO3_ADJUSTED','SR_NO3')
                    LINES.append(line+"\n")
                    if is_provided_indexer: print ("added " + line)



F = open(FloatIndexer,'w')
F.writelines(LINES)
F.close()
os.chdir(HERE)
