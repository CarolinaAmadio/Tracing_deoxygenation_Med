# 02_analyze_clim

Questa cartella contiene il workflow di analisi delle serie temporali e della qualità dei profili BGC-Argo e Coriolis nel Mediterraneo.

## Cosa fa il launcher

Il file `Launcher.sh` esegue questi passaggi principali:
- definisce `BASEDIR`, `NAMEDIR=02_analyze_clim` e `WORKDIR=${BASEDIR}/${NAMEDIR}`
- attiva l'ambiente Python necessario
- imposta `PYTHONPATH` su `${BASEDIR}/bit.sea/src`
- imposta `ONLINE_REPO=${BASEDIR}/ONLINE`
- crea la directory di output `plots`
- lancia lo script principale `timeseries_qc_pres_sal_rho_line_trend.py` per la variabile `O2o`

## File richiamati dal launcher

1. `timeseries_qc_pres_sal_rho_line_trend.py`
   - estrae valori di ossigeno sui profili Superfloat
   - calcola trend temporali real-time di O2 a 600 m e su isopicni di densità e liw based
   - salva per ogni sottobacino:
     - `${ISUB.name}_superfloat_trend.csv`
     - `${ISUB.name}_superfloat_trend.png`
   - output principale: directory `plots_qc_pres_sal_rho_trend`

## Altri script utili nella cartella

2. `timeseries_qc_pres_sal_rho.py`
   - confronta profili Superfloat e Coriolis su O2 a 600 m e sulla stessa isopycnale
   - salva per ogni sottobacino:
     - `${ISUB.name}_superfloat_oxy_at600m.csv`
     - `${ISUB.name}_coriolis_oxy_at600m.csv`
     - `${ISUB.name}_intersect_wmo_cycle.csv`
     - `${ISUB.name}_superfloat.png`
     - `${ISUB.name}_coriolis.png`
     - `${ISUB.name}_comparison_oxy_at600m.png`

3. `timeseries_at_depth.py`
   - calcola serie temporali e grafici O2 a 600 m per singolo sottobacino
   - salva CSV e PNG per ogni sottobacino:
     - `${ISUB.name}_coriolis_oxy_at600m.csv`
     - `${ISUB.name}_superfloat_oxy_at600m.csv`
     - `${ISUB.name}_intersect_wmo_cycle.csv`
     - `${ISUB.name}_superfloat.png`
     - `${ISUB.name}_coriolis.png`
     - `${ISUB.name}_comparison_oxy_at600m.png`

4. `Hovmoeller_temp_sal_rho_doxy.py`
   - genera tracciati di Hovmöller per temperatura, salinità, densità e ossigeno
   - salva file PNG in `OUTDIR` con nomi del tipo:
     - `<basin>_superfloat_hovmoeller.png`
     - `<basin>_coriolis_hovmoeller.png`

5. `create_pdf_hovmoeller.py`
   - raccoglie i PNG Hovmöller e li converte in un PDF
   - output: `hovmoeller.pdf` o `hovmoeller_<dataset>.pdf`

6. `Calculate_density.py`
   - calcola campi di densità medi a 600 m per sottobacino
   - salva:
     - `density_600m.csv`
     - `density_std_600m.csv`
     - `density_subplots_4x4.png`

## Nota importante

La cartella serve per analisi di serie temporali e qualità dei profili, con focus su O2 e densità. Il launcher di default esegue solo `timeseries_qc_pres_sal_rho_line_trend.py`, ma sono disponibili altri script per confronti Superfloat/Coriolis, Hovmöller e PDF di report.
