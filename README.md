## Flusso del progetto

1. Lo script `./generator/generate_instance.py` crea dei file di input in `./instance`:
- `operators.json` contenente, per ogni giorno e care_unit, l'elenco degli operatori attivi
- `services.json` che contiene l'elenco dei servizi assegnabili
- `packets.json` che descrive i pacchetti (sottoinsiemi di servizi)
- `priorities.json` contenente le priorità di ciascun paziente che farà richieste
- `full_input.json` che, oltre alle informazioni precedenti, contiene anche l'elenco di protocolli e le incompatibilità fra servizi.

2. Una volta che è tutto generato è possibile chiamare lo script `./subsumptions/compute_subsumption_with_ASP.py` (o in alternativa `./subsumptions/compute_subsumption_with_MILP.py`) per ottenere il file `subsumption.json` che conterrà le informazioni riguardo che giorno è interamente contenuto in un altro, considerando gli intervalli degli operatori che sono attivi in quel giorno. Questo processo è necessario che sia svolto solo una volta prima della risoluzione.

3. Lo script `./master/solve_master_problem_with_ASP.py` permette, leggendo l'istanza in `full_input.json`, di ottenere un primo tentativo di assegnamento dei pacchetti nelle giornate. L'output è contenuto in `requests.json`.

4. Lo script `./subproblem/solve_subproblem_with_ASP.py` (o in alternativa `./subproblem/solve_subproblem_with_MILP.py`) legge l'output del problema master appena prodotto e restituisce il file `results.json` contenente l'elenco dei pacchetti schedulati richiesti dal master.

5. Lo script `./cores/compute_unsatisfiable_cores.py` legge i vari file generati e produce `unsatisfiable_cores.json` che ha al suo interno le informazioni per generare nuovi tagli utili al master, in formadi giorni di incompatibilità.

6. [TODO] manca lo script di integrazione dei cores nel ciclo di chiamata master-subproblem in cui verranno generati i nuovi vincoli di incompatibilità.

Il risultato finale con le assegnazioni è all'interno del file `./subproblem/results.json`, generato dal sottoproblema dopo essere stato chiamato per l'ultima volta dal master.

---

- TODO add initial shift when build input in python!!!
- TODO add incompatibilities and necessities