# CANYONMED

Creazione di un **dataset CANYONMED** a partire dai dati contenuti in `SUPERFLOAT` per le seguenti variabili biogeochimiche:

* `NITRATE_CANYONMED`
* `PO4_CANYONMED`
* `DIC_CANYONMED`
* `SiOH4_CANYONMED`
* `AT_CANYONMED`
* `PH_IN_SITU_TOTAL_CANYONMED`

## Struttura delle directory

I dati di input sono contenuti nella directory `SUPERFLOAT`:

```text
ONLINE/
└── SUPERFLOAT/
    ├── *.nc
    └── Float_Index.txt
```

Gli script utilizzati per la generazione del dataset CANYONMED si trovano in:

```text
03_calculate_NN_datasets/
└── CANYONMED/
    ├── canyonmed.py
    └── dump_index_canyonmed.py
```

## Workflow

Il processo di elaborazione è gestito dallo script `Launcher.sh`.

Lo script utilizza la directory `SUPERFLOAT` come input e genera il dataset CANYONMED, insieme al relativo `Float_Index.txt`.

Il workflow prevede i seguenti passaggi:

1. I file NetCDF contenuti in `SUPERFLOAT` vengono utilizzati come dati di input.
2. Le variabili CANYONMED vengono calcolate tramite `canyonmed.py`.
3. Viene generato il dataset CANYONMED in formato NetCDF.
4. Il relativo `Float_Index.txt` viene generato o aggiornato tramite `dump_index_canyonmed.py`.

## Variabili CANYONMED

I file NetCDF prodotti contengono le seguenti variabili CANYONMED:

```text
NITRATE_CANYONMED
PO4_CANYONMED
DIC_CANYONMED
SiOH4_CANYONMED
AT_CANYONMED
PH_IN_SITU_TOTAL_CANYONMED
```

## Ambito attuale

Al momento, questo workflow è dedicato **esclusivamente a CANYONMED**.

`PPCON` **non è incluso** in questo workflow.

Di conseguenza, i file NetCDF prodotti da questa procedura conterranno **solo le variabili CANYONMED**.

Non verrà quindi mai generato, nell'ambito di questo workflow, un singolo file NetCDF contenente contemporaneamente variabili **CANYONMED** e **PPCON**.

L'elaborazione delle variabili `PPCON` verrà implementata separatamente.

---

# canyonmed.py

## Descrizione

Lo script `canyonmed.py` elabora i profili biogeochimici contenuti nei file NetCDF di input e utilizza il modello **CANYON-MED** per stimare le principali variabili biogeochimiche.

Lo script mantiene la struttura delle directory di input nella directory di output e produce file NetCDF contenenti le variabili stimate da CANYON-MED.

## Argomenti da riga di comando

Lo script richiede tre argomenti:

```text
-i, --indir
```

Directory contenente i file NetCDF di input.

```text
-o, --outdir
```

Directory in cui verranno salvati i file NetCDF elaborati.

```text
-c, --coriolis
```

Directory o root contenente i file Coriolis utilizzati come riferimento.

## Processo di elaborazione

Per ogni file NetCDF presente nella directory di input, lo script esegue i seguenti passaggi.

### 1. Ricerca dei file di input

Vengono ricercati i file NetCDF nella directory di input secondo la struttura prevista:

```text
INPUTDIR/*/*.nc
```

Per ogni file trovato viene determinato il corrispondente file nella directory `CORIOLIS`, utilizzando lo stesso percorso relativo.

Viene inoltre costruito il corrispondente percorso nella directory di output, mantenendo la stessa struttura delle directory di input.

### 2. Controllo dell'output

Se il file di output esiste già, il processamento del file viene saltato.

In questo modo è possibile interrompere e rilanciare il processo senza dover rielaborare i file già completati.

### 3. Gestione dei file senza DOXY

Se il file NetCDF non contiene la variabile `DOXY`, il dataset viene copiato direttamente nel file di output senza applicare il processamento CANYON-MED.

### 4. Elaborazione dei profili contenenti DOXY

Se il file contiene `DOXY`, vengono eseguite le seguenti operazioni:

* vengono identificati i livelli di pressione associati a `DOXY`;
* `TEMP`, `PSAL` e `DOXY` vengono interpolati sulla stessa griglia di pressione;
* viene creato un nuovo dataset contenente le variabili interpolate;
* viene ricostruito il tempo assoluto a partire da `REFERENCE_DATE_TIME` e `JULD`;
* il profilo viene convertito dal formato **profile** al formato **point** utilizzando `argopy`;
* viene calcolata la densità utilizzando `gsw`;
* `DOXY` viene convertito nelle unità richieste dal modello;
* viene eseguita la predizione utilizzando il modello **CANYON-MED**;
* `DOXY` e le altre variabili vengono riconvertite nelle unità finali;
* alcune variabili e informazioni di metadati vengono copiate dal file Coriolis;
* il dataset viene riconvertito dal formato **point** al formato **profile**;
* vengono aggiunte al dataset finale le nuove variabili stimate da CANYON-MED;
* vengono aggiunti i corrispondenti profili di pressione e i relativi campi QC.

## Variabili stimate

Le variabili stimate dal modello CANYON-MED e aggiunte ai file NetCDF sono:

```text
NITRATE_CANYONMED
PO4_CANYONMED
DIC_CANYONMED
SiOH4_CANYONMED
AT_CANYONMED
PH_IN_SITU_TOTAL_CANYONMED
```

Per ciascuna variabile vengono inoltre aggiunti i relativi campi di pressione e QC, quando previsti dalla struttura del dataset.

## Output

Il dataset elaborato viene salvato in formato NetCDF nella directory di output utilizzando:

```python
to_netcdf(..., mode="w")
```

La struttura delle directory di output mantiene quella dei dati di input.

---

## Schema semplificato del processo

```text
SUPERFLOAT
    │
    ├── File NetCDF
    │
    ▼
canyonmed.py
    │
    ├── Lettura dati
    ├── Controllo DOXY
    ├── Interpolazione
    ├── Calcolo densità
    ├── Conversione unità
    ├── Modello CANYON-MED
    ├── Aggiunta variabili stimate
    └── Aggiunta QC e metadati
    │
    ▼
Dataset CANYONMED
    │
    ├── NITRATE_CANYONMED
    ├── PO4_CANYONMED
    ├── DIC_CANYONMED
    ├── SiOH4_CANYONMED
    ├── AT_CANYONMED
    └── PH_IN_SITU_TOTAL_CANYONMED
```


