from bitsea.basins.region import Region, Rectangle
import bitsea.basins.V2 as basV2
import pandas as pd

def cross_Med_basins(RECTANGLE):
   if RECTANGLE.cross(basV2.eas3):
      LIST_REGION=['lev1','lev2','lev3','lev4','aeg']
      if RECTANGLE.cross(basV2.lev1):
         return(basV2.lev1.name, basV2.lev1.borders, )
      elif RECTANGLE.cross(basV2.lev2):
         return(basV2.lev2.name, basV2.lev2.borders)
      elif RECTANGLE.cross(basV2.lev3):
         return(basV2.lev3.name, basV2.lev3.borders)
      elif RECTANGLE.cross(basV2.lev4):
         return(basV2.lev4.name, basV2.lev4.borders)
      elif RECTANGLE.cross(basV2.aeg):
         return(basV2.aeg.name, basV2.aeg.borders)
   elif  RECTANGLE.cross(basV2.wes3):
      LIST_REGION=['alb','nwm','tyr1','tyr2','swm1','swm2']
      if RECTANGLE.cross(basV2.alb):
         return(basV2.alb.name, basV2.alb.borders)
      elif RECTANGLE.cross(basV2.nwm):
         return(basV2.nwm.name, basV2.nwm.borders)
      elif RECTANGLE.cross(basV2.tyr1):
         return(basV2.tyr1.name, basV2.tyr1.borders)
      elif RECTANGLE.cross(basV2.tyr2):
         return(basV2.tyr2.name, basV2.tyr2.borders)
      elif RECTANGLE.cross(basV2.swm1):
         return(basV2.swm1.name, basV2.swm1.borders)
      elif RECTANGLE.cross(basV2.swm2):
         return(basV2.swm2.name, basV2.swm2.borders)
   elif RECTANGLE.cross(basV2.mid3):
      LIST_REGION=['adr1','adr2','ion1','ion2','ion3']
      if RECTANGLE.cross(basV2.adr1):
         return(basV2.adr1.name, basV2.adr1.borders)
      elif RECTANGLE.cross(basV2.adr2):
         return(basV2.adr2.name, basV2.adr2.borders)
      elif RECTANGLE.cross(basV2.ion1):
         return(basV2.ion1.name, basV2.ion1.borders)
      elif RECTANGLE.cross(basV2.ion2):
         return(basV2.ion2.name, basV2.ion2.borders)
      elif RECTANGLE.cross(basV2.ion3):
         return(basV2.ion3.name, basV2.ion3.borders)


def plot_map_subbasins():
      """ input : none 
        output: list_name --> subbasins code and subbabis limits of the area
      """ 
      list_name=['alb','swm1','swm2','nwm','tyr1','tyr2','adr1','adr2','aeg','ion1','ion2','ion3','lev1','lev2','lev3','lev4']
      matrix_borders=(basV2.alb.borders,basV2.swm1.borders,basV2.swm2.borders,basV2.nwm.borders, basV2.tyr1.borders, basV2.tyr2.borders,  basV2.adr1.borders, basV2.adr2.borders, basV2.aeg.borders, basV2.ion1.borders, basV2.ion2.borders, basV2.ion3.borders ,basV2.lev1.borders, basV2.lev2.borders, basV2.lev3.borders, basV2.lev4.borders)
      return(list_name, matrix_borders)

def sorted_basin():
    sorted_list=[ 'alb', 'swm1', 'swm2','nwm','tyr1', 'tyr2', 'ion1','adr1','adr2','ion2','ion3', 'lev1','lev2','lev3','lev4','aeg']
    return (sorted_list)

    
def Is_in_Med(lat, lon):
      LN_MIN=-6
      LT_MIN=36
      LN_MAX=30
      LT_MAX=46
      return LT_MIN < lat < LT_MAX and LN_MIN < lon < LN_MAX

def identify_ocean_basin(lat, lon):
    """
    Identifica il bacino oceanico in base alla latitudine e longitudine fornite e restituisce i limiti geografici del bacino.
    Args:
        lat (float): Latitudine.
        lon (float): Longitudine.
    Returns:
        str: Nome del bacino oceanico.
        tuple: Limiti di latitudine e longitudine (lat_min, lat_max, lon_min, lon_max).
    """
    # Oceano Atlantico
    if lat >= -60 and lat <= 70 and lon >= -80 and lon <= 20:
        if lat >= 0:  # Nord Atlantico
            return "N. Atlantic", (0, 70, -80, 20)
        else:  # Sud Atlantico
            return "S. Atlantic", (-60, 0, -80, 20)
    
    # Mar Mediterraneo
    elif lat >= 30 and lat <= 46 and lon >= -6 and lon <= 36:
        return "Mediterranean Sea", (30, 46, -6, 36)
    
    # Oceano Pacifico
    elif lat >= -60 and lat <= 70 and (lon >= 120 or lon <= -70):
        if lat >= 0:  # Nord Pacifico
            if lon >= 120:
                return "N. Pacific", (0, 70, 120, 180)
            else:
                return "N. Pacific", (0, 70, -180, -70)
        else:  # Sud Pacifico
            if lon >= 120:
                return "S. Pacific", (-60, 0, 120, 180)
            else:
                return "S. Pacific", (-60, 0, -180, -70)
    # Oceano Indiano
    elif lat >= -60 and lat <= 30 and lon >= 20 and lon <= 120:
        return "Indian", (-60, 30, 20, 120)
    # Oceano Artico
    elif lat > 70:
        return "Artic", (70, 90, -180, 180)
    # Oceano Antartico
    elif lat < -60:
        if lon>0:
           return "W. Antartic", (-90, -20,    0, 180)
        else: 
           return "W. Antartic", (-90, -20,    -180, 0)
    else:
        return "Mare Continentale o Indefinito", (None, None, None, None)

