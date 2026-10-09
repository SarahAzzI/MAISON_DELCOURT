# Post-Mortem & Documentation de Gestion des Incidents · ChocoBot
**Projet :** ChocoBot · Maison Delcourt (Chocolatier artisanal lillois)  
**Date :** Octobre 2026  
**Auteurs :** Équipe Data / IA & DevOps  
**Périmètre :** Supervision, alerting (Sentry & local), gestion des défaillances et runbook d'exploitation avant la période critique du Black Friday et de Noël.

---

## 1. Contexte & Architecture de Supervision

Dans la perspective de la forte affluence attendue pour le Black Friday et les fêtes de fin d'année, l'assistant conversationnel **ChocoBot** a été doté d'une chaîne complète d'observabilité, de supervision des erreurs et de résilience face aux pannes.

```
                           ┌────────────────────────────────────────┐
                           │      Client Web / Mobile (Front)       │
                           └───────────────────┬────────────────────┘
                                               │ HTTP JSON
                                               ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 FastAPI (Port 8000)                                    │
│                                                                                        │
│  [Validation Pydantic] ──(422)──► ExceptionHandler ──► incidents.record_incident()     │
│            │                                                                           │
│  [Sobriété / Cache FAQ] ──(Hit)──► Réponse instantanée (0 token, 33 ms)               │
│            │ (Miss)                                                                    │
│  [Routage Modèle 1B/3B] ──► Ollama (Local LLM)                                        │
│                                   │                                                    │
│                                   ├─► Succès ──► Phoenix OTel + SQLite metrics         │
│                                   │                                                    │
│                                   └─► Échec (503/Timeout)                              │
│                                            │                                           │
│                                            ▼                                           │
│                              incidents.record_incident()                               │
│                              + Fallback Gracieux Catalogue                             │
└───────────────────────────────┬──────────────────────────┬─────────────────────────────┘
                                │                          │
                                ▼                          ▼
       ┌────────────────────────────────┐  ┌────────────────────────────────┐
       │   Logs Structurés & Sentry     │  │   Tableau de Bord Back-office  │
       │  • logs/incidents.log          │  │  • http://localhost:8000/admin │
       │  • logs/incidents.jsonl        │  │  • Bandeau d'alerte rouge      │
       │  • Sentry Cloud (si DSN actif) │  │  • Historique des incidents    │
       │  • Arize Phoenix (traces)      │  │  • Compteur d'erreurs en direct│
       └────────────────────────────────┘  └────────────────────────────────┘
```

### Outils déployés
1. **Journalisation structurée locale (`logs/incidents.log` et `logs/incidents.jsonl`) :**
   Format JSON standardisé horodaté (`ISO 8601`), catégorisation par type d'incident, session tronquée et stacktrace complète en cas d'exception.
2. **Suivi d'erreurs d'application (Sentry SDK) :**
   Intégration via `sentry-sdk[fastapi]` avec tags personnalisés (`incident_type`, `session_id`). Conformité RGPD stricte grâce à `send_default_pii=False`.
3. **Observabilité LLM (Arize Phoenix & OpenTelemetry) :**
   Collecteur OTel gRPC sur le port 4317 et tableau de bord sur `http://localhost:6006` pour monitorer la latence, les tokens et les traces de chaque inférence.
4. **Back-office avec alerte visuelle (`static/admin.html`) :**
   Bandeau rouge d'alerte réactif (`#alert-banner`), suivi du nombre d'erreurs et table d'historique des incidents récents.

---

## 2. Synthèse des Incidents Diagnostiqués et Résolus

| Incident | Type | Symptôme Initial | Cause Racine | Solution Appliquée | Impact Résiduel |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Incident 1** | `PANNE_API_LLM` | Erreur 503 / Crash HTTP 500 pour le client | Arrêt du service Ollama ou timeout sous charge (`FAIL_RATE`) | Mode dégradé sécurisé (*Graceful Fallback*) orientant vers les coffrets sans allergène et la boutique | **Zéro rupture de service**, réponse sûre garantie en 200 OK |
| **Incident 2** | `DONNEE_CORROMPUE` | Rejet 422 non tracé ou plantage de parsing | Payload JSON incomplet (absence de `session_id`) ou formats altérés | Handler FastAPI `RequestValidationError`, log d'audit immédiat et réponse 422 standardisée | Sécurisation de l'API sans fuite de stacktrace interne |
| **Incident 3** | `PIC_DE_CHARGE` | Latence > 8 s, engorgement GPU/CPU | Afflux massif d'appels LLM (simulé via `load_test.py`) | Cache FAQ statique (0 token), routage vers `llama3.2:1b`, fenêtre glissante (4 msgs) | Latence divisée par 2, absorption de 50 % du trafic sans LLM |

---

