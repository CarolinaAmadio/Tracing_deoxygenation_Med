# yearly_clim

Questa cartella contiene il workflow per generare climatologie **annuali** a partire dai dati BGC-Argo Superfloat e Coriolis.

## Cosa fa il launcher

Il file `Launcher.sh` esegue questi passaggi principali:
- definisce `BASEDIR`, `NAMEDIR=01_calc_clim` e `WORKDIR=${BASEDIR}/${NAMEDIR}/yearly_clim`
- attiva l'ambiente Python necessario
- imposta `PYTHONPATH` su `${BASEDIR}/bit.sea/src`
- imposta `ONLINE_REPO=${BASEDIR}/ONLINE`
- crea le directory di output:
  - `PLOTS`
  - `PLOTS/CLIMA_FLOAT`
  - `PLOTS/SUPERFLOAT`
  - `PLOTS/CORIOLIS`
- lancia in sequenza gli script Python per la variabile `O2o`

## File richiamati dal launcher

1. `Yr_Climfloat_netcdf_superfloat.py`
   - legge i profili Superfloat BGC-Argo per la variabile richiesta
   - interpola i profili sulle quote di riferimento del modello
   - calcola medie e deviazioni standard annuali per ogni sub-bacino
   - salva i risultati in NetCDF annuali:
     - `yr_Avg_superfloat_dataset_<variable>.nc`
     - `yr_Std_superfloat_dataset_<variable>.nc`
   - salva anche PNG e CSV dei profili per ciascun sub-bacino

2. `Yr_Climfloat_netcdf_Coriolis.py`
   - legge i profili Coriolis per la stessa variabile
   - applica la stessa logica di interpolazione e aggregazione annuale
   - salva i NetCDF annuali:
     - `yr_Avg_<variable>_coriolis_ogs.nc`
     - `yr_Std_<variable>_coriolis_ogs.nc`
   - salva anche PNG e CSV dei profili per ciascun sub-bacino

3. `compare_clima_doxy.py`
   - confronta le climatologie annuali Superfloat e Coriolis
   - genera grafici per ciascun sub-bacino comparando:
     - `PLOTS/SUPERFLOAT`
     - `PLOTS/CORIOLIS`
     - dati di riferimento EMODNET
   - salva le figure in `PLOTS/CLIMA_FLOAT`

4. `clim_visualizer_html_pdf.py`
   - crea una pagina HTML semplice per visualizzare le immagini generate
   - usa una configurazione YAML per ordinare i sottobacini

5. `create_pdf.py`
   - raggruppa le immagini generate in `PLOTS/CLIMA_FLOAT`
   - crea PDF output per ogni variabile / sub-bacino


