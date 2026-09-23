# PPCON

Creazione del dataset **PPCON** a partire dai file contenuti in `SUPERFLOAT`.

Il workflow è pensato per generare profili NetCDF arricchiti con le variabili predette dal modello **PPCON**:

* `NITRATE_PPCON`
* `CHLA_PPCON`
* `BBP700_PPCON`

## Struttura delle directory

I dati di input sono contenuti nella directory `SUPERFLOAT`:

```text
ONLINE/
└── SUPERFLOAT/
    ├── *.nc
    └── Float_Index.txt
```

Gli script del workflow PPCON si trovano in:

```text
bit.sea/src/bitsea/Float/ppcon/
```

In particolare, i file coinvolti dal launcher sono:

* `clustering/clustering.py`
* `make_generated_ds/generate_netcdf_netcdf4.py`
* `dump_index.py`

## Workflow

Il processo è gestito dallo script `Launcher.sh`.

Il launcher esegue i passaggi seguenti:

1. imposta l’ambiente di esecuzione e i percorsi di lavoro;
2. copia la struttura di `SUPERFLOAT` dentro `ONLINE/PPCON/`;
3. prepara la directory `ONLINE/PPCON/clustering/`;
4. genera il `Float_Index.txt` del dataset PPCON tramite `dump_index.py`.

Le chiamate a `clustering/clustering.py` e `make_generated_ds/generate_netcdf_netcdf4.py` sono presenti nel launcher ma risultano commentate, quindi non vengono eseguite nella configurazione attuale.

## Launcher.sh

## Descrizione

Lo script `Launcher.sh` è il punto di ingresso del workflow PPCON su SLURM.

Definisce il job, attiva l’ambiente Python, imposta le directory di input e output e poi avvia la fase finale di indicizzazione del dataset PPCON.

## Passi eseguiti dal launcher

### 1. Preparazione dell’ambiente

Vengono impostati:

* `BASEDIR`
* `WORKDIR`
* `ONLINE_REPO`
* `PYTHONPATH`

e viene attivato l’ambiente Python usato per i moduli `bitsea`.

### 2. Copia dei file SUPERFLOAT in PPCON

La directory `ONLINE/SUPERFLOAT/` viene copiata in `ONLINE/PPCON/` mantenendo la struttura delle sottodirectory.

Questo passaggio prepara il contenuto che verrà poi usato dal workflow PPCON.

### 3. Preparazione della directory di clustering

Viene creata la directory:

```text
ONLINE/PPCON/clustering/
```

Questa directory è destinata ai file intermedi del workflow.

### 4. Generazione dell’indice

Il launcher esegue:

```bash
python dump_index.py -i $ONLINE_REPO/PPCON -o $ONLINE_REPO/PPCON/Float_Index.txt -t ppcon_float
```

Questo comando genera o aggiorna il file `Float_Index.txt` del dataset PPCON.

## Script PPCON richiamati dal launcher

### `clustering/clustering.py`

Questo script prepara un dataset CSV per il clustering a partire da:

* `Float_Index.txt`, oppure
* file `DIFF_floats...`

Lo script controlla il nome del file di input, legge i dati e scrive un CSV chiamato:

```text
ds_sf_clustering.csv
```

nella directory di output indicata con `-o`.

Il file di input non viene modificato.

### `make_generated_ds/generate_netcdf_netcdf4.py`

Questo script aggiunge le variabili PPCON ai file NetCDF presenti in `ONLINE/PPCON/`.

Le variabili prodotte sono:

* `NITRATE_PPCON`
* `CHLA_PPCON`
* `BBP700_PPCON`

Per ciascuna variabile vengono aggiunti anche:

* il relativo asse di pressione;
* il campo QC.

Lo script apre i file NetCDF in modalità append e scrive direttamente dentro i file già presenti nella directory `PPCON`.

### `dump_index.py`

Questo script genera il file `Float_Index.txt` associato al dataset PPCON.

Nel launcher attuale è l’unico script PPCON effettivamente eseguito.

## Variabili PPCON

I file NetCDF PPCON contengono le seguenti variabili stimate:

```text
NITRATE_PPCON
CHLA_PPCON
BBP700_PPCON
```

Per ciascuna variabile sono presenti anche i rispettivi profili di pressione e i campi QC:

```text
PRES_NITRATE_PPCON
NITRATE_PPCON_QC
PRES_CHLA_PPCON
CHLA_PPCON_QC
PRES_BBP700_PPCON
BBP700_PPCON_QC
```

## Output atteso

L’output del workflow PPCON è organizzato nella directory:

```text
ONLINE/PPCON/
```

In questa directory sono attesi:

* i file NetCDF copiati da `SUPERFLOAT`;
* il file `Float_Index.txt` generato dal launcher;
* eventuali file intermedi nella sottodirectory `clustering/`;
* i NetCDF arricchiti con le variabili PPCON, quando viene eseguito `generate_netcdf_netcdf4.py`.

## Stato attuale del workflow

Nel launcher fornito, la pipeline completa PPCON non è attiva in tutte le sue fasi.

In particolare:

* la preparazione dei file e la copia in `PPCON` sono attive;
* la generazione del `Float_Index.txt` è attiva;
* la generazione del CSV di clustering e l’arricchimento dei NetCDF PPCON risultano commentati.

Quindi, allo stato attuale, il launcher prepara il dataset e genera l’indice, ma non esegue automaticamente l’intera catena di calcolo delle variabili PPCON.

---

# Launcher.sh

## Schema semplificato del processo

```text
SUPERFLOAT
    │
    ├── copia in PPCON/
    │
    ├── preparazione directory clustering/
    │
    ├── dump_index.py
    │
    ├── clustering/clustering.py   [commentato]
    │
    └── make_generated_ds/generate_netcdf_netcdf4.py   [commentato]
```

## Variabili di ambiente usate dal launcher

Il launcher usa in particolare:

* `WORKDIR`
* `ONLINE_REPO`
* `INPUTDIR`
* `OUTDIR`
* `TRAIN_DIR`
* `ONLINE_REPO_CLUSTERING`

Questi percorsi definiscono il flusso dei dati tra `SUPERFLOAT`, `PPCON` e la directory di clustering.
