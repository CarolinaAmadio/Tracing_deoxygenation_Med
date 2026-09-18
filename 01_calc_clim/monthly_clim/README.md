# monthly_clim

Questa cartella contiene il workflow per generare climatologie **mensili** a partire dai dati Superfloat e Coriolis.

## Cosa fa il launcher

Il file `Launcher.sh` esegue questi passaggi principali:
- definisce `BASEDIR`, `NAMEDIR=01_calc_clim` e `WORKDIR=${BASEDIR}/${NAMEDIR}/monthly_clim`
- attiva l'ambiente Python necessario
- imposta `PYTHONPATH` su `${BASEDIR}/bit.sea/src`
- imposta `ONLINE_REPO=${BASEDIR}/ONLINE`
- crea le directory di output:
  - `PLOTS`
  - `PLOTS/CLIMA_FLOAT`
  - `PLOTS/SUPERFLOAT`
  - `PLOTS/CORIOLIS`
  - `PLOTS/MONTHLY_PROFILES`
- lancia in sequenza gli script Python per la variabile `O2o`

## File richiamati dal launcher

1. `Month_Climfloat_netcdf_Coriolis.py`
   - genera climatologie mensili per i sub-bacini dai dati Coriolis
   - interpola i profili sulle quote di riferimento del modello
   - salva i risultati in NetCDF mensili:
     - `MM_Avg_<variable>_coriolis_ogs.nc`
     - `MM_Std_<variable>_coriolis_ogs.nc`
   - salva anche PNG e CSV dei profili per ciascun sub-bacino

2. `Month_Climfloat_netcdf_superfloat.py`
   - genera climatologie mensili per i sub-bacini dai dati Superfloat
   - applica la stessa logica di interpolazione e aggregazione mensile
   - salva i risultati in NetCDF mensili:
     - `MM_Avg_superfloat_dataset_<variable>.nc`
     - `MM_Std_superfloat_dataset_<variable>.nc`
   - salva anche PNG e CSV dei profili per ciascun sub-bacino

3. `compare_clima_doxy_monthly.py`
   - confronta le climatologie mensili Superfloat e Coriolis
   - genera grafici per ciascun sub-bacino comparando:
     - `PLOTS/SUPERFLOAT`
     - `PLOTS/CORIOLIS`
     - eventuali dati EMODNET o referenze esterne
   - salva le figure in `PLOTS/CLIMA_FLOAT`

4. `plot_all_months.py`
   - legge tutti i file NetCDF mensili generati in `PLOTS/SUPERFLOAT` e `PLOTS/CORIOLIS`
   - disegna profili mensili per sub-bacino su un unico grafico
   - salva i grafici in `PLOTS/MONTHLY_PROFILES`

5. `create_pdf_monthly_clim.py`
   - prende le immagini generate in `PLOTS/CLIMA_FLOAT`
   - raggruppa le immagini per sub-bacino/variabile
   - genera PDF di output per ogni gruppo

## Nota importante

Il workflow mensile calcola e confronta climatologie su base mese-per-mese, quindi il suo output è diverso da quello della cartella `yearly_clim`, che invece lavora su climatologie annuali.