## 3. Analyse Détaillée des Incidents

### Incident 1 : Panne d'API LLM (503 Service Unavailable / Coupure Ollama)

#### A. Contexte et Déclenchement
- **Scénario :** Simulation d'une indisponibilité du moteur Ollama ou d'une défaillance d'infrastructure via `FAIL_RATE=0.5` dans `.env`, ou arrêt inopiné du processus `ollama serve`.
- **Symptôme avant correctif :** L'exception `RuntimeError("Panne simulée : 503 service unavailable")` remontait jusqu'à la couche HTTP, provoquant une erreur `500 Internal Server Error`. L'internaute se retrouvait face à un écran blanc ou un chatbot figé.

#### B. Diagnostic & Journalisation
L'incident est immédiatement intercepté dans le bloc `try...except` de `handle_chat()` ([chatbot.py](file:///home/souhaib/Documents/proget_alternance/MAISON_DELCOURT/chatbot.py#L122-L129)) :
- Enregistrement dans `logs/incidents.jsonl` :
```json
{
  "timestamp": "2026-10-09T00:02:02.742239",
  "type": "PANNE_API_LLM",
  "message": "Échec d'appel LLM (llama3.2:3b) : Panne simulée : 503 service unavailable",
  "session": "sess-inc",
  "stacktrace": "Traceback (most recent call last):\n  File \"chatbot.py\", line 116...\nRuntimeError: Panne simulée : 503 service unavailable",
  "sentry_reported": false
}
```
- Remontée immédiate dans le Back-office `/admin` :
  - Incrémentation du compteur `errors_count`.
  - Affichage automatique du bandeau d'alerte rouge :  
    *« ⚠️ ALERTE SUPERVISION : Défaillance détectée sur le service LLM. Le mode de secours dégradé (fallback) a été déclenché pour protéger l'expérience client. »*

