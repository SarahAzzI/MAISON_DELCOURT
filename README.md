# ChocoBot - Maison Delcourt

Assistant IA qui conseille des coffrets de chocolats selon les goûts, le budget et les allergies des clients.
Développé en urgence pour Noël : à vous de le rendre conforme, sobre et fiable (voir le brief).

Le chatbot utilise un petit modèle de langage qui tourne **sur votre machine**, grâce à Ollama.

## 1. Première installation (à faire une seule fois)

### 1a. Installer Ollama et télécharger les modèles

1. Installer Ollama : https://ollama.com/download
   (ou, dans **PowerShell** : `irm https://ollama.com/install.ps1 | iex` ; Linux / Mac : `curl -fsSL https://ollama.com/install.sh | sh`)
2. **Fermer et rouvrir le terminal**, puis télécharger les modèles (quelques Go, prévoir environ 4 Go de mémoire libre) :
   ```
   ollama pull llama3.2:3b
   ollama pull llama3.2:1b
   ```
3. Vérifier : `ollama list` doit afficher les deux modèles.

### 1b. Créer l'environnement Python

Ouvrir un terminal **dans le dossier du projet** (celui qui contient `app.py`).

**Windows (Invite de commandes)**
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Windows (PowerShell)** : si l'activation est refusée (« l'exécution de scripts est désactivée »), tapez d'abord
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, ou utilisez l'Invite de commandes, ou n'activez pas le venv :
`.venv\Scripts\python -m pip install -r requirements.txt`.

**Linux / Mac**
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Aucun fichier de configuration n'est nécessaire : le projet utilise Ollama et `llama3.2:3b` par défaut.

### 1c. Vérifier que tout fonctionne

```
python check_llm.py
```
Il affiche une réponse du modèle (la première prend plus de temps : le modèle se charge en mémoire).
S'il affiche une erreur, vérifiez qu'Ollama est lancé (icône de lama près de l'horloge) et que `ollama list` montre le modèle.

## 2. Lancer le projet (à chaque fois)

Dans le dossier du projet :
```bash
.venv\Scripts\activate          (Linux / Mac : source .venv/bin/activate)
uvicorn app:app --reload
```
Arrêter le serveur : Ctrl+C. Ollama doit rester lancé en arrière-plan.

### Lancer Arize Phoenix (Monitoring et traçage LLM)

Pour capturer et visualiser les traces OpenTelemetry, la latence et les tokens en temps réel, lancez le serveur Phoenix dans un terminal séparé :
```bash
.venv\Scripts\activate          (Linux / Mac : source .venv/bin/activate)
phoenix serve
```
Le tableau de bord est accessible sur **http://localhost:6006**.

## Où voir quoi

- **Le chatbot** : http://localhost:8000
- **Le back-office de la Maison Delcourt** (clients, conversations et métriques LLM) : http://localhost:8000/admin
- **Le dashboard Arize Phoenix** (traces complètes, latences, tokens, evals) : http://localhost:6006
- **La documentation de l'API** : http://localhost:8000/docs
- **La base de données** : le fichier `chocobot.db`, créé au premier message, dans le dossier où vous lancez `uvicorn`.
  Ouvrez-le avec [DB Browser for SQLite](https://sqlitebrowser.org/) (ou `sqlite3 chocobot.db`). Tables : `customers`, `messages`, `llm_metrics`.
  Pour repartir de zéro, arrêtez le serveur et supprimez ce fichier.
- **Les données d'émissions carbone** : le fichier `data/emissions.csv` généré par CodeCarbon.

## Mesurer et évaluer (Performances & Empreinte Carbone)

## 1 Mesure de l'empreinte carbone (CodeCarbon)

L'empreinte carbone de ChocoBot est mesurée avec [CodeCarbon](https://codecarbon.io) (v3.3.1) pendant un scénario de test reproductible.

### Principe

`load_test.py` rejoue des conversations types contre le serveur et entoure l'ensemble d'un `EmissionsTracker`. Il en tire l'énergie consommée (kWh) et les émissions (kg CO₂eq), au total et par message. Chaque run ajoute une ligne à `data/emissions.csv`.

### Prérequis

- Environnement virtuel activé et dépendances installées (`pip install -r requirements.txt`)
- Ollama lancé avec le modèle `llama3.2:3b`
- Serveur ChocoBot lancé sur le port 8000
- Applications lourdes fermées : CodeCarbon mesure toute la machine

### Lancer une mesure

```bash
python load_test.py 5
```

5 conversations de 5 messages, soit 25 messages. Un message d'échauffement est envoyé avant le tracker pour exclure le chargement du modèle en mémoire. Faire 3 runs dans les mêmes conditions.

### Résumer une série

```bash
python summarize_emissions.py chocobot-baseline 25 3
```

Arguments : nom du projet CodeCarbon, messages par run, nombre de derniers runs à agréger. Le résultat est enregistré dans `data/summary_chocobot-baseline.json`.

Pour mesurer une version optimisée, changer `project_name` dans `load_test.py` (par exemple `chocobot-optimise`) et relancer avec le même protocole.

### Résultats de l'état initial

| Indicateur | Valeur (moyenne de 3 runs de 25 messages) |
|---|---|
| Durée par run | environ 140 s |
| Énergie par run | environ 0,46 Wh |
| Émissions par run | environ 0,026 g CO₂eq |
| Émissions par message | environ 1,04 mg CO₂eq |

Les 3 runs sont très proches (écart d'environ 0,3 % sur la durée et 1,5 % sur les émissions).

### Limites de la mesure

- Sur Mac, sans droits administrateur, CodeCarbon estime la puissance du processeur (à peu près constante) et ne compte pas le GPU : le chiffre absolu est probablement sous-estimé.
- Conséquence : les gains mesurés reflètent surtout le temps de calcul économisé.
- Périmètre : modèle local (`llama3.2:3b`) sur un MacBook Apple M4 (16 Go), pas un serveur distant.
- L'avant/après reste comparable tant que le protocole est identique.

### Fichiers

- `data/emissions.csv` : mesures brutes, une ligne par run
- `data/summary_<projet>.json` : résumé d'une série
- `load_test.py` : scénario et mesure
- `summarize_emissions.py` : agrégation des runs

### 2. Analyser les traces LLM (Arize Phoenix)

Lorsque le serveur Phoenix est lancé (`phoenix serve`), rendez-vous sur **http://localhost:6006** (ou cliquez sur le bouton dans le back-office `/admin`). Vous pouvez inspecter :
- Le détail de chaque appel LLM (prompt système, prompt utilisateur, réponse).
- La latence exacte par requête.
- Le nombre de tokens consommés (prompt, complétion, total).
- L'historique des sessions et des erreurs.

## Réglages facultatifs

Pour changer de modèle ou simuler des pannes, copiez `.env.example` en `.env` (une seule fois : le refaire écrase vos
réglages), décommentez les lignes voulues, puis relancez `uvicorn`.

## Structure

- `app.py` : API FastAPI
- `chatbot.py` : logique de conversation
- `llm.py` : appel au modèle (Ollama) et instrumentation Phoenix
- `db.py` : stockage SQLite (clients, messages, métriques)
- `static/` : page de chat et back-office
- `docs/` : documentations détaillées ([index](docs/README.md), audit, monitoring, RGPD, CodeCarbon)
- `data/catalog.json` : catalogue des coffrets
- `data/emissions.csv` : historique des émissions mesurées par CodeCarbon
- `check_llm.py` : test de connexion au modèle
- `load_test.py` : test de charge avec mesure d'émissions carbone (CodeCarbon)