#### C. Résolution : Mode Dégradé Gracieux (*Graceful Fallback*)
Plutôt que d'abandonner l'utilisateur, ChocoBot active la méthode `get_fallback_recommendation(customer)` ([incidents.py](file:///home/souhaib/Documents/proget_alternance/MAISON_DELCOURT/incidents.py#L84-L107)) :
1. **Respect absolu des allergies (Règlement INCO) :** Si le client a déclaré une allergie aux fruits à coque ou noisettes, le système conseille systématiquement le **Coffret Sans Noix (C04 - 28 €)**.
2. **Conseil par défaut :** Recommandation du **Coffret Découverte (C01 - 22 €)** et du **Grand Coffret Noël (C06 - 59 €)**.
3. **Orientation physique :** Transmission directe des coordonnées de la boutique lilloise (*03 20 00 00 00*) pour un conseil humain direct.

**Résultat vérifié :** L'API retourne un statut HTTP 200, le client reçoit une réponse soignée et conforme, et l'équipe technique est alertée sans impact sur les ventes.

---

### Incident 2 : Donnée Corrompue ou Malformée (Validation 422)

#### A. Contexte et Déclenchement
- **Scénario :** Requête API malveillante ou bug client envoyant un objet JSON dépourvu de champ obligatoire (ex : absence de `session_id` ou types invalides sur `/chat` ou `/profile`).
- **Symptôme avant correctif :** FastAPI retournait une erreur 422 standard non journalisée, masquant d'éventuelles tentatives d'injection ou des bugs d'intégration du front-end.

#### B. Diagnostic & Journalisation
Un gestionnaire d'exception dédié a été implémenté dans [app.py](file:///home/souhaib/Documents/proget_alternance/MAISON_DELCOURT/app.py#L35-L48) :
```python
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = exc.errors()
    incidents.record_incident(
        incident_type="DONNEE_CORROMPUE",
        message=f"Format de données invalide sur {request.url.path} : {error_details}",
        exc=exc
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Données de requête invalides ou incomplètes."}
    )
```

#### C. Résolution
1. **Sécurité :** Rejet immédiat de la requête avant toute interaction avec la base de données SQLite ou le LLM.
2. **Audit :** Log complet des champs rejetés pour analyse de sécurité sans exposer les détails techniques internes au client.

---

### Incident 3 : Pic de Charge et Saturation des Ressources

#### A. Contexte et Déclenchement
- **Scénario :** Simulation d'un afflux massif de clients simultanés via `load_test.py` à l'approche de Noël.
- **Symptôme avant correctif :**
  - Ollama monopolise les cœurs CPU et la VRAM GPU.
  - La latence d'inférence s'envole au-delà de 8 à 12 secondes par réponse.
  - Risque d'abandon de panier et de requêtes en timeout.

#### B. Diagnostic & Observabilité
- **Arize Phoenix :** Visualisation de la distribution des temps de réponse (latence P95 atteignant plusieurs secondes sur les inférences complexes).
- **Détection automatique de latence excessive :** Dans `chatbot.py`, tout appel dépassant 8,0 secondes est consigné sous l'étiquette `PIC_DE_CHARGE` dans les logs d'incidents.

#### C. Résolution par les 3 Leviers de Sobriété
La résolution structurelle du pic de charge s'appuie sur les optimisations développées dans [RapportCorrectifsSobriete.md](file:///home/souhaib/Documents/proget_alternance/MAISON_DELCOURT/RapportCorrectifsSobriete.md) :

1. **Levier 1 – Cache FAQ Statique & Cache de Session :**
   - Intercepte les questions récurrentes sur les horaires et les livraisons.
   - **0 token consommé, latence de 33 ms** (contre ~2,5 secondes avec Ollama).
   - Soulage instantanément 40 à 60 % de la charge totale du serveur.
2. **Levier 2 – Routage Intelligent de Modèle (SLM 1B vs LLM 3B) :**
   - Les messages courts et salutations sont orientés vers `llama3.2:1b`.
   - Modèle 3 fois plus léger en mémoire, libérant la ressource pour les requêtes complexes de conseil.
3. **Levier 3 – Fenêtre Glissante & Clamping des Tokens :**
   - Historique plafonné aux 4 derniers échanges (`sliding_history = history[-4:]`).
   - `max_tokens` bridé à 350 (contre 1 500 initialement).
   - Fin de l'inflation exponentielle du prompt lors des conversations longues.

---

## 4. Fiches Réflexes & Runbook d'Exploitation

Ce guide opérationnel est destiné aux développeurs et administrateurs assurant l'astreinte pendant les périodes de forte activité (Black Friday, Noël).

### 🚨 Fiche Réflexe 1 : Alerte Rouge sur le Back-office (`/admin`)

#### 1. Vérification Immédiate
1. Accéder au back-office : `http://localhost:8000/admin` (Identifiants : `admin` / `delcourt2026!`).
2. Consulter la table **« Journal des Incidents Supervisés »**.
3. Identifier le type d'incident prédominant (`PANNE_API_LLM`, `DONNEE_CORROMPUE`, `PIC_DE_CHARGE`).

#### 2. Procédure si `PANNE_API_LLM`
1. Vérifier l'état du démon Ollama :
   ```bash
   curl -s http://localhost:11434/api/tags
   ```
2. Si Ollama ne répond pas, le relancer en arrière-plan :
   ```bash
   ollama serve > logs/ollama.log 2>&1 &
   ```
3. Vérifier que les modèles sont disponibles :
   ```bash
   ollama list
   # Si absent :
   ollama pull llama3.2:3b
   ollama pull llama3.2:1b
   ```
4. Contrôler le fichier `.env` pour s'assurer que `FAIL_RATE` est bien désactivé (`# FAIL_RATE=0.5`).
5. Tester la reprise du service :
   ```bash
   curl -s http://localhost:8000/health
   ```

#### 3. Procédure si `DONNEE_CORROMPUE`
1. Consulter les dernières lignes de `logs/incidents.jsonl` :
   ```bash
   tail -n 20 logs/incidents.jsonl
   ```
2. Vérifier si les erreurs proviennent d'une IP spécifique ou d'un composant frontend récemment modifié.
3. Confirmer que le formulaire client `static/index.html` transmet bien un `session_id` valide.

#### 4. Procédure si `PIC_DE_CHARGE`
1. Ouvrir le tableau de bord Arize Phoenix : `http://localhost:6006`.
2. Inspecter la latence moyenne et les tokens consommés par message.
3. Si la machine hôte sature, basculer temporairement le modèle principal sur `1B` dans le fichier `.env` :
   ```ini
   LLM_MODEL_BIG=llama3.2:1b
   ```
4. Recharger le service FastAPI pour diviser immédiatement par 3 la charge de calcul.

---

## 5. Synthèse des Résultats & Bonnes Pratiques Retenues

1. **Résilience et Continuité d'Activité :**  
   Grâce au mode dégradé (*Graceful Fallback*), aucun internaute n'est laissé sans réponse en cas de panne du sous-jacent IA. Les recommandations d'urgence préservent la sécurité des clients allergiques.
2. **Protection des Données & RGPD :**  
   Les outils de supervision (Sentry, Phoenix, logs locaux) sont configurés pour **ne jamais capturer de données personnelles (PII)**. Les identifiants de session sont tronqués (`session[:8]`) et aucun nom ou email n'est transmis aux plateformes tierces.
3. **Efficacité Opérationnelle :**  
   L'équipe Maison Delcourt dispose d'un point d'entrée unique (`/admin`) réunissant métriques métier, suivi de consommation de tokens, et journalisation temps réel des anomalies.